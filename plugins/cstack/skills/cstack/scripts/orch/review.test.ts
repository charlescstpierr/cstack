import { afterEach, expect, it } from "bun:test";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { openStore, type Store } from "./store.ts";

const roots: string[] = [];
const stores: Store[] = [];
function git(root: string, ...args: string[]): string {
  const result = Bun.spawnSync(["git", "-C", root, ...args]);
  if (result.exitCode) throw new Error(result.stderr.toString());
  return result.stdout.toString().trim();
}
async function fixture(limit = 2) {
  const repo = await mkdtemp(join(tmpdir(), "review-loop-")); roots.push(repo);
  git(repo, "init", "-b", "main"); git(repo, "config", "user.name", "Fixture");
  git(repo, "config", "user.email", "fixture@example.invalid");
  await writeFile(join(repo, ".gitignore"), ".cstack/\n");
  await writeFile(join(repo, "app.txt"), "bug\n");
  git(repo, "add", "."); git(repo, "commit", "-m", "initial");
  const directory = join(repo, ".cstack/review");
  const store = openStore(directory); stores.push(store); await store.init();
  const evidence = join(repo, ".cstack/evidence.txt"); await writeFile(evidence, "Observed fixture result\n");
  const finding = {id:"F1", mechanism:"wrong order", paths:["app.txt"], severity:"blocking"};
  const open = (target: unknown = {kind:"session"}) => store.review.open({id:"loop", repo, limit, source:"fixture workflow", target, findings:[finding]});
  const strategy = async (content: string) => {
    const path = join(repo, ".cstack", `strategy-${content}.txt`);
    await writeFile(path, content);
    return {reason:`Investigate ${content}`, files:[{kind:"brief", path}]};
  };
  const attempt = async (id: string, content = "first") => store.review.attempt({id:"loop", attempt:id, author:"builder", strategy:await strategy(content)});
  const report = async (attemptId: string, resolved = false) => {
    const view = await store.review.check("loop");
    return {id:"loop", attempt:attemptId, reviewer:"reviewer", base:view.base, patch:view.patch,
      tests:[{kind:"affected", command:"fixture affected", result:resolved ? "pass" : "fail", evidence}, {kind:"integration", command:"fixture integration", result:"pass", evidence}],
      outcomes:[{id:"F1", kind:resolved ? "fixed" : "open", reason:"Observed fixture result", evidence}],
      findings:[], progress:{kind:"none"}, decision:{kind:resolved ? "complete" : "continue", reason:"Fixture decision"}};
  };
  return {repo, directory, store, evidence, finding, open, strategy, attempt, report};
}
afterEach(async () => {
  for (const store of stores.splice(0)) await store.close();
  for (const root of roots.splice(0)) await rm(root, {recursive:true, force:true});
});

it("reserves attempts before dispatch, resumes without reset, and stops at the effective limit", async () => {
  const f = await fixture(); await f.open();
  await f.attempt("a1"); await f.attempt("a1");
  expect((await f.store.review.check("loop")).used).toBe(1);
  await f.store.review.record(await f.report("a1"));
  await f.store.close(); const resumed = openStore(f.directory); stores.push(resumed);
  await resumed.review.attempt({id:"loop", attempt:"a2", author:"builder", strategy:await f.strategy("second")});
  expect((await resumed.review.check("loop")).used).toBe(2);
  await expect(resumed.review.attempt({id:"loop", attempt:"a3", author:"builder", strategy:await f.strategy("third")})).rejects.toThrow();
  expect((await resumed.review.check("loop")).ready).toBe(false);
  expect((await resumed.review.check("loop")).source).toBe("fixture workflow");
});

it("requires an actual strategy content change after no progress", async () => {
  const f = await fixture(); await f.open(); await f.attempt("a1"); await f.store.review.record(await f.report("a1"));
  const renamed = join(f.repo, ".cstack/renamed.txt"); await writeFile(renamed, "first");
  await expect(f.store.review.attempt({id:"loop", attempt:"a2", author:"other", strategy:{reason:"New strategy", files:[{kind:"brief", path:renamed}]}})).rejects.toThrow("stratégie");
  await f.attempt("a2", "different hypothesis");
  expect((await f.store.review.check("loop")).used).toBe(2);
});

it("does not treat strategy labels or duplicate content as an escalation", async () => {
  const f = await fixture(); await f.open(); await f.attempt("a1"); await f.store.review.record(await f.report("a1"));
  const path = join(f.repo, ".cstack/relabelled.txt"); await writeFile(path, "first");
  for (const files of [[{kind:"context",path}], [{kind:"brief",path},{kind:"design",path}]]) {
    await expect(f.store.review.attempt({id:"loop",attempt:"a2",author:"other",strategy:{reason:"Changed label",files}})).rejects.toThrow("stratégie");
    expect((await f.store.review.check("loop")).used).toBe(1);
  }
});

it("keeps the last completed review head and covers all commits of a correction", async () => {
  const f = await fixture(); await f.open(); const base = git(f.repo,"rev-parse","HEAD"); await f.attempt("a1");
  for (const content of ["partial", "fixed"]) {
    await writeFile(join(f.repo,"app.txt"),content); git(f.repo,"add","app.txt"); git(f.repo,"commit","-m",content);
  }
  const view = await f.store.review.check("loop");
  expect(view.base).toBe(base); expect(git(f.repo,"rev-list","--count",`${view.base}..${view.patch.head}`)).toBe("2");
  await f.store.review.record(await f.report("a1", true));
  const ready = await f.store.review.check("loop"); expect(ready.ready).toBe(true); expect(ready.base).toBe(view.patch.head);
});

it("retains an outside finding without extending the targeted loop", async () => {
  const f = await fixture(); await f.open(); await f.attempt("a1");
  await writeFile(join(f.repo,"app.txt"),"fixed");
  const report = await f.report("a1",true);
  await f.store.review.record({...report, findings:[{id:"outside", mechanism:"separate typo", paths:["other.txt"], severity:"non-blocking", introduced:false}]});
  const view = await f.store.review.check("loop");
  expect(view.ready).toBe(true); expect(view.followUps.map(row=>row.id)).toEqual(["outside"]);
  await expect(f.attempt("a2","other")).rejects.toThrow();
});

it("keeps an older finding in a changed file outside the targeted correction", async () => {
  const f = await fixture();
  await writeFile(join(f.repo,"app.txt"),"bug\nseparator\nold unrelated typo\n");
  git(f.repo,"add","app.txt"); git(f.repo,"commit","-m","existing separate defect");
  await f.open(); await f.attempt("a1");
  await writeFile(join(f.repo,"app.txt"),"fixed\nseparator\nold unrelated typo\n");
  await f.store.review.record({...await f.report("a1",true),findings:[{id:"old",mechanism:"pre-existing typo on line 3",paths:["app.txt"],severity:"non-blocking",introduced:false}]});
  const view = await f.store.review.check("loop");
  expect(view.ready).toBe(true); expect(view.followUps.map(item=>item.id)).toEqual(["old"]);
  await expect(f.attempt("a2","unrelated typo")).rejects.toThrow("terminée");
});

it("rejects a corrupted deferred blocking finding at the persisted-state boundary", async () => {
  const f = await fixture(); await f.open(); await f.attempt("a1"); await f.store.review.record(await f.report("a1",true));
  const path = join(f.directory,"reviews.json"), saved = JSON.parse(await readFile(path,"utf8"));
  saved.reviews[0].findings[0].disposition = "deferred";
  await writeFile(path,JSON.stringify(saved));
  await expect(f.store.review.check("loop")).rejects.toThrow("non reportable");
});

it("never completes with a newly introduced blocking defect", async () => {
  const f = await fixture(); await f.open(); await f.attempt("a1"); await writeFile(join(f.repo,"app.txt"),"broken fix");
  const report = await f.report("a1",true);
  const findings = [{id:"regression", mechanism:"lost values", paths:["app.txt"], severity:"blocking", introduced:true}];
  await expect(f.store.review.record({...report, findings})).rejects.toThrow();
  await f.store.review.record({...report, findings, decision:{kind:"continue",reason:"Fix introduced regression"}});
  expect((await f.store.review.check("loop")).ready).toBe(false);
});

for (const change of ["head", "worktree", "index", "untracked"] as const) {
  it(`invalidates a completed review when ${change} changes`, async () => {
    const f = await fixture(); await f.open(); await f.attempt("a1"); await f.store.review.record(await f.report("a1",true));
    if (change === "head") git(f.repo,"commit","--allow-empty","-m","new head");
    if (change === "worktree") await writeFile(join(f.repo,"app.txt"),"changed");
    if (change === "untracked") await writeFile(join(f.repo,"new.txt"),"new behavior");
    if (change === "index") {
      await writeFile(join(f.repo,"app.txt"),"staged"); git(f.repo,"add","app.txt"); await writeFile(join(f.repo,"app.txt"),"bug\n");
    }
    expect((await f.store.review.check("loop")).ready).toBe(false);
  });
}

it("rejects a stale report and rewritten ancestry without advancing the review head", async () => {
  const f = await fixture(); await f.open(); await f.attempt("a1"); const report = await f.report("a1",true);
  await writeFile(join(f.repo,"app.txt"),"changed");
  await expect(f.store.review.record(report)).rejects.toThrow("périm");
  git(f.repo,"checkout","--orphan","replacement"); git(f.repo,"add","app.txt"); git(f.repo,"commit","-m","unrelated");
  await expect(f.store.review.check("loop")).rejects.toThrow("replan");
});

it("requires an explicit exhaustion decision and refuses deferring a blocker", async () => {
  const f = await fixture(1); await f.open(); await f.attempt("a1"); const report = await f.report("a1");
  await expect(f.store.review.record(report)).rejects.toThrow("limite");
  await expect(f.store.review.record({...report,outcomes:[{id:"F1",kind:"deferred",reason:"budget",evidence:f.evidence}],decision:{kind:"complete",reason:"budget"}})).rejects.toThrow();
  await f.store.review.record({...report,decision:{kind:"blocked",reason:"Failure reproduced at limit"}});
  expect((await f.store.review.check("loop")).ready).toBe(false);
});

it("serializes reservations on one handle and preserves distinct loops", async () => {
  const f = await fixture(); await f.open();
  const strategy = await f.strategy("first");
  const outcomes = await Promise.allSettled(["a1","a2"].map(attempt=>f.store.review.attempt({id:"loop",attempt,author:"builder",strategy})));
  expect(outcomes.filter(row=>row.status==="fulfilled")).toHaveLength(1);
  expect((await f.store.review.check("loop")).used).toBe(1);
});

it("gates only the associated unit and PR, including dirty-patch freshness", async () => {
  const f = await fixture();
  await f.store.units.add({id:"A",track:"fix"}); await f.store.units.add({id:"B",track:"independent"});
  await f.store.units.set({id:"A",state:"working",pr:1}); await f.store.units.set({id:"B",state:"working",pr:2});
  await f.open({kind:"unit",id:"A"});
  await expect(f.store.units.set({id:"A",state:"ready"})).rejects.toThrow();
  await f.store.units.set({id:"B",state:"done"});
  await f.store.ledger.record({pr:2,sha:"other",verdict:"unit-test-verified",evidence:f.evidence});
  await expect(f.store.ledger.record({pr:1,sha:git(f.repo,"rev-parse","HEAD"),verdict:"unit-test-verified",evidence:f.evidence})).rejects.toThrow();
  await f.attempt("a1"); await f.store.review.record(await f.report("a1",true));
  await f.store.units.set({id:"A",state:"ready"});
  await writeFile(join(f.repo,"app.txt"),"later change");
  await expect(f.store.units.set({id:"A",state:"done"})).rejects.toThrow();
});

it("rejects invalid limits, missing sources and mutated evidence", async () => {
  const f = await fixture();
  for (const limit of [0,-1,1.5]) await expect(f.store.review.open({id:"bad",repo:f.repo,limit,source:"fixture",target:{kind:"session"},findings:[f.finding]})).rejects.toThrow();
  await expect(f.store.review.open({id:"bad",repo:f.repo,limit:1,source:"",target:{kind:"session"},findings:[f.finding]})).rejects.toThrow();
  await f.open(); await f.attempt("a1"); await f.store.review.record(await f.report("a1",true));
  await writeFile(f.evidence,"replacement evidence"); expect((await f.store.review.check("loop")).ready).toBe(false);
  expect((await readFile(join(f.directory,"reviews.json"),"utf8")).length).toBeGreaterThan(0);
});

it("returns the original reservation on replay after a later attempt", async () => {
  const f = await fixture(); await f.open(); await f.attempt("a1"); await f.store.review.record(await f.report("a1"));
  await f.attempt("a2","second");
  expect((await f.attempt("a1")).id).toBe("a1");
  expect((await f.store.review.check("loop")).used).toBe(2);
});

it("allows a stale completed loop to consume another verification attempt without resetting its budget", async () => {
  const f = await fixture(); await f.open(); await f.attempt("a1"); await f.store.review.record(await f.report("a1",true));
  await writeFile(join(f.repo,"app.txt"),"later patch");
  await f.attempt("a2","review later patch");
  await f.store.review.record(await f.report("a2",true));
  const view = await f.store.review.check("loop"); expect(view.ready).toBe(true); expect(view.used).toBe(2);
});

it("CLI check exits nonzero with the current snapshot when blocked and zero only when ready", async () => {
  const f = await fixture(); await f.open(); await f.store.close();
  const script = join(import.meta.dir,"orch.ts");
  const before = Bun.spawnSync([process.execPath,script,"--store",f.directory,"--json","review","check","loop"]);
  expect(before.exitCode).toBe(1); expect(JSON.parse(before.stdout.toString()).ready).toBe(false);
});

it("records why integration checks do not apply without inventing a passing test", async () => {
  const f = await fixture(); await f.open(); await f.attempt("a1");
  const report = await f.report("a1",true);
  await f.store.review.record({...report,tests:[report.tests[0],{kind:"integration",command:"none",result:"not-required",reason:"Documentation-only correction has no runtime integration",evidence:f.evidence}]});
  expect((await f.store.review.check("loop")).ready).toBe(true);
});

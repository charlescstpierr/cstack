import { afterEach, expect, it } from "bun:test";
import { mkdtemp, mkdir, readFile, rm, symlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { openStore, type Store } from "./store.ts";

const roots: string[] = [];
const stores: Store[] = [];
const SCRIPT = join(import.meta.dir, "orch.ts");
const block = (value: unknown): string => `\`\`\`horizon\n${JSON.stringify(value, null, 2)}\n\`\`\`\n`;
function git(root: string, ...args: string[]): string {
  const result = Bun.spawnSync(["git", "-C", root, ...args]);
  if (result.exitCode) throw new Error(result.stderr.toString());
  return result.stdout.toString().trim();
}
function cli(...args: string[]) { return Bun.spawnSync([process.execPath, SCRIPT, ...args]); }
async function fixture() {
  const root = await mkdtemp(join(tmpdir(), "horizon-handoff-")); roots.push(root);
  git(root, "init", "-b", "main"); git(root, "config", "user.name", "Fixture"); git(root, "config", "user.email", "fixture@example.invalid");
  await writeFile(join(root, "README.md"), "Fixture\n"); git(root, "add", "."); git(root, "commit", "-m", "fixture");
  const head = git(root, "rev-parse", "HEAD");
  const horizon = join(root, ".cstack/horizon/feature"); await mkdir(join(horizon, "units"), {recursive: true});
  await mkdir(join(horizon, "tickets"));
  await writeFile(join(horizon, "tickets/01-policy.md"), "---\nid: 01\nstatus: resolved\n---\n## Réponse\nConserver pendant 90 jours.\n");
  const spec = join(horizon, "spec.md");
  const definition = {schema: 1, status: "ready", goal: "Livrer quatre comportements", out_of_scope: ["Aucune publication distante"], context: ["README.md"], decisions: ["tickets/01-policy.md"], contracts: [], requirements: ["A", "B", "C", "D"].map(id => ({id, description: `Livrer ${id}`})), units: ["units/A.md", "units/B.md", "units/C.md", "units/D.md"]};
  await writeFile(spec, block(definition));
  const definitions = ["A", "B", "C", "D"].map(id => ({id, goal: `Livrer ${id}`, blocked_by: id === "C" ? ["A"] : id === "D" ? ["B", "C"] : [], acceptance: [`L'appel ${id} retourne sa valeur attendue`], writable: [`src/${id}.ts`], forbidden: ["Ne pas publier"], context: ["README.md"], verify: [`bun run verify-${id}`], produces: [], consumes: [], tests: [{name: `verify-${id}`, requirements: [id], input: `Appel ${id}`, assertions: [`Résultat ${id}`], command: `bun run verify-${id}`, success: "exit 0"}]}));
  for (const unit of definitions) {
    await writeFile(join(horizon, `units/${unit.id}.md`), block(unit)); git(root, "branch", `work/${unit.id}`);
  }
  const directory = join(root, ".cstack/orchestrate/feature");
  const store = openStore(directory); stores.push(store); await store.init();
  const complete = async (id: string, sha = head, verdict: "unit-test-verified" | "type-check-only" = "unit-test-verified") => {
    const pr = 100 + id.charCodeAt(0); // Synthetic local fixture IDs; no remote PR is created.
    await writeFile(join(root, `evidence-${id}.md`), `${id} behavior observed at ${sha}\n`);
    await store.units.set({id, state: "done", pr, sha});
    await store.ledger.record({pr, sha, verdict, evidence: `evidence-${id}.md`, verifier: "independent-verifier"});
  };
  const claim = (id: string) => store.handoff.claim({id, owner: `owner-${id}`, branch: `work/${id}`, repo: root});
  return {root, horizon, spec, definition, definitions, directory, store, head, complete, claim};
}
afterEach(async () => { for (const store of stores.splice(0)) await store.close(); for (const root of roots.splice(0)) await rm(root, {recursive: true, force: true}); });

for (const stage of ["open", "stale"] as const) {
  it(`does not reuse ledger evidence for an ${stage} correction review while independent B stays ready`, async () => {
    const f = await fixture(); await f.store.handoff.import(f.spec); await f.claim("A"); await f.complete("A");
    expect((await f.store.handoff.ready(f.root)).ready).toEqual(["B", "C"]);
    await f.store.review.open({id:"fix-A", repo:f.root, limit:2, source:"handoff review fixture", target:stage === "open" ? {kind:"unit",id:"A"} : {kind:"pr",pr:165},
      findings:[{id:"F1", mechanism:"incorrect A behavior", paths:["src/A.ts"], severity:"blocking"}]});
    if (stage === "stale") {
      const brief = join(f.root,".cstack/review-brief.md"), evidence = join(f.root,".cstack/review-evidence.md");
      await writeFile(brief,"Verify the A correction against its behavior contract\n"); await writeFile(evidence,"Independent fixture verification completed\n");
      await f.store.review.attempt({id:"fix-A",attempt:"a1",author:"builder-A",strategy:{reason:"Inspect the A contract",files:[{kind:"brief",path:brief}]}});
      const snapshot = await f.store.review.check("fix-A");
      await f.store.review.record({id:"fix-A",attempt:"a1",reviewer:"reviewer-A",base:snapshot.base,patch:snapshot.patch,
        tests:[{kind:"affected",command:"fixture A",result:"pass",evidence},{kind:"integration",command:"fixture integration",result:"pass",evidence}],
        outcomes:[{id:"F1",kind:"fixed",reason:"A behavior verified",evidence}],findings:[],progress:{kind:"verified",summary:"A behavior passes",evidence},decision:{kind:"complete",reason:"Correction verified"}});
      expect((await f.store.handoff.ready(f.root)).ready).toEqual(["B", "C"]);
      await writeFile(join(f.root,"later-untracked.ts"),"export const later = true;\n");
    }
    expect((await f.store.handoff.ready(f.root)).ready).toEqual(["B"]);
    await expect(f.claim("C")).rejects.toThrow("non dispatchable");
    expect((await f.claim("B")).owner).toBe("owner-B");
  });
}

it("imports the four-unit graph once and unlocks C then D only with exact-head behavior evidence", async () => {
  const f = await fixture();
  expect((await f.store.handoff.import(f.spec)).added).toEqual(["A", "B", "C", "D"]);
  expect((await f.store.handoff.ready(f.root)).ready).toEqual(["A", "B"]);
  const brief = await readFile(join(f.directory, "briefs/C.md"), "utf8");
  for (const value of [f.spec, "Version SHA256:", "Bloqueurs: A", "GOAL", "SCOPE", "CONTEXT", "ACCEPTANCE", "VERIFY", "FORBIDDEN", "REPORT"]) expect(brief).toContain(value);
  await expect(f.claim("C")).rejects.toThrow("non dispatchable");
  await f.claim("A"); await f.claim("B");
  await expect(f.claim("A")).rejects.toThrow("non dispatchable");
  await f.complete("A", f.head, "type-check-only");
  expect((await f.store.handoff.ready(f.root)).ready).toEqual([]);
  await f.complete("A"); expect((await f.store.handoff.ready(f.root)).ready).toEqual(["C"]);
  await f.claim("C"); await f.complete("C"); expect((await f.store.handoff.ready(f.root)).ready).toEqual([]);
  await f.complete("B"); expect((await f.store.handoff.ready(f.root)).ready).toEqual(["D"]);
  await f.claim("D"); await f.complete("D"); expect((await f.store.handoff.ready(f.root)).ready).toEqual([]);
  const units = await readFile(join(f.directory, "units.tsv"), "utf8");
  const ledger = await readFile(join(f.directory, "ledger.tsv"), "utf8");
  expect((await f.store.handoff.import(f.spec)).reused).toEqual(["A", "B", "C", "D"]);
  expect(await readFile(join(f.directory, "units.tsv"), "utf8")).toBe(units);
  expect(await readFile(join(f.directory, "ledger.tsv"), "utf8")).toBe(ledger);
});

for (const failure of ["missing-id", "duplicate-id", "unknown", "cycle", "waiting", "acceptance", "writable", "spec", "verify"] as const) {
  it(`fails closed before any rows or receipt for ${failure}`, async () => {
    const f = await fixture(); const a = f.definitions[0]!;
    if (failure === "waiting") await writeFile(join(f.horizon, "tickets/01-policy.md"), "---\nstatus: waiting\n---\n");
    else if (failure === "spec") await writeFile(f.spec, block({...f.definition, status: "draft"}));
    else {
      const mutation = failure === "missing-id" ? {id: ""} : failure === "duplicate-id" ? {id: "B"} : failure === "unknown" ? {blocked_by: ["unknown"]} : failure === "cycle" ? {blocked_by: ["D"]} : {[failure]: []};
      await writeFile(join(f.horizon, "units/A.md"), block({...a, ...mutation}));
    }
    await expect(f.store.handoff.import(f.spec)).rejects.toThrow();
    expect(await f.store.units.list()).toEqual([]);
    expect(await Bun.file(join(f.directory, "horizon.json")).exists()).toBe(false);
  });
}

it("detects changed spec, decisions and briefs without losing owner or evidence", async () => {
  for (const changed of ["spec", "decision", "brief"]) {
    const f = await fixture(); await f.store.handoff.import(f.spec); await f.claim("A"); await f.complete("A");
    const units = await readFile(join(f.directory, "units.tsv"), "utf8");
    const ledger = await readFile(join(f.directory, "ledger.tsv"), "utf8");
    const path = changed === "spec" ? f.spec : changed === "decision" ? join(f.horizon, "tickets/01-policy.md") : join(f.directory, "briefs/A.md");
    await writeFile(path, `${await readFile(path, "utf8")}\nChanged source\n`);
    await expect(f.store.handoff.import(f.spec)).rejects.toThrow("dérive");
    await expect(f.claim("B")).rejects.toThrow("dérive");
    expect(await readFile(join(f.directory, "units.tsv"), "utf8")).toBe(units);
    expect(await readFile(join(f.directory, "ledger.tsv"), "utf8")).toBe(ledger);
  }
});

it("resumes interrupted preparation and preserves a claim across reopening", async () => {
  const f = await fixture(); await f.store.handoff.import(f.spec);
  const receiptPath = join(f.directory, "horizon.json");
  const receipt = JSON.parse(await readFile(receiptPath, "utf8")); receipt.committed = false;
  await writeFile(receiptPath, JSON.stringify(receipt));
  const unitsPath = join(f.directory, "units.tsv");
  await writeFile(unitsPath, (await readFile(unitsPath, "utf8")).split("\n")[0] + "\n");
  await rm(join(f.directory, "briefs/C.md"));
  await expect(f.claim("A")).rejects.toThrow("incomplet");
  expect((await f.store.handoff.import(f.spec)).added).toEqual(["A", "B", "C", "D"]);
  await f.claim("A"); await f.store.close();
  const resumed = openStore(f.directory); stores.push(resumed);
  expect((await resumed.handoff.import(f.spec)).added).toEqual([]);
  expect((await resumed.units.get("A")).owner).toBe("owner-A");
  await expect(resumed.handoff.claim({id:"A", owner:"new-owner", branch:"work/A", repo:f.root})).rejects.toThrow("non dispatchable");
  await expect(resumed.units.set({id:"A", state:"pending"})).rejects.toThrow("réattribution");
});

it("refuses deleted execution rows instead of recreating completed work", async () => {
  for (const all of [true, false]) {
    const f = await fixture(); await f.store.handoff.import(f.spec); await f.claim("A");
    const path = join(f.directory, "units.tsv"); const rows = (await readFile(path, "utf8")).trimEnd().split("\n");
    await writeFile(path, (all ? rows.slice(0, 1) : rows.filter(row => !row.startsWith("A\t"))).join("\n") + "\n");
    await expect(f.store.handoff.import(f.spec)).rejects.toThrow();
  }
});

it("never reuses an old ledger verdict when either recorded or actual local head changes", async () => {
  const f = await fixture(); await f.store.handoff.import(f.spec); await f.claim("A"); await f.complete("A");
  expect((await f.store.handoff.ready(f.root)).ready).toEqual(["B", "C"]);
  git(f.root, "commit", "--allow-empty", "-m", "new head"); const newHead = git(f.root, "rev-parse", "HEAD");
  git(f.root, "branch", "-f", "work/A", newHead);
  expect((await f.store.handoff.ready(f.root)).ready).toEqual(["B"]);
  await f.store.units.set({id:"A", state:"done", sha:newHead});
  expect((await f.store.handoff.ready(f.root)).ready).toEqual(["B"]);
  await f.complete("A", newHead); expect((await f.store.handoff.ready(f.root)).ready).toEqual(["B", "C"]);
});

it("requires distinct verifier and existing evidence, and serializes overlapping writes", async () => {
  const f = await fixture(); await writeFile(join(f.horizon, "units/B.md"), block({...f.definitions[1], writable:["src/A.ts"]}));
  await f.store.handoff.import(f.spec); await f.claim("A");
  expect((await f.store.handoff.ready(f.root)).ready).toEqual([]);
  await f.complete("A");
  await f.store.ledger.record({pr:165, sha:f.head, verdict:"unit-test-verified", evidence:"evidence-A.md", verifier:"owner-A"});
  expect((await f.store.handoff.ready(f.root)).ready).toEqual(["B"]);
  await f.complete("A"); await rm(join(f.root,"evidence-A.md"));
  expect((await f.store.handoff.ready(f.root)).ready).toEqual(["B"]);
});

it("exposes local-only CLI handoff and concurrent claims yield one winner", async () => {
  const f = await fixture(); await f.store.close();
  let result = cli("--store",f.directory,"--json","handoff","import",f.spec);
  expect(result.exitCode, result.stderr.toString()).toBe(0);
  result = cli("--store",f.directory,"--json","handoff","ready","--repo",f.root);
  expect(result.exitCode, result.stderr.toString()).toBe(0); expect(JSON.parse(result.stdout.toString()).ready).toEqual(["A","B"]);
  const args = [process.execPath,SCRIPT,"--store",f.directory,"--json","handoff","claim","A","--owner","owner-A","--branch","work/A","--repo",f.root];
  const children = [Bun.spawn(args,{stdout:"pipe",stderr:"pipe"}),Bun.spawn(args,{stdout:"pipe",stderr:"pipe"})];
  const codes = await Promise.all(children.map(child=>child.exited));
  expect(codes.sort()).toEqual([0,1]);
  expect(git(f.root,"remote")).toBe("");
});

it("blocks omitted waiting decisions", async () => {
  const f = await fixture();
  await writeFile(join(f.horizon,"tickets/02-waiting.md"), "---\nstatus: waiting\n---\nHuman answer required.\n");
  await expect(f.store.handoff.import(f.spec)).rejects.toThrow("non référencée");
});

it("exposes persistent ownership in status", async () => {
  const f = await fixture();
  await f.store.handoff.import(f.spec); await f.claim("A"); await f.store.status.render();
  const status = await readFile(join(f.directory,"status.md"),"utf8");
  expect(status).toContain("| Brief | Owner |"); expect(status).toContain("owner-A");
});

it("serializes same-handle claims and rejects branches occupied by legacy units", async () => {
  const f = await fixture(); await f.store.handoff.import(f.spec);
  await f.store.units.add({id:"legacy",track:"other"}); await f.store.units.set({id:"legacy",state:"working",branch:"work/A"});
  await expect(f.claim("A")).rejects.toThrow("branche déjà attribuée");
  const results = await Promise.allSettled([f.claim("B"), f.claim("B")]);
  expect(results.filter(result => result.status === "fulfilled")).toHaveLength(1);
});

it("does not reopen completed writers or dispatch without integrated blocker heads", async () => {
  const f = await fixture(); await f.store.handoff.import(f.spec); await f.claim("A");
  git(f.root,"checkout","work/A"); await writeFile(join(f.root,"a.txt"),"A\n"); git(f.root,"add","a.txt"); git(f.root,"commit","-m","A behavior");
  const head = git(f.root,"rev-parse","HEAD"); await f.complete("A",head);
  await expect(f.store.units.set({id:"A",state:"working"})).rejects.toThrow("terminée");
  await expect(f.claim("C")).rejects.toThrow("intégrer");
  git(f.root,"checkout","work/C"); git(f.root,"merge","--ff-only","work/A");
  expect((await f.claim("C")).owner).toBe("owner-C");
});

it("allows only one simultaneous claim on a shared handle", async () => {
  const f = await fixture(); await f.store.handoff.import(f.spec);
  const results = await Promise.allSettled([f.claim("A"), f.claim("A")]);
  expect(results.filter(result => result.status === "fulfilled")).toHaveLength(1);
});

it("requires a dependent branch to contain verified blocker code", async () => {
  const f = await fixture(); await f.store.handoff.import(f.spec); await f.claim("A");
  git(f.root,"checkout","work/A"); git(f.root,"commit","--allow-empty","-m","new verified A");
  await f.complete("A",git(f.root,"rev-parse","HEAD"));
  await expect(f.claim("C")).rejects.toThrow("intégrer");
});

it("rejects ambiguous writable paths and unanswered resolved decisions", async () => {
  const f = await fixture();
  await writeFile(join(f.horizon,"units/A.md"),block({...f.definitions[0],writable:["src//A.ts"]}));
  await expect(f.store.handoff.import(f.spec)).rejects.toThrow("frontière");
});

it("rejects a resolved decision with no recorded answer", async () => {
  const f = await fixture(); await writeFile(join(f.horizon,"tickets/01-policy.md"),"---\nstatus: resolved\n---\n## Réponse\n<TODO>\n");
  await expect(f.store.handoff.import(f.spec)).rejects.toThrow("réponse");
});

it("rejects ambiguous omitted decision status", async () => {
  const f = await fixture();
  await writeFile(join(f.horizon,"tickets/02-ambiguous.md"),"---\nstatus: waiting\nstatus: out-of-scope\n---\n");
  await expect(f.store.handoff.import(f.spec)).rejects.toThrow("non référencée");
});

it("rejects duplicate writable entries after trailing slash normalization", async () => {
  const f = await fixture();
  await writeFile(join(f.horizon,"units/A.md"),block({...f.definitions[0],writable:["src/A", "src/A/"]}));
  await expect(f.store.handoff.import(f.spec)).rejects.toThrow("doublons");
});


it("blocks symlinked writable scopes while preserving independent eligibility", async () => {
  const f = await fixture();
  await mkdir(join(f.root, "src"));
  await writeFile(join(f.root, "src/shared.ts"), "shared\n");
  await writeFile(join(f.horizon, "units/A.md"), block({...f.definitions[0], writable:["src/shared.ts"]}));
  await writeFile(join(f.horizon, "units/B.md"), block({...f.definitions[1], writable:["alias/shared.ts"]}));
  await f.store.handoff.import(f.spec);
  expect((await f.store.handoff.ready(f.root)).ready).toEqual(["A", "B"]);
  await f.claim("A");
  await symlink("src", join(f.root, "alias"));
  const ready = await f.store.handoff.ready(f.root);
  expect(ready.ready).toEqual([]);
  expect(ready.blocked.find(row => row.id === "B")?.reason).toContain("symbolique");
  await expect(f.claim("B")).rejects.toThrow("non dispatchable");
  expect((await f.store.units.get("B")).owner).toBeUndefined();
});

it("rejects symlinked existing ancestors and leaves missing in-repo scopes eligible", async () => {
  for (const target of ["README.md", "missing/deep/new.ts"]) {
    const f = await fixture();
    const external = await mkdtemp(join(tmpdir(), "horizon-outside-")); roots.push(external);
    await writeFile(join(f.horizon, "units/A.md"), block({...f.definitions[0], writable:[`escape/${target}`]}));
    await f.store.handoff.import(f.spec);
    await symlink(external, join(f.root, "escape"));
    expect((await f.store.handoff.ready(f.root)).ready).toEqual(["B"]);
    await expect(f.claim("A")).rejects.toThrow("non dispatchable");
    expect((await f.claim("B")).owner).toBe("owner-B");
  }
});

for (const branch of ["work/A^{commit}", "work/A~0", "work/A@{0}", "@{-1}", "work/alias"]) {
  it(`rejects nonliteral or aliased branch ${branch} without acquiring an owner`, async () => {
    const f = await fixture(); await f.store.handoff.import(f.spec); await f.claim("A");
    git(f.root, "symbolic-ref", "refs/heads/work/alias", "refs/heads/work/A");
    await expect(f.store.handoff.claim({id:"B", owner:"owner-B", branch, repo:f.root})).rejects.toThrow("branche locale littérale");
    expect((await f.store.units.get("B")).owner).toBeUndefined();
    expect((await f.claim("B")).branch).toBe("work/B");
  });
}

it("blocks a writable directory containing a descendant symlink to another unit", async () => {
  const f = await fixture();
  await mkdir(join(f.root, "src/nested"), {recursive:true});
  await mkdir(join(f.root, "other"));
  await writeFile(join(f.root, "other/shared.ts"), "shared\n");
  await writeFile(join(f.horizon, "units/A.md"), block({...f.definitions[0], writable:["src"]}));
  await writeFile(join(f.horizon, "units/B.md"), block({...f.definitions[1], writable:["other"]}));
  await f.store.handoff.import(f.spec);
  expect((await f.store.handoff.ready(f.root)).ready).toEqual(["A", "B"]);
  await symlink("../../other", join(f.root, "src/nested/alias"));
  const ready = await f.store.handoff.ready(f.root);
  expect(ready.ready).toEqual(["B"]);
  expect(ready.blocked.find(row => row.id === "A")?.reason).toContain("src/nested/alias");
  await expect(f.claim("A")).rejects.toThrow("non dispatchable");
  expect((await f.claim("B")).owner).toBe("owner-B");
});

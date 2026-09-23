import { expect, test } from "bun:test";
import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import {
  chmodSync,
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  statSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

const root = resolve(import.meta.dir, "..");
const tool = join(root, "scripts/sync-upstream.mjs");
const repository = "https://github.com/cursor/plugins";

function git(cwd: string, ...args: string[]) {
  return execFileSync("git", args, { cwd, encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] }).trim();
}

function blob(value: string | Buffer) {
  const bytes = Buffer.isBuffer(value) ? value : Buffer.from(value);
  return createHash("sha1").update(`blob ${bytes.length}\0`).update(bytes).digest("hex");
}

function commit(cwd: string, message: string) {
  git(cwd, "add", "-A");
  git(cwd, "commit", "-m", message);
  return git(cwd, "rev-parse", "HEAD");
}

type Fixture = {
  workspace: string;
  source: string;
  oldPin: string;
  newPin: string;
  oldFiles: Record<string, string>;
  newFiles: Record<string, string>;
};

type RepoFixture = Pick<Fixture, "workspace" | "source">;

function makeFixture() {
  const workspace = mkdtempSync(join(tmpdir(), "cstack-sync-workspace-"));
  const source = mkdtempSync(join(tmpdir(), "cstack-sync-source-"));
  mkdirSync(join(workspace, "plugins/cstack"), { recursive: true });
  git(source, "init", "-b", "main");
  git(source, "config", "user.email", "fixture@example.invalid");
  git(source, "config", "user.name", "Fixture");
  git(source, "remote", "add", "origin", `${repository}.git`);
  return { workspace, source };
}

function writeSource(source: string, files: Record<string, string>) {
  for (const [path, content] of Object.entries(files)) {
    const target = join(source, path);
    mkdirSync(join(target, ".."), { recursive: true });
    writeFileSync(target, content);
  }
}

function prepareWorkspace(workspace: string, source: string, oldPin: string, oldFiles: Record<string, string>, mappings: Array<Record<string, string>>, original: Array<Record<string, string>> = []) {
  const inventory = {
    repository,
    commit: oldPin,
    subdirectory: "pstack",
    files: Object.keys(oldFiles).map((path) => ({
      path: `pstack/${path}`,
      git_blob: git(source, "rev-parse", `${oldPin}:pstack/${path}`),
    })),
  };
  writeFileSync(join(workspace, "UPSTREAM.json"), `${JSON.stringify(inventory, null, 2)}\n`);
  writeFileSync(join(workspace, "PORTING.json"), `${JSON.stringify({ commit: oldPin, files: mappings, original }, null, 2)}\n`);
}

function run(fixture: RepoFixture, ...args: string[]) {
  return Bun.spawnSync([
    "bun",
    tool,
    "--root",
    fixture.workspace,
    "--source",
    fixture.source,
    ...args,
  ], { cwd: root, stdout: "pipe", stderr: "pipe" });
}

function parsePlan(result: ReturnType<typeof run>) {
  if (result.exitCode !== 0) throw new Error(result.stderr.toString());
  expect(result.exitCode).toBe(0);
  return JSON.parse(result.stdout.toString());
}

function fixtureWithChanges(): Fixture {
  const { workspace, source } = makeFixture();
  const oldFiles: Record<string, string> = {
    "ported.md": "# Upstream title\nbase\n",
    "retained.md": "retained old\n",
    "replaced.md": "replace me\n",
    "many-a.md": "a old\n",
    "many-b.md": "b old\n",
    "deleted.md": "delete me\n",
  };
  const newFiles: Record<string, string> = {
    "ported.md": "# Upstream title\nbase\nupstream addition\n",
    "retained.md": "retained new\n",
    "replaced.md": "replace upstream\n",
    "many-a.md": "a new\n",
    "many-b.md": "b old\n",
    "new.md": "new upstream\n",
  };
  writeSource(source, Object.fromEntries(Object.entries(oldFiles).map(([path, content]) => [`pstack/${path}`, content])));
  const oldPin = commit(source, "old upstream");
  rmSync(join(source, "pstack/deleted.md"));
  writeSource(source, Object.fromEntries(Object.entries(oldFiles)
    .filter(([path]) => path !== "deleted.md")
    .map(([path]) => [`pstack/${path}`, newFiles[path] ?? oldFiles[path]])));
  writeSource(source, { "pstack/new.md": newFiles["new.md"] });
  const newPin = commit(source, "new upstream");
  const targets = {
    "plugins/cstack/ported.md": "# Titre français\nbase\n",
    "plugins/cstack/retained.md": oldFiles["retained.md"],
    "plugins/cstack/replaced.md": "traduction locale\n",
    "plugins/cstack/many.md": "contenu composé local\n",
    "plugins/cstack/deleted.md": oldFiles["deleted.md"],
    "plugins/cstack/original.md": "maintenu par cstack\n",
  };
  const mappings = [
    { source: "pstack/ported.md", target: "plugins/cstack/ported.md", status: "ported", reason: "traduction française" },
    { source: "pstack/retained.md", target: "plugins/cstack/retained.md", status: "retained", reason: "texte MIT inchangé" },
    { source: "pstack/replaced.md", target: "plugins/cstack/replaced.md", status: "replaced", reason: "adaptation Codex" },
    { source: "pstack/many-a.md", target: "plugins/cstack/many.md", status: "ported", reason: "guide composé" },
    { source: "pstack/many-b.md", target: "plugins/cstack/many.md", status: "replaced", reason: "guide composé" },
    { source: "pstack/deleted.md", target: "plugins/cstack/deleted.md", status: "ported", reason: "supprimé amont" },
  ];
  for (const [path, content] of Object.entries(targets)) {
    const target = join(workspace, path);
    mkdirSync(join(target, ".."), { recursive: true });
    writeFileSync(target, content);
  }
  prepareWorkspace(workspace, source, oldPin, oldFiles, mappings, [{ path: "plugins/cstack/original.md", reason: "provenance cstack" }]);
  return { workspace, source, oldPin, newPin, oldFiles, newFiles };
}

function fillResolution(fixture: Fixture, plan: any) {
  const resolution = plan.resolutionTemplate;
  mkdirSync(join(fixture.workspace, ".cstack/resolutions"), { recursive: true });
  for (const group of resolution.groups) {
    const state = plan.entries.find((entry: any) => entry.sources.join("\0") === group.sources.join("\0") || group.sources.every((source: string) => entry.sources.includes(source)));
    if (group.sources.includes("pstack/new.md")) {
      group.target = "plugins/cstack/new.md";
      group.status = "ported";
      group.mappingReason = "nouvelle source revue";
      group.action = "write";
      const path = join(fixture.workspace, ".cstack/resolutions/new.md");
      writeFileSync(path, "nouvelle traduction\n");
      group.result = { path: ".cstack/resolutions/new.md", blob: blob(readFileSync(path)) };
    } else if (group.sources.includes("pstack/deleted.md")) {
      group.action = "delete";
      group.reason = "suppression amont approuvée";
    } else if (group.sources.includes("pstack/replaced.md")) {
      group.action = "write";
      group.reason = "traduction française relue après conflit";
      const path = join(fixture.workspace, ".cstack/resolutions/replaced.md");
      writeFileSync(path, "traduction locale\n");
      group.result = { path: ".cstack/resolutions/replaced.md", blob: blob(readFileSync(path)) };
    } else if (group.sources.includes("pstack/many-a.md")) {
      group.action = "write";
      group.reason = "résultat composé revu";
      const path = join(fixture.workspace, ".cstack/resolutions/many.md");
      writeFileSync(path, "composition française revue\n");
      group.result = { path: ".cstack/resolutions/many.md", blob: blob(readFileSync(path)) };
    } else if (group.sources.includes("pstack/ported.md")) {
      group.action = "write";
      group.reason = "merge français relu";
      const path = join(fixture.workspace, ".cstack/resolutions/ported.md");
      writeFileSync(path, "# Titre français\nbase\nupstream addition\n");
      group.result = { path: ".cstack/resolutions/ported.md", blob: blob(readFileSync(path)) };
    } else {
      throw new Error(`groupe de test inattendu: ${JSON.stringify(group)}`);
    }
    if (!group.reason) group.reason = "résolution approuvée";
    if (state && group.action === "write" && !group.result) throw new Error("result manquant");
  }
  const path = join(fixture.workspace, ".cstack/resolution.json");
  writeFileSync(path, `${JSON.stringify(resolution, null, 2)}\n`);
  return path;
}

test("preview réel décrit les changements sans toucher les octets ni les pins", () => {
  const fixture = fixtureWithChanges();
  try {
    const beforeInventory = readFileSync(join(fixture.workspace, "UPSTREAM.json"));
    const beforeTarget = readFileSync(join(fixture.workspace, "plugins/cstack/ported.md"));
    const plan = parsePlan(run(fixture, "--to", fixture.newPin, "--dry-run"));
    expect(plan.oldPin).toBe(fixture.oldPin);
    expect(plan.newPin).toBe(fixture.newPin);
    expect(typeof plan.summary.unresolved).toBe("number");
    expect(plan.summary.unresolved).toBeGreaterThan(0);
    expect(plan.entries.find((entry: any) => entry.sources.includes("pstack/many-a.md")).manyToOne).toBe(true);
    expect(readFileSync(join(fixture.workspace, "UPSTREAM.json"))).toEqual(beforeInventory);
    expect(readFileSync(join(fixture.workspace, "plugins/cstack/ported.md"))).toEqual(beforeTarget);
  } finally {
    rmSync(fixture.workspace, { recursive: true, force: true });
    rmSync(fixture.source, { recursive: true, force: true });
  }
});

test("apply exige des résolutions bornées puis avance pin et couverture ensemble", () => {
  const fixture = fixtureWithChanges();
  try {
    const plan = parsePlan(run(fixture, "--to", fixture.newPin));
    const resolutionPath = fillResolution(fixture, plan);
    const result = run(fixture, "--to", fixture.newPin, "--apply", "--resolutions", resolutionPath);
    if (result.exitCode !== 0) throw new Error(result.stderr.toString());
    expect(result.exitCode).toBe(0);
    expect(JSON.parse(result.stdout.toString()).summary.unresolved).toBe(0);
    const upstream = JSON.parse(readFileSync(join(fixture.workspace, "UPSTREAM.json"), "utf8"));
    const porting = JSON.parse(readFileSync(join(fixture.workspace, "PORTING.json"), "utf8"));
    expect(upstream.commit).toBe(fixture.newPin);
    expect(porting.commit).toBe(fixture.newPin);
    expect(porting.files.map((entry: any) => entry.source)).toContain("pstack/new.md");
    expect(porting.files.map((entry: any) => entry.source)).not.toContain("pstack/deleted.md");
    expect(porting.original).toEqual(expect.arrayContaining([{ path: "plugins/cstack/original.md", reason: "provenance cstack" }]));
    expect(readFileSync(join(fixture.workspace, "plugins/cstack/ported.md"), "utf8")).toContain("upstream addition");
    expect(readFileSync(join(fixture.workspace, "plugins/cstack/new.md"), "utf8")).toBe("nouvelle traduction\n");
    expect(existsSync(join(fixture.workspace, "plugins/cstack/deleted.md"))).toBe(false);
  } finally {
    rmSync(fixture.workspace, { recursive: true, force: true });
    rmSync(fixture.source, { recursive: true, force: true });
  }
});

test("keep sans cible finale refuse l’apply, puis map/write crée une cible valide", () => {
  const fixture = fixtureWithChanges();
  try {
    const plan = parsePlan(run(fixture, "--to", fixture.newPin));
    const resolutionPath = fillResolution(fixture, plan);
    const resolution = JSON.parse(readFileSync(resolutionPath, "utf8"));
    const group = resolution.groups.find((item: any) => item.sources.includes("pstack/new.md"));
    group.target = "plugins/cstack/missing-notice.md";
    group.action = "keep";
    group.reason = "conserver sans fichier serait invalide";
    group.result = null;
    writeFileSync(resolutionPath, JSON.stringify(resolution));

    const refused = run(fixture, "--to", fixture.newPin, "--apply", "--resolutions", resolutionPath);
    expect(refused.exitCode).not.toBe(0);
    expect(refused.stderr.toString()).toContain("cible finale absente");
    expect(JSON.parse(readFileSync(join(fixture.workspace, "UPSTREAM.json"), "utf8")).commit).toBe(fixture.oldPin);
    expect(existsSync(join(fixture.workspace, "plugins/cstack/missing-notice.md"))).toBe(false);

    const resultPath = join(fixture.workspace, ".cstack/resolutions/missing-notice.md");
    writeFileSync(resultPath, "notice unsupported approuvée\n");
    group.action = "map";
    group.result = { path: resultPath, blob: blob(readFileSync(resultPath)) };
    writeFileSync(resolutionPath, JSON.stringify(resolution));
    const applied = run(fixture, "--to", fixture.newPin, "--apply", "--resolutions", resolutionPath);
    if (applied.exitCode !== 0) throw new Error(applied.stderr.toString());
    expect(applied.exitCode).toBe(0);
    expect(readFileSync(join(fixture.workspace, "plugins/cstack/missing-notice.md"), "utf8")).toBe("notice unsupported approuvée\n");
    expect(JSON.parse(readFileSync(join(fixture.workspace, "UPSTREAM.json"), "utf8")).commit).toBe(fixture.newPin);
  } finally {
    rmSync(fixture.workspace, { recursive: true, force: true });
    rmSync(fixture.source, { recursive: true, force: true });
  }
});

test("une nouvelle source ne peut pas écraser la cible retained d’un groupe inchangé", () => {
  const fixture = makeFixture();
  try {
    const oldFiles = { "a.md": "retained source\n" };
    writeSource(fixture.source, { "pstack/a.md": oldFiles["a.md"] });
    const oldPin = commit(fixture.source, "old retained");
    writeSource(fixture.source, { "pstack/b.md": "new source\n" });
    const newPin = commit(fixture.source, "new source");
    const target = join(fixture.workspace, "plugins/cstack/a.md");
    mkdirSync(join(target, ".."), { recursive: true });
    writeFileSync(target, oldFiles["a.md"]);
    prepareWorkspace(fixture.workspace, fixture.source, oldPin, oldFiles, [{
      source: "pstack/a.md",
      target: "plugins/cstack/a.md",
      status: "retained",
      reason: "contenu MIT",
    }]);
    const actualFixture = { workspace: fixture.workspace, source: fixture.source };
    const plan = parsePlan(run(actualFixture, "--to", newPin));
    const resolution = plan.resolutionTemplate;
    const group = resolution.groups.find((item: any) => item.sources.includes("pstack/b.md"));
    group.target = "plugins/cstack/a.md";
    group.localBlob = blob(readFileSync(target));
    group.localMode = 0o644;
    group.status = "ported";
    group.mappingReason = "nouvelle traduction";
    group.action = "write";
    group.reason = "résultat divergent";
    const resultPath = join(fixture.workspace, "result.md");
    writeFileSync(resultPath, "divergent replacement\n");
    group.result = { path: resultPath, blob: blob(readFileSync(resultPath)) };
    const resolutionPath = join(fixture.workspace, "resolution.json");
    writeFileSync(resolutionPath, JSON.stringify(resolution));

    const refused = run(actualFixture, "--to", newPin, "--apply", "--resolutions", resolutionPath);
    expect(refused.exitCode).not.toBe(0);
    expect(refused.stderr.toString()).toContain("retained final différent");
    expect(readFileSync(target, "utf8")).toBe(oldFiles["a.md"]);
    expect(JSON.parse(readFileSync(join(fixture.workspace, "UPSTREAM.json"), "utf8")).commit).toBe(oldPin);

    group.target = "plugins/cstack/b.md";
    group.localBlob = null;
    group.localMode = null;
    const validResult = join(fixture.workspace, "result-b.md");
    writeFileSync(validResult, "new translated source\n");
    group.result = { path: validResult, blob: blob(readFileSync(validResult)) };
    writeFileSync(resolutionPath, JSON.stringify(resolution));
    const applied = run(actualFixture, "--to", newPin, "--apply", "--resolutions", resolutionPath);
    if (applied.exitCode !== 0) throw new Error(applied.stderr.toString());
    expect(applied.exitCode).toBe(0);
    expect(readFileSync(target, "utf8")).toBe(oldFiles["a.md"]);
    expect(readFileSync(join(fixture.workspace, "plugins/cstack/b.md"), "utf8")).toBe("new translated source\n");
    expect(JSON.parse(readFileSync(join(fixture.workspace, "UPSTREAM.json"), "utf8")).commit).toBe(newPin);
  } finally {
    rmSync(fixture.workspace, { recursive: true, force: true });
    rmSync(fixture.source, { recursive: true, force: true });
  }
});

test("une résolution ne peut pas déclarer une source inchangée hors de son union", () => {
  const fixture = makeFixture();
  try {
    const oldFiles = { "a.md": "a old\n", "b.md": "b same\n" };
    writeSource(fixture.source, { "pstack/a.md": oldFiles["a.md"], "pstack/b.md": oldFiles["b.md"] });
    const oldPin = commit(fixture.source, "old two sources");
    writeSource(fixture.source, { "pstack/a.md": "a new\n" });
    const newPin = commit(fixture.source, "change only a");
    for (const [path, content] of Object.entries({
      "plugins/cstack/a.md": oldFiles["a.md"],
      "plugins/cstack/b.md": oldFiles["b.md"],
    })) {
      const target = join(fixture.workspace, path);
      mkdirSync(join(target, ".."), { recursive: true });
      writeFileSync(target, content);
    }
    prepareWorkspace(fixture.workspace, fixture.source, oldPin, oldFiles, [
      { source: "pstack/a.md", target: "plugins/cstack/a.md", status: "ported", reason: "adaptation" },
      { source: "pstack/b.md", target: "plugins/cstack/b.md", status: "ported", reason: "adaptation" },
    ]);
    const actualFixture = { workspace: fixture.workspace, source: fixture.source };
    const plan = parsePlan(run(actualFixture, "--to", newPin));
    const resolution = plan.resolutionTemplate;
    const group = resolution.groups[0];
    group.sources.push("pstack/b.md");
    const bBlob = git(fixture.source, "rev-parse", `${oldPin}:pstack/b.md`);
    group.old.push({ path: "pstack/b.md", blob: bBlob, mode: 0o644 });
    group.next.push({ path: "pstack/b.md", blob: bBlob, mode: 0o644 });
    group.mappings.push({ source: "pstack/b.md", status: "ported", reason: "détournement" });
    group.reason = "résultat a seulement";
    const resultPath = join(fixture.workspace, "result.md");
    writeFileSync(resultPath, "a translated\n");
    group.result = { path: resultPath, blob: blob(readFileSync(resultPath)) };
    const resolutionPath = join(fixture.workspace, "resolution.json");
    writeFileSync(resolutionPath, JSON.stringify(resolution));
    const refused = run(actualFixture, "--to", newPin, "--apply", "--resolutions", resolutionPath);
    expect(refused.exitCode).not.toBe(0);
    expect(refused.stderr.toString()).toContain("sources hors union");
    expect(readFileSync(join(fixture.workspace, "plugins/cstack/b.md"), "utf8")).toBe(oldFiles["b.md"]);
    expect(JSON.parse(readFileSync(join(fixture.workspace, "UPSTREAM.json"), "utf8")).commit).toBe(oldPin);
  } finally {
    rmSync(fixture.workspace, { recursive: true, force: true });
    rmSync(fixture.source, { recursive: true, force: true });
  }
});

test("un changement de mode Git retained est planifié et appliqué", () => {
  const fixture = makeFixture();
  try {
    const content = "#!/bin/sh\necho ok\n";
    writeSource(fixture.source, { "pstack/tool.sh": content });
    chmodSync(join(fixture.source, "pstack/tool.sh"), 0o644);
    const oldPin = commit(fixture.source, "tool non executable");
    chmodSync(join(fixture.source, "pstack/tool.sh"), 0o755);
    const newPin = commit(fixture.source, "tool executable");
    const target = join(fixture.workspace, "plugins/cstack/tool.sh");
    mkdirSync(join(target, ".."), { recursive: true });
    writeFileSync(target, content);
    chmodSync(target, 0o644);
    prepareWorkspace(fixture.workspace, fixture.source, oldPin, { "tool.sh": content }, [{
      source: "pstack/tool.sh", target: "plugins/cstack/tool.sh", status: "retained", reason: "script MIT",
    }]);
    const actualFixture = { workspace: fixture.workspace, source: fixture.source };
    const plan = parsePlan(run(actualFixture, "--to", newPin));
    const entry = plan.entries.find((item: any) => item.target === "plugins/cstack/tool.sh");
    expect(plan.summary.changed).toBe(1);
    expect(entry.state).toBe("clean-update");
    expect(entry.snapshots[0].oldMode).toBe(0o644);
    expect(entry.snapshots[0].newMode).toBe(0o755);
    expect(entry.candidateMode).toBe(0o755);
    const resolutionPath = join(fixture.workspace, "resolution.json");
    writeFileSync(resolutionPath, JSON.stringify(plan.resolutionTemplate));
    const applied = run(actualFixture, "--to", newPin, "--apply", "--resolutions", resolutionPath);
    if (applied.exitCode !== 0) throw new Error(applied.stderr.toString());
    expect(statSync(target).mode & 0o111).not.toBe(0);
    expect(JSON.parse(readFileSync(join(fixture.workspace, "UPSTREAM.json"), "utf8")).commit).toBe(newPin);
  } finally {
    rmSync(fixture.workspace, { recursive: true, force: true });
    rmSync(fixture.source, { recursive: true, force: true });
  }
});

test("une nouvelle source exécutable reçoit le mode source", () => {
  const fixture = makeFixture();
  try {
    const base = "base\n";
    const executable = "#!/bin/sh\necho new\n";
    writeSource(fixture.source, { "pstack/base.md": base });
    const oldPin = commit(fixture.source, "base");
    writeSource(fixture.source, { "pstack/new.sh": executable });
    chmodSync(join(fixture.source, "pstack/new.sh"), 0o755);
    const newPin = commit(fixture.source, "new executable");
    const target = join(fixture.workspace, "plugins/cstack/base.md");
    mkdirSync(join(target, ".."), { recursive: true });
    writeFileSync(target, base);
    prepareWorkspace(fixture.workspace, fixture.source, oldPin, { "base.md": base }, [{
      source: "pstack/base.md", target: "plugins/cstack/base.md", status: "retained", reason: "base MIT",
    }]);
    const actualFixture = { workspace: fixture.workspace, source: fixture.source };
    const plan = parsePlan(run(actualFixture, "--to", newPin));
    const resolution = plan.resolutionTemplate;
    const group = resolution.groups.find((item: any) => item.sources.includes("pstack/new.sh"));
    group.target = "plugins/cstack/new.sh";
    group.status = "retained";
    group.mappingReason = "script approuvé";
    group.action = "write";
    group.reason = "nouveau script exécutable relu";
    const resultPath = join(fixture.workspace, "new-result.sh");
    writeFileSync(resultPath, executable);
    group.result = { path: resultPath, blob: blob(readFileSync(resultPath)) };
    const resolutionPath = join(fixture.workspace, "resolution.json");
    writeFileSync(resolutionPath, JSON.stringify(resolution));
    const applied = run(actualFixture, "--to", newPin, "--apply", "--resolutions", resolutionPath);
    if (applied.exitCode !== 0) throw new Error(applied.stderr.toString());
    expect(statSync(join(fixture.workspace, "plugins/cstack/new.sh")).mode & 0o111).not.toBe(0);
  } finally {
    rmSync(fixture.workspace, { recursive: true, force: true });
    rmSync(fixture.source, { recursive: true, force: true });
  }
});

test("un bit exécutable local divergent invalide un retained", () => {
  const fixture = makeFixture();
  try {
    const content = "#!/bin/sh\necho ok\n";
    writeSource(fixture.source, { "pstack/tool.sh": content });
    chmodSync(join(fixture.source, "pstack/tool.sh"), 0o644);
    const pin = commit(fixture.source, "non executable");
    const target = join(fixture.workspace, "plugins/cstack/tool.sh");
    mkdirSync(join(target, ".."), { recursive: true });
    writeFileSync(target, content);
    chmodSync(target, 0o755);
    prepareWorkspace(fixture.workspace, fixture.source, pin, { "tool.sh": content }, [{
      source: "pstack/tool.sh", target: "plugins/cstack/tool.sh", status: "retained", reason: "script MIT",
    }]);
    const result = run({ workspace: fixture.workspace, source: fixture.source }, "--to", pin);
    expect(result.exitCode).not.toBe(0);
    expect(result.stderr.toString()).toContain("retained invalide");
  } finally {
    rmSync(fixture.workspace, { recursive: true, force: true });
    rmSync(fixture.source, { recursive: true, force: true });
  }
});

test("un conflit Git réel refuse apply et ne bouge ni cible ni pin", () => {
  const fixture = makeFixture();
  try {
    const oldFiles = { "conflict.md": "value base\n" };
    writeSource(fixture.source, { "pstack/conflict.md": oldFiles["conflict.md"] });
    const oldPin = commit(fixture.source, "old");
    writeSource(fixture.source, { "pstack/conflict.md": "value upstream\n" });
    const newPin = commit(fixture.source, "new");
    const target = join(fixture.workspace, "plugins/cstack/conflict.md");
    mkdirSync(join(target, ".."), { recursive: true });
    writeFileSync(target, "value local\n");
    prepareWorkspace(fixture.workspace, fixture.source, oldPin, oldFiles, [{ source: "pstack/conflict.md", target: "plugins/cstack/conflict.md", status: "ported", reason: "français" }]);
    const actualFixture = { workspace: fixture.workspace, source: fixture.source };
    const plan = parsePlan(run(actualFixture, "--to", newPin));
    expect(plan.summary.conflicts).toBe(1);
    expect(typeof plan.summary.unresolved).toBe("number");
    const before = readFileSync(target);
    const resolution = plan.resolutionTemplate;
    resolution.groups[0].action = "map";
    resolution.groups[0].reason = "conflit reconnu, résolution encore requise";
    const resolutionPath = join(fixture.workspace, "resolution.json");
    writeFileSync(resolutionPath, JSON.stringify(resolution));
    const result = run(actualFixture, "--to", newPin, "--apply", "--resolutions", resolutionPath);
    expect(result.exitCode).not.toBe(0);
    expect(result.stderr.toString()).toContain("conflits");
    expect(readFileSync(target)).toEqual(before);
    expect(JSON.parse(readFileSync(join(fixture.workspace, "UPSTREAM.json"), "utf8")).commit).toBe(oldPin);

    const approved = JSON.parse(readFileSync(resolutionPath, "utf8"));
    const resultPath = join(fixture.workspace, "resolved.md");
    writeFileSync(resultPath, "value résolu\n");
    approved.groups[0].action = "map";
    approved.groups[0].result = { path: resultPath, blob: blob(readFileSync(resultPath)) };
    writeFileSync(resolutionPath, JSON.stringify(approved));
    const applied = run(actualFixture, "--to", newPin, "--apply", "--resolutions", resolutionPath);
    if (applied.exitCode !== 0) throw new Error(applied.stderr.toString());
    expect(applied.exitCode).toBe(0);
    expect(readFileSync(target, "utf8")).toBe("value résolu\n");
    expect(JSON.parse(readFileSync(join(fixture.workspace, "UPSTREAM.json"), "utf8")).commit).toBe(newPin);
  } finally {
    rmSync(fixture.workspace, { recursive: true, force: true });
    rmSync(fixture.source, { recursive: true, force: true });
  }
});

test("résolution périmée et source Git mismatch sont refusées", () => {
  const fixture = fixtureWithChanges();
  try {
    const plan = parsePlan(run(fixture, "--to", fixture.newPin));
    const resolution = fillResolution(fixture, plan);
    const value = JSON.parse(readFileSync(resolution, "utf8"));
    value.newPin = fixture.oldPin;
    writeFileSync(resolution, JSON.stringify(value));
    const stale = run(fixture, "--to", fixture.newPin, "--apply", "--resolutions", resolution);
    expect(stale.exitCode).not.toBe(0);
    expect(stale.stderr.toString()).toContain("résolution périmée");

    git(fixture.source, "remote", "set-url", "origin", "https://example.invalid/wrong.git");
    const mismatch = run(fixture, "--to", fixture.newPin);
    expect(mismatch.exitCode).not.toBe(0);
    expect(mismatch.stderr.toString()).toContain("source Git mismatch");
  } finally {
    rmSync(fixture.workspace, { recursive: true, force: true });
    rmSync(fixture.source, { recursive: true, force: true });
  }
});

test("un retained local modifié est refusé avant tout plan d’écriture", () => {
  const fixture = fixtureWithChanges();
  try {
    writeFileSync(join(fixture.workspace, "plugins/cstack/retained.md"), "retained local divergent\n");
    const result = run(fixture, "--to", fixture.newPin);
    expect(result.exitCode).not.toBe(0);
    expect(result.stderr.toString()).toContain("retained invalide");
    expect(JSON.parse(readFileSync(join(fixture.workspace, "UPSTREAM.json"), "utf8")).commit).toBe(fixture.oldPin);
  } finally {
    rmSync(fixture.workspace, { recursive: true, force: true });
    rmSync(fixture.source, { recursive: true, force: true });
  }
});

test.skipIf(process.getuid?.() === 0)("un échec de manifeste restaure la cible déjà écrite et nettoie les temporaires", () => {
  const fixture = fixtureWithChanges();
  try {
    const plan = parsePlan(run(fixture, "--to", fixture.newPin));
    const resolutionPath = fillResolution(fixture, plan);
    const target = join(fixture.workspace, "plugins/cstack/retained.md");
    const before = readFileSync(target);
    chmodSync(fixture.workspace, 0o555);
    const result = run(fixture, "--to", fixture.newPin, "--apply", "--resolutions", resolutionPath);
    expect(result.exitCode).not.toBe(0);
    expect(result.stderr.toString()).toContain("apply annulé et restauré");
    expect(readFileSync(target)).toEqual(before);
    expect(JSON.parse(readFileSync(join(fixture.workspace, "UPSTREAM.json"), "utf8")).commit).toBe(fixture.oldPin);
    expect(Bun.spawnSync(["find", fixture.workspace, "-name", ".sync-upstream-*.tmp", "-print"], { stdout: "pipe", stderr: "pipe" }).stdout.toString()).toBe("");
  } finally {
    chmodSync(fixture.workspace, 0o755);
    rmSync(fixture.workspace, { recursive: true, force: true });
    rmSync(fixture.source, { recursive: true, force: true });
  }
});

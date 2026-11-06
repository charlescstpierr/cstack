import { expect, test } from "bun:test";
import { createHash } from "node:crypto";
import { mkdtemp, writeFile, rm, readdir, readFile, symlink } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve, join, relative } from "node:path";
import { prepareT3, parseT3Selection, type T3Selection } from "./prepare.ts";
import { main } from "./runtime.ts";

const pluginRoot = resolve(import.meta.dir, "../../../..");
const selection = { runtime: "t3", providerInstanceId: "synthetic-provider", model: "synthetic-model", options: { effort: "fixture-high" } } satisfies T3Selection;

test("preparation preserves target and exact snapshot without process launch or output writes", async () => {
  const root = await mkdtemp(join(tmpdir(), "cstack-t3-prepare-"));
  const oldPath = process.env.PATH;
  try {
    const brief = join(root, "brief.md");
    const content = "GOAL\nInspect this frozen fixture only.\n";
    await writeFile(brief, content);
    const { runtime: _, ...target } = selection;
    const binding = { coordinatorScope: { ...target, threadId: "fixture-thread", projectId: "fixture-project",
      link: "opaque-link", runtimeMode: "full-access", interactionMode: "default" }, catalogSha256: "a".repeat(64), target };
    const request = { selection, binding, brief_file: brief, context_files: [], skills: [], skill_references: [],
      scope: "fixture only", acceptance: "cite file hashes", evidence: "HEAD/status before and after",
      snapshot: [{ path: brief, sha256: createHash("sha256").update(content).digest("hex") }], transport_limit_bytes: 1024 * 1024 };
    process.env.PATH = "";
    const result = await prepareT3(request, pluginRoot);
    await expect(prepareT3({ ...request, brief_file: relative(process.cwd(), brief) }, pluginRoot)).rejects.toThrow("absolu");
    expect(result.status).toBe("prepared");
    expect(result.binding).toEqual(binding);
    await expect(prepareT3({ ...request, binding: undefined }, pluginRoot)).rejects.toThrow("binding");
    await expect(prepareT3({ ...request, binding: { ...binding, target: { ...target, model: "other" } } }, pluginRoot)).rejects.toThrow("différent");
    const special = JSON.parse('{"__proto__":true,"effort":"fixture-high"}');
    const reordered = JSON.parse('{"effort":"fixture-high","__proto__":true}');
    const bound = await prepareT3({ ...request, selection: { ...selection, options: special },
      binding: { ...binding, target: { ...target, options: reordered } } }, pluginRoot);
    expect(Object.hasOwn(bound.binding.target.options, "__proto__")).toBe(true);
    expect(bound.binding.target.options.__proto__).toBe(true);
    await expect(prepareT3({ ...request, binding: { ...binding, target: { ...target, options: { effort: true } } } }, pluginRoot)).rejects.toThrow("différent");
    expect(result.selection).toEqual(selection);
    expect(result.context.files).toEqual(request.snapshot);
    expect(result.prompt).toContain("Contrat T3 pour cstack");
    expect(result.prompt).toContain(content);
    const alias = join(root, "brief-alias.md");
    await symlink(brief, alias);
    const aliased = await prepareT3({ ...request, brief_file: alias,
      snapshot: [{ path: alias, sha256: request.snapshot[0].sha256 }] }, pluginRoot);
    expect(aliased.context.files).toEqual(request.snapshot);
    await rm(alias);
    expect(result.sha256).toBe(createHash("sha256").update(result.prompt).digest("hex"));
    await expect(prepareT3({ ...request, transport_limit_bytes: 1 }, pluginRoot)).rejects.toThrow("aucune troncature");
    await writeFile(brief, "mutated");
    await expect(prepareT3(request, pluginRoot)).rejects.toThrow("snapshot différent");
    await expect(prepareT3({ ...request, snapshot: [] }, pluginRoot)).rejects.toThrow("snapshot exact");
    await writeFile(brief, content);
    expect(await readdir(root)).toEqual(["brief.md"]);
    await expect(prepareT3({ ...request, skills: ["missing-required-skill"] }, pluginRoot)).rejects.toThrow();
  } finally {
    process.env.PATH = oldPath;
    await rm(root, { recursive: true, force: true });
  }
});

test("CLI runner refuses T3 before any process or request dependent filesystem operation", async () => {
  const root = await mkdtemp(join(tmpdir(), "cstack-t3-reject-"));
  try {
    const request = join(root, "request.json");
    await writeFile(request, JSON.stringify({ selection, brief_file: "/absent", cwd: "/absent", output_dir: "/absent", permissions: "read-only" }));
    const errors: string[] = [];
    expect(await main(["run", "--request", request], { stdout: () => {}, stderr: (s) => errors.push(s) })).toBe(64);
    expect(errors.join(" ")).toContain("aucun processus CLI");
  } finally { await rm(root, { recursive: true, force: true }); }
});

test("T3 preparation refuses CLI and legacy keys", () => {
  expect(() => parseT3Selection({ ...selection, runtime: "claude-code" })).toThrow();
  expect(() => parseT3Selection({ ...selection, reasoning_effort: "high" })).toThrow();
});


test("shared T3 selection contract agrees with Python parser", async () => {
  const cases: unknown = JSON.parse(await readFile(resolve(import.meta.dir, "../../../../../../tests/fixtures/t3-selections.json"), "utf8"));
  if (!Array.isArray(cases)) throw new Error("fixture list required");
  for (const row of cases) {
    if (row.valid) expect(parseT3Selection(row.selection)).toEqual(row.selection);
    else expect(() => parseT3Selection(row.selection)).toThrow();
  }
});

test("Python preflight binding passes through preparation and rejects a changed target", async () => {
  const root = await mkdtemp(join(tmpdir(), "cstack-t3-binding-"));
  try {
    const repo = resolve(pluginRoot, "../..");
    const catalog = JSON.parse(await readFile(join(repo, "tests/fixtures/t3-normalizer/snapshot.json"), "utf8"));
    const context = { schema: "cstack.t3-context/2", expectedCoordinator: catalog.coordinator,
      snapshotSha256: catalog.sha256, capabilitiesSha256: catalog.sources.capabilities.sha256,
      threadSha256: catalog.sources.thread.sha256, revalidated: true,
      revalidatedAt: "2026-11-05T00:36:23.734Z", expiresAt: "2099-01-01T00:00:00Z" };
    const catalogPath = join(root, "catalog.json");
    const contextPath = join(root, "context.json");
    await writeFile(catalogPath, JSON.stringify(catalog));
    await writeFile(contextPath, JSON.stringify(context));
    const processResult = Bun.spawnSync(["python3", join(pluginRoot, "skills/setup-cstack/scripts/models.py"),
      "--workspace", root, "--host", "t3", "--catalog", catalogPath, "--host-context", contextPath,
      "preflight", "how explorer"]);
    expect(processResult.exitCode).toBe(0);
    const row = JSON.parse(processResult.stdout.toString()).positions["how explorer"][0];
    const brief = join(root, "brief.md");
    const content = "Inspect the public fixture only.\n";
    await writeFile(brief, content);
    const request = { selection: { runtime: "t3", ...row.target }, binding: row.binding,
      brief_file: brief, context_files: [], skills: [], skill_references: [], scope: "fixture only",
      acceptance: "exact binding", evidence: "hash", transport_limit_bytes: 1024 * 1024,
      snapshot: [{ path: brief, sha256: createHash("sha256").update(content).digest("hex") }] };
    const result = await prepareT3(request, pluginRoot);
    expect(result.binding).toEqual(row.binding);
    await expect(prepareT3({ ...request, selection: { ...request.selection, model: "changed" } }, pluginRoot)).rejects.toThrow("différent");
  } finally { await rm(root, { recursive: true, force: true }); }
});


test("prepare CLI drains a large JSON response through a pipe before exiting", async () => {
  const root = await mkdtemp(join(tmpdir(), "cstack-t3-pipe-"));
  try {
    const brief = join(root, "brief.md");
    const content = "transport data\n".repeat(10000) + "FINAL_TRANSPORT_MARKER\n";
    await writeFile(brief, content);
    const { runtime: _, ...target } = selection;
    const binding = { coordinatorScope: { ...target, threadId: "fixture-thread", projectId: "fixture-project",
      link: "opaque-link", runtimeMode: "full-access", interactionMode: "default" }, catalogSha256: "a".repeat(64), target };
    const request = join(root, "request.json");
    await writeFile(request, JSON.stringify({ selection, binding, brief_file: brief, context_files: [],
      skills: [], skill_references: [], scope: "fixture", acceptance: "complete output", evidence: "pipe JSON",
      snapshot: [{ path: brief, sha256: createHash("sha256").update(content).digest("hex") }], transport_limit_bytes: 1024 * 1024 }));
    const child = Bun.spawn([process.execPath, resolve(import.meta.dir, "runtime.ts"), "prepare", "--request", request],
      { stdout: "pipe", stderr: "pipe" });
    const [output, errors, status] = await Promise.all([(async () => { await Bun.sleep(100); return await new Response(child.stdout).text(); })(), new Response(child.stderr).text(), child.exited]);
    expect(status).toBe(0);
    expect(errors).toBe("");
    const result = JSON.parse(output);
    expect(result.bytes).toBeGreaterThan(65536);
    expect(result.prompt).toContain(content);
    expect(result.sha256).toBe(createHash("sha256").update(result.prompt).digest("hex"));
  } finally { await rm(root, { recursive: true, force: true }); }
});

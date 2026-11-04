import { expect, test } from "bun:test";
import { createHash } from "node:crypto";
import { mkdtemp, writeFile, rm, readdir, readFile } from "node:fs/promises";
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
    const request = { selection, brief_file: brief, context_files: [], skills: [], skill_references: [],
      scope: "fixture only", acceptance: "cite file hashes", evidence: "HEAD/status before and after",
      snapshot: [{ path: brief, sha256: createHash("sha256").update(content).digest("hex") }], transport_limit_bytes: 1024 * 1024 };
    process.env.PATH = "";
    const result = await prepareT3(request, pluginRoot);
    await expect(prepareT3({ ...request, brief_file: relative(process.cwd(), brief) }, pluginRoot)).rejects.toThrow("absolu");
    expect(result.status).toBe("prepared");
    expect(result.selection).toEqual(selection);
    expect(result.context.files).toEqual(request.snapshot);
    expect(result.prompt).toContain("Contrat T3 pour cstack");
    expect(result.prompt).toContain(content);
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

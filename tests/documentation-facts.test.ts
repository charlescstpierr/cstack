import { test, expect } from "bun:test";
import { cpSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

const root = resolve(import.meta.dir, "..");
const generator = join(root, "scripts/generate-facts.mjs");
const validator = join(root, "scripts/validate.ts");
const artifact = join(root, "docs/GENERATED-FACTS.md");

function run(...args: string[]) {
  return Bun.spawnSync(["bun", generator, ...args], { cwd: root, stdout: "pipe", stderr: "pipe" });
}

function runValidator(directory: string) {
  return Bun.spawnSync(["bun", validator, directory], { cwd: root, stdout: "pipe", stderr: "pipe" });
}

function fixture() {
  const directory = mkdtempSync(join(tmpdir(), "cstack-facts-"));
  mkdirSync(join(directory, "scripts"), { recursive: true });
  for (const path of ["UPSTREAM.json", "PORTING.json", "README.md", "CHANGELOG.md", "docs", ".agents", ".claude-plugin", "plugins/cstack"]) {
    cpSync(join(root, path), join(directory, path), {
      recursive: true,
      filter: (source) => !source.split("/").some((part) => [".git", "node_modules", "__pycache__"].includes(part)),
    });
  }
  cpSync(validator, join(directory, "scripts/validate.ts"));
  return directory;
}

function numberRow(text: string, label: string) {
  const match = text.match(new RegExp(`\\| ${label} \\| (\\d+) \\|`));
  expect(match).not.toBeNull();
  return Number(match?.[1] ?? "-1");
}

test("les faits générés couvrent le pin, l’arbre et les statuts de portage", () => {
  const result = run("--check");
  expect(result.exitCode).toBe(0);

  const text = readFileSync(artifact, "utf8");
  expect(text).toMatch(/\| Commit amont \| `[0-9a-f]{40}` \|/);
  expect(text).toMatch(/\| Version du plugin \| \d+\.\d+\.\d+ \|/);
  const sourceCount = numberRow(text, "Fichiers source amont");
  expect(numberRow(text, "Compétences")).toBeGreaterThan(0);
  expect(numberRow(text, "Principes internes")).toBeGreaterThan(0);
  expect(numberRow(text, "Guides d’exécution")).toBeGreaterThan(0);
  expect(
    ["ported", "retained", "replaced", "unsupported"]
      .map((status) => numberRow(text, `Fichiers \`${status}\``))
      .reduce((sum, count) => sum + count, 0),
  ).toBe(sourceCount);
});

test("--check refuse un artefact périmé sans modifier le fichier", () => {
  const directory = fixture();
  try {
    const path = join(directory, "docs/GENERATED-FACTS.md");
    const original = readFileSync(path, "utf8");
    const current = /\| Compétences \| (\d+) \|/.exec(original);
    expect(current).not.toBeNull();
    const stale = original.replace(current?.[0] ?? "", `| Compétences | ${Number(current?.[1] ?? "-1") + 1} |`);
    writeFileSync(path, stale);

    const result = run("--root", directory, "--check");

    expect(result.exitCode).toBe(1);
    expect(result.stderr.toString()).toContain("GENERATED-FACTS.md");
    expect(readFileSync(path, "utf8")).toBe(stale);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

test("--check vérifie les faits courants du pin et du guide", () => {
  const directory = fixture();
  try {
    const path = join(directory, "plugins/cstack/docs/guide/02-cstack.md");
    const original = readFileSync(path, "utf8");
    const current = /Le routeur en liste (\d+)\./.exec(original);
    expect(current).not.toBeNull();
    const replacement = `Le routeur en liste ${Number(current?.[1] ?? "-1") + 1}.`;
    writeFileSync(path, original.replace(current?.[0] ?? "", replacement));

    const result = run("--root", directory, "--check");

    expect(result.exitCode).toBe(1);
    expect(result.stderr.toString()).toContain("plugins/cstack/docs/guide/02-cstack.md");
    expect(readFileSync(path, "utf8")).not.toBe(original);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

test("le validateur partagé refuse un compte documentaire faux et accepte l’apostrophe courbe", () => {
  const directory = fixture();
  try {
    const readme = join(directory, "README.md");
    const originalReadme = readFileSync(readme, "utf8");
    const count = /Le catalogue contient (\d+) (compétences|skills)\./.exec(originalReadme);
    expect(count).not.toBeNull();
    writeFileSync(
      readme,
      originalReadme.replace(
        count?.[0] ?? "",
        `Le catalogue contient ${Number(count?.[1] ?? "-1") + 1} ${count?.[2] ?? "compétences"}.`,
      ),
    );
    const stale = runValidator(directory);
    expect(stale.exitCode).toBe(1);
    expect(stale.stderr.toString()).toContain("nombre de skills cité");

    writeFileSync(readme, originalReadme);
    const report = join(directory, "docs/VERIFICATION.md");
    const originalReport = readFileSync(report, "utf8");
    const reportCount = /(\d+) (skills|compétences)/.exec(originalReport);
    expect(reportCount).not.toBeNull();
    writeFileSync(
      report,
      originalReport.replace(
        reportCount?.[0] ?? "",
        `${Number(reportCount?.[1] ?? "-1") + 1} ${reportCount?.[2] ?? "skills"}`,
      ),
    );
    const staleReport = runValidator(directory);
    expect(staleReport.exitCode).toBe(1);
    expect(staleReport.stderr.toString()).toContain("nombre de skills cité");

    writeFileSync(report, originalReport);
    const apostrophe = /(\d+ guides )d'exécution/.exec(originalReport);
    expect(apostrophe).not.toBeNull();
    writeFileSync(report, originalReport.replace(apostrophe?.[0] ?? "", `${apostrophe?.[1] ?? ""}d’exécution`));
    const curved = runValidator(directory);
    expect(curved.exitCode).toBe(0);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

test("la génération dérive les statuts du portage au lieu de les figer dans le test", () => {
  const directory = fixture();
  try {
    const path = join(directory, "PORTING.json");
    const porting = JSON.parse(readFileSync(path, "utf8"));
    const original = readFileSync(join(directory, "docs/GENERATED-FACTS.md"), "utf8");
    const previousReplaced = numberRow(original, "Fichiers `replaced`");
    const previousPorted = numberRow(original, "Fichiers `ported`");
    const item = porting.files.find((entry: { status: string }) => entry.status === "ported");
    expect(item).toBeDefined();
    item.status = "replaced";
    writeFileSync(path, JSON.stringify(porting));

    const result = run("--root", directory);
    expect(result.exitCode).toBe(0);
    const generated = readFileSync(join(directory, "docs/GENERATED-FACTS.md"), "utf8");
    expect(numberRow(generated, "Fichiers `replaced`")).toBe(previousReplaced + 1);
    expect(numberRow(generated, "Fichiers `ported`")).toBe(previousPorted - 1);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

test.each([
  ["Source", "https://github.com/cursor/plugins/tree/outdated/pstack"],
  ["Upstream commit", "`0000000000000000000000000000000000000000`"],
  ["Upstream manifest version", "`0.0.0`"],
])("le contrôle des faits refuse une provenance NOTICE périmée : %s", (field, staleValue) => {
  const directory = fixture();
  try {
    const path = join(directory, "plugins/cstack/NOTICE.md");
    const original = readFileSync(path, "utf8");
    const stale = original.replace(new RegExp(`^- ${field}: .+$`, "m"), `- ${field}: ${staleValue}`);
    expect(stale).not.toBe(original);
    writeFileSync(path, stale);
    const result = run("--root", directory, "--check");
    expect(result.exitCode).toBe(1);
    expect(result.stderr.toString()).toContain("plugins/cstack/NOTICE.md");
    expect(readFileSync(path, "utf8")).toBe(stale);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

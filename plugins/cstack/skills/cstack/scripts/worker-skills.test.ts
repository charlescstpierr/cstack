import { describe, expect, it } from "bun:test";
import { readdir, chmod, mkdir, mkdtemp, rm, symlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { loadWorkerSkills } from "./worker-skills.ts";

async function pluginFixture(): Promise<string> {
  const root = await mkdtemp(join(tmpdir(), "cstack-worker-skills-"));
  await mkdir(join(root, "skills/cstack/references/agents"), { recursive: true });
  await mkdir(join(root, "skills/cstack/references/principles"), { recursive: true });
  await mkdir(join(root, "skills/cstack/playbooks"), { recursive: true });
  await writeFile(join(root, "skills/cstack/references/agents/cstack-agent.md"), "COMMON AGENT\n");
  await writeFile(join(root, "skills/cstack/references/runtime-workers.md"), "RUNTIME WORKERS\n[Runtime](codex-runtime.md)\n");
  await writeFile(join(root, "skills/cstack/references/codex-runtime.md"), "CODEX RUNTIME\n");
  await writeFile(join(root, "skills/cstack/references/principles/prove-it-works.md"), "PROVE IT\n");
  await writeFile(join(root, "skills/cstack/playbooks/worktree-cleanup.md"), "WORKTREE CLEANUP\n");

  await mkdir(join(root, "skills/alpha/references/nested"), { recursive: true });
  await mkdir(join(root, "skills/alpha/scripts"), { recursive: true });
  await writeFile(join(root, "skills/alpha/SKILL.md"), "ALPHA\n[Guide](references/guide.md)\n[Runtime](../cstack/references/runtime-workers.md)\n[Principle](../cstack/references/principles/prove-it-works.md)\n[Playbook](../cstack/playbooks/worktree-cleanup.md)\n[Beta](../beta/SKILL.md)\n[Ignored](scripts/tool.sh)\n");
  await writeFile(join(root, "skills/alpha/references/guide.md"), "GUIDE\n[Nested](nested/deep.md)\n[Cycle](cycle.md)\n");
  await writeFile(join(root, "skills/alpha/references/cycle.md"), "CYCLE\n[Guide](guide.md)\n");
  await writeFile(join(root, "skills/alpha/references/nested/deep.md"), "DEEP\n");
  await writeFile(join(root, "skills/alpha/scripts/tool.sh"), "echo no\n");

  await mkdir(join(root, "skills/beta/references"), { recursive: true });
  await writeFile(join(root, "skills/beta/SKILL.md"), "BETA\n");
  await writeFile(join(root, "skills/beta/references/extra.md"), "EXTRA\n");

  await mkdir(join(root, "skills/why/references/sources"), { recursive: true });
  await writeFile(join(root, "skills/why/SKILL.md"), "WHY\n`references/sources/<source>.md`\n");
  await writeFile(join(root, "skills/why/references/source-playbook.md"), "SOURCE PLAYBOOK\n");
  await writeFile(join(root, "skills/why/references/sources/code-archaeology.md"), "CODE ARCHAEOLOGY\n");
  await writeFile(join(root, "skills/why/references/sources/not-markdown.txt"), "NO\n");
  return root;
}

describe("worker skill bundles", () => {
  it("charge les mêmes sources textuelles dans un bundle stable", async () => {
    const root = await pluginFixture();
    try {
      const first = await loadWorkerSkills({ pluginRoot: root, names: ["alpha"] });
      const second = await loadWorkerSkills({ pluginRoot: root, names: ["alpha"] });
      const paths = first.files.map((file) => file.path);
      expect(first.sha256).toBe(second.sha256);
      expect(first.text).toContain("COMMON AGENT");
      expect(first.text).toContain("ALPHA");
      expect(first.text).toContain("GUIDE");
      expect(first.text).toContain("DEEP");
      expect(first.text).toContain("RUNTIME WORKERS");
      expect(first.text).toContain("CODEX RUNTIME");
      expect(first.text).toContain("PROVE IT");
      expect(first.text).toContain("WORKTREE CLEANUP");
      expect(first.text).not.toContain("echo no");
      expect(first.text).not.toContain("BETA");
      expect(first.text).toContain("do not grant extra delegation rights");
      expect(paths).toContain("skills/cstack/references/agents/cstack-agent.md");
      expect(paths).toContain("skills/alpha/SKILL.md");
      expect(paths).toContain("skills/alpha/references/cycle.md");
      expect(paths).toContain("skills/alpha/references/guide.md");
      expect(paths).toContain("skills/cstack/playbooks/worktree-cleanup.md");
      expect(paths).toContain("skills/cstack/references/principles/prove-it-works.md");
      expect(paths).toContain("skills/cstack/references/runtime-workers.md");
      expect(paths).toContain("skills/alpha/references/nested/deep.md");
      expect(paths).toContain("skills/cstack/references/codex-runtime.md");
      expect(new Set(paths).size).toBe(paths.length);
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });

  it("inclut seulement les references markdown directes quand aucun lien n'est nommé", async () => {
    const root = await pluginFixture();
    try {
      const bundle = await loadWorkerSkills({ pluginRoot: root, names: ["beta"] });
      expect(bundle.text).toContain("BETA");
      expect(bundle.text).toContain("EXTRA");
      expect(bundle.files.map((file) => file.path)).toEqual([
        "skills/cstack/references/agents/cstack-agent.md",
        "skills/beta/SKILL.md",
        "skills/beta/references/extra.md",
      ]);
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });

  it("charge une référence explicite de skill sans récursion globale", async () => {
    const root = await pluginFixture();
    try {
      const bundle = await loadWorkerSkills({
        pluginRoot: root,
        names: ["why"],
        skillReferences: ["why/references/sources/code-archaeology.md"],
      });
      expect(bundle.text).toContain("WHY");
      expect(bundle.text).toContain("SOURCE PLAYBOOK");
      expect(bundle.text).toContain("CODE ARCHAEOLOGY");
      expect(bundle.text).not.toContain("not-markdown");
      expect(bundle.files.map((file) => file.path)).toContain("skills/why/references/sources/code-archaeology.md");
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });

  it("refuse traversal, doublons, listes trop longues et liens sortants", async () => {
    const root = await pluginFixture();
    try {
      await expect(loadWorkerSkills({ pluginRoot: root, names: ["../alpha"] })).rejects.toThrow();
      await expect(loadWorkerSkills({ pluginRoot: root, names: ["alpha", "alpha"] })).rejects.toThrow();
      await expect(loadWorkerSkills({ pluginRoot: root, names: ["a", "b", "c", "d", "e", "f", "g", "h", "i"] })).rejects.toThrow();
      const outside = join(root, "outside.md");
      await writeFile(outside, "outside\n");
      await symlink(outside, join(root, "skills/alpha/references/out.md"));
      await writeFile(join(root, "skills/alpha/SKILL.md"), "ALPHA\n[Out](references/out.md)\n");
      await expect(loadWorkerSkills({ pluginRoot: root, names: ["alpha"] })).rejects.toThrow(/lien symbolique|hors/);
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });

  it("refuse les références explicites hors périmètre, non markdown, URLs et doublons", async () => {
    const root = await pluginFixture();
    try {
      await expect(loadWorkerSkills({ pluginRoot: root, names: ["why"], skillReferences: ["../why/references/source-playbook.md"] })).rejects.toThrow(/invalide/);
      await expect(loadWorkerSkills({ pluginRoot: root, names: ["why"], skillReferences: ["https://example.com/file.md"] })).rejects.toThrow(/URL/);
      await expect(loadWorkerSkills({ pluginRoot: root, names: ["why"], skillReferences: ["why/references/sources/not-markdown.txt"] })).rejects.toThrow(/markdown/);
      await expect(loadWorkerSkills({ pluginRoot: root, names: ["why"], skillReferences: ["alpha/references/guide.md"] })).rejects.toThrow(/ne concerne pas/);
      await expect(loadWorkerSkills({ pluginRoot: root, names: ["why"], skillReferences: ["why/SKILL.md"] })).rejects.toThrow(/SKILL.md/);
      await expect(loadWorkerSkills({ pluginRoot: root, names: ["why"], skillReferences: ["why/references/source-playbook.md", "why/references/source-playbook.md"] })).rejects.toThrow(/dupliquée/);
      await expect(loadWorkerSkills({ pluginRoot: root, names: ["why"], skillReferences: Array.from({ length: 17 }, (_, index) => `why/references/sources/${index}.md`) })).rejects.toThrow(/maximum 16/);
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });

  // root ignore chmod 000 : l'erreur de permission ne peut pas être provoquée.
  it.skipIf(process.getuid?.() === 0)("ne masque pas les erreurs de permissions du dossier references", async () => {
    const root = await pluginFixture();
    try {
      await mkdir(join(root, "skills/locked/references"), { recursive: true });
      await writeFile(join(root, "skills/locked/SKILL.md"), "LOCKED\n");
      await chmod(join(root, "skills/locked/references"), 0o000);
      try {
        await expect(loadWorkerSkills({ pluginRoot: root, names: ["locked"] })).rejects.toThrow();
      } finally {
        await chmod(join(root, "skills/locked/references"), 0o700);
      }
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });

  it("borne la taille cumulée du bundle", async () => {
    const root = await pluginFixture();
    try {
      await writeFile(join(root, "skills/alpha/references/guide.md"), "x".repeat(257 * 1024));
      await expect(loadWorkerSkills({ pluginRoot: root, names: ["alpha"] })).rejects.toThrow(/trop grand/);
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });

  it("inclut les références partagées du vrai skill architect", async () => {
    const pluginRoot = join(import.meta.dir, "../../..");
    const bundle = await loadWorkerSkills({ pluginRoot, names: ["architect"] });
    const paths = bundle.files.map((file) => file.path);
    expect(paths).toContain("skills/cstack/references/runtime-workers.md");
    expect(paths).toContain("skills/cstack/references/codex-runtime.md");
    expect(paths).toContain("skills/cstack/references/principles/exhaust-the-design-space.md");
    expect(paths).toContain("skills/architect/references/runner-prompt.md");
  });
});

it("ne charge pas les liens d'exemple à l'intérieur des blocs de code Markdown", async () => {
  const root = await pluginFixture();
  try {
    await writeFile(join(root, "skills/cstack/references/shared.md"), "Shared rule\n");
    await writeFile(join(root, "skills/alpha/references/guide.md"), [
      "GUIDE",
      "```markdown", "[Template](tickets/<id>.md)", "```",
      "~~~~markdown", "[Example](../../outside.md)", "~~~~~",
      "[Real shared rule](../../cstack/references/shared.md)",
    ].join("\n"));
    const bundle = await loadWorkerSkills({ pluginRoot: root, names: ["alpha"] });
    expect(bundle.text).toContain("tickets/<id>.md");
    expect(bundle.files.some((file) => file.path.includes("tickets/"))).toBe(false);
    expect(bundle.files.some((file) => file.path.endsWith("cstack/references/shared.md"))).toBe(true);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

it("construit un bundle exploitable pour chaque skill livré, dont les templates Horizon", async () => {
  const pluginRoot = join(import.meta.dir, "../../..");
  const names = (await readdir(join(pluginRoot, "skills"), { withFileTypes: true }))
    .filter((entry) => entry.isDirectory()).map((entry) => entry.name);
  for (const name of names) {
    const bundle = await loadWorkerSkills({ pluginRoot, names: [name] });
    expect(bundle.files.some((file) => file.path === `skills/${name}/SKILL.md`)).toBe(true);
  }
});


it("T3 bundles retain selected task sources and replace Codex runtime traversal", async () => {
  const pluginRoot = resolve(import.meta.dir, "../../..");
  const bundle = await loadWorkerSkills({ pluginRoot, names: ["how"], host: "t3",
    skillReferences: ["cstack/references/runtime/t3.md", "cstack/references/principles/prove-it-works.md"] });
  const paths = bundle.files.map((file) => file.path);
  expect(paths).toContain("skills/how/SKILL.md");
  expect(paths).toContain("skills/how/references/explorer-prompt.md");
  expect(paths).toContain("skills/how/references/explainer-prompt.md");
  expect(paths).toContain("skills/cstack/references/agents/cstack-agent.md");
  expect(paths).toContain("skills/cstack/references/runtime/t3.md");
  expect(paths).toContain("skills/cstack/references/principles/prove-it-works.md");
  expect(paths.filter((path) => path.startsWith("skills/cstack/references/runtime/"))).toEqual(["skills/cstack/references/runtime/t3.md"]);
  expect(paths).not.toContain("skills/cstack/references/runtime-workers.md");
  expect(paths).not.toContain("skills/cstack/references/codex-runtime.md");
  await expect(loadWorkerSkills({ pluginRoot, names: [], host: "t3",
    skillReferences: ["cstack/references/runtime/base.md"] })).rejects.toThrow("remplacée");
});

import { describe, expect, it } from "bun:test";
import { mkdir, mkdtemp, rm, symlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { loadWorkerSkills } from "./worker-skills.ts";

async function pluginFixture(): Promise<string> {
  const root = await mkdtemp(join(tmpdir(), "cstack-worker-skills-"));
  await mkdir(join(root, "skills/cstack/references/agents"), { recursive: true });
  await writeFile(join(root, "skills/cstack/references/agents/cstack-agent.md"), "COMMON AGENT\n");
  await mkdir(join(root, "skills/alpha/references"), { recursive: true });
  await mkdir(join(root, "skills/alpha/scripts"), { recursive: true });
  await writeFile(join(root, "skills/alpha/SKILL.md"), "ALPHA\n[Guide](references/guide.md)\n[Ignored](scripts/tool.sh)\n");
  await writeFile(join(root, "skills/alpha/references/guide.md"), "GUIDE\n");
  await writeFile(join(root, "skills/alpha/scripts/tool.sh"), "echo no\n");
  await mkdir(join(root, "skills/beta/references"), { recursive: true });
  await writeFile(join(root, "skills/beta/SKILL.md"), "BETA\n");
  await writeFile(join(root, "skills/beta/references/extra.md"), "EXTRA\n");
  return root;
}

describe("worker skill bundles", () => {
  it("charge les mêmes sources textuelles dans un bundle stable", async () => {
    const root = await pluginFixture();
    try {
      const first = await loadWorkerSkills({ pluginRoot: root, names: ["alpha"] });
      const second = await loadWorkerSkills({ pluginRoot: root, names: ["alpha"] });
      expect(first.sha256).toBe(second.sha256);
      expect(first.text).toContain("COMMON AGENT");
      expect(first.text).toContain("ALPHA");
      expect(first.text).toContain("GUIDE");
      expect(first.text).not.toContain("echo no");
      expect(first.text).toContain("do not grant extra delegation rights");
      expect(first.files.map((file) => file.path)).toEqual([
        "skills/cstack/references/agents/cstack-agent.md",
        "skills/alpha/SKILL.md",
        "skills/alpha/references/guide.md",
      ]);
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

  it("borne la taille cumulée du bundle", async () => {
    const root = await pluginFixture();
    try {
      await writeFile(join(root, "skills/alpha/references/guide.md"), "x".repeat(257 * 1024));
      await expect(loadWorkerSkills({ pluginRoot: root, names: ["alpha"] })).rejects.toThrow(/trop grand/);
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });
});

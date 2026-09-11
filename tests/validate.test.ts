import { test, expect } from "bun:test";
import { cpSync, mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { validate } from "../scripts/validate.ts";

test("the distributable loads 28 skills and rejects unsafe or incomplete packaging", () => {
  const root = resolve(import.meta.dir, "..");
  const copy = mkdtempSync(join(tmpdir(), "cstack-package-"));
  try {
    for (const path of ["plugins", ".agents", "UPSTREAM.json", "PORTING.json"]) {
      cpSync(join(root, path), join(copy, path), {
        recursive: true,
        filter: (source) => !source.split("/").some((part) => ["node_modules", "__pycache__"].includes(part)),
      });
    }
    expect(validate(copy)).toEqual({ skills: 28, sourceFiles: 158 });
    const cases = [
      ["plugins/cstack/.codex-plugin/plugin.json", (text: string) => text.replace('"name": "cstack"', '"name": "other"'), /manifest identity/],
      ["plugins/cstack/skills/cstack/agents/openai.yaml", (text: string) => text.replace("allow_implicit_invocation: false", "allow_implicit_invocation: true"), /explicit-only/],
      ["plugins/cstack/skills/cstack/agents/openai.yaml", (text: string) => text.replace("$cstack:cstack", "$cstack"), /canonical invocation/],
      ["plugins/cstack/skills/cstack/agents/openai.yaml", (text: string) => text.replace(/short_description: .*/, 'short_description: "Route the work and verify it with"'), /truncated skill UI description/],
      ["plugins/cstack/skills/cstack/agents/openai.yaml", (text: string) => text.replace(/short_description: .*/, `short_description: "${"x".repeat(65)}"`), /skill UI description length/],
      ["plugins/cstack/skills/cstack/SKILL.md", (text: string) => `${text}\n[Missing resource](references/does-not-exist.md)\n`, /broken or escaping link/],
      ["PORTING.json", (text: string) => {
        const value = JSON.parse(text);
        value.files.pop();
        return JSON.stringify(value);
      }, /coverage is incomplete/],
      ["plugins/cstack/sources/matt-pocock.json", (text: string) => text.replace("3cca18b368ae95cdbdebbff572ccafa662551015", "unknown"), /Matt source provenance/],
      ["plugins/cstack/skills/horizon/agents/openai.yaml", (text: string) => text.replace("allow_implicit_invocation: false", "allow_implicit_invocation: true"), /explicit-only/],
      ["PORTING.json", (text: string) => text.replace(
        "plugins/cstack/skills/cstack/references/principles/prove-it-works.md",
        "plugins/cstack/skills/cstack/references/principles/fix-root-causes.md",
      ), /principle port target/],
      ["plugins/cstack/skills/cstack/SKILL.md", (text: string) => text.replace("[Prove It Works](references/principles/prove-it-works.md)", "Prove It Works"), /not discoverable/],
      ["plugins/cstack/skills/cstack/SKILL.md", (text: string) => `${text}\nUse ../principle-prove-it-works/SKILL.md.\n`, /stale principle skill reference/],
      ["plugins/cstack/skills/cstack/SKILL.md", (text: string) => `${text}\n\`\`\`\nRead principle-prove-it-works/SKILL.md\n\`\`\`\n`, /stale principle skill reference/],
      ["plugins/cstack/skills/cstack/SKILL.md", (text: string) => `${text}\n\`\`\`\n$cstack:principle-prove-it-works\n\`\`\`\n`, /stale principle invocation/],
    ] satisfies [string, (text: string) => string, RegExp][];
    for (const [path, change, error] of cases) {
      const target = join(copy, path);
      const original = readFileSync(target, "utf8");
      writeFileSync(target, change(original));
      expect(() => validate(copy)).toThrow(error);
      writeFileSync(target, original);
    }
    const reference = "plugins/cstack/skills/cstack/references/principles/prove-it-works.md";
    rmSync(join(copy, reference));
    expect(() => validate(copy)).toThrow(/missing or escaping port target/);
    cpSync(join(root, reference), join(copy, reference));
    mkdirSync(join(copy, "plugins/cstack/skills/principle-prove-it-works"), { recursive: true });
    writeFileSync(join(copy, "plugins/cstack/skills/principle-prove-it-works/SKILL.md"), "---\nname: principle-prove-it-works\ndescription: stale\n---\n");
    expect(() => validate(copy)).toThrow(/principle skill entrypoints were moved to references/);
  } finally {
    rmSync(copy, { recursive: true, force: true });
  }
});

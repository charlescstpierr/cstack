import { test, expect } from "bun:test";
import { cpSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { validate } from "../scripts/validate.ts";

test("the distributable loads 51 skills and rejects unsafe or incomplete packaging", () => {
  const root = resolve(import.meta.dir, "..");
  const copy = mkdtempSync(join(tmpdir(), "cstack-package-"));
  try {
    for (const path of ["plugins", ".agents", "UPSTREAM.json", "PORTING.json"]) {
      cpSync(join(root, path), join(copy, path), {
        recursive: true,
        filter: (source) => !source.split("/").some((part) => ["node_modules", "__pycache__"].includes(part)),
      });
    }
    expect(validate(copy)).toEqual({ skills: 51, sourceFiles: 158 });
    const cases = [
      ["plugins/cstack/.codex-plugin/plugin.json", (text: string) => text.replace('"name": "cstack"', '"name": "other"'), /manifest identity/],
      ["plugins/cstack/skills/cstack/agents/openai.yaml", (text: string) => text.replace("allow_implicit_invocation: false", "allow_implicit_invocation: true"), /explicit-only/],
      ["plugins/cstack/skills/cstack/agents/openai.yaml", (text: string) => text.replace("$cstack:cstack", "$cstack"), /canonical invocation/],
      ["plugins/cstack/skills/cstack/SKILL.md", (text: string) => `${text}\n[Missing resource](references/does-not-exist.md)\n`, /broken or escaping link/],
      ["PORTING.json", (text: string) => {
        const value = JSON.parse(text);
        value.files.pop();
        return JSON.stringify(value);
      }, /coverage is incomplete/],
      ["plugins/cstack/sources/matt-pocock.json", (text: string) => text.replace("3cca18b368ae95cdbdebbff572ccafa662551015", "unknown"), /Matt source provenance/],
      ["plugins/cstack/skills/horizon/agents/openai.yaml", (text: string) => text.replace("allow_implicit_invocation: false", "allow_implicit_invocation: true"), /explicit-only/],
    ] satisfies [string, (text: string) => string, RegExp][];
    for (const [path, change, error] of cases) {
      const target = join(copy, path);
      const original = readFileSync(target, "utf8");
      writeFileSync(target, change(original));
      expect(() => validate(copy)).toThrow(error);
      writeFileSync(target, original);
    }
  } finally {
    rmSync(copy, { recursive: true, force: true });
  }
});

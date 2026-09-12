import { test, expect } from "bun:test";
import { chmodSync, cpSync, existsSync, mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { validate } from "../scripts/validate.ts";

test("the distributable loads 29 skills and rejects unsafe or incomplete packaging", () => {
  const root = resolve(import.meta.dir, "..");
  const copy = mkdtempSync(join(tmpdir(), "cstack-package-"));
  try {
    for (const path of ["plugins", ".agents", "UPSTREAM.json", "PORTING.json"]) {
      cpSync(join(root, path), join(copy, path), {
        recursive: true,
        filter: (source) => !source.split("/").some((part) => ["node_modules", "__pycache__"].includes(part)),
      });
    }
    const manifest = JSON.parse(readFileSync(join(copy, "plugins/cstack/.codex-plugin/plugin.json"), "utf8"));
    mkdirSync(join(copy, "docs/evidence"), { recursive: true });
    const evidenceSrc = join(root, "docs/evidence", `${manifest.version}.json`);
    if (existsSync(evidenceSrc)) cpSync(evidenceSrc, join(copy, "docs/evidence", `${manifest.version}.json`));
    else writeFileSync(join(copy, "docs/evidence", `${manifest.version}.json`), "{}\n");
    if (existsSync(join(root, "CHANGELOG.md"))) cpSync(join(root, "CHANGELOG.md"), join(copy, "CHANGELOG.md"));
    if (existsSync(join(root, "docs/VERIFICATION.md"))) {
      mkdirSync(join(copy, "docs"), { recursive: true });
      cpSync(join(root, "docs/VERIFICATION.md"), join(copy, "docs/VERIFICATION.md"));
    }
    if (existsSync(join(root, "README.md"))) cpSync(join(root, "README.md"), join(copy, "README.md"));
    expect(validate(copy)).toEqual({ skills: 29, sourceFiles: 158 });
    const cases = [
      ["plugins/cstack/.codex-plugin/plugin.json", (text: string) => text.replace('"name": "cstack"', '"name": "other"'), /manifest identity/],
      ["plugins/cstack/skills/cstack/agents/openai.yaml", (text: string) => text.replace("allow_implicit_invocation: false", "allow_implicit_invocation: true"), /explicit-only/],
      ["plugins/cstack/skills/cstack/agents/openai.yaml", (text: string) => text.replace("$cstack:cstack", "$cstack"), /canonical invocation/],
      ["plugins/cstack/skills/cstack/agents/openai.yaml", (text: string) => text.replace(/short_description: .*/, 'short_description: "Route the work and verify it with"'), /truncated skill UI description/],
      ["plugins/cstack/skills/cstack/agents/openai.yaml", (text: string) => text.replace(/short_description: .*/, `short_description: "${"x".repeat(65)}"`), /skill UI description length/],
      ["plugins/cstack/skills/cstack/agents/openai.yaml", (text: string) => text.replace("interface:", "unexpected: 1\ninterface:"), /unknown skill UI key/],
      ["plugins/cstack/skills/cstack/agents/openai.yaml", (text: string) => text.replace('display_name: "cstack"', 'display_name: "router"'), /display_name must match/],
      ["plugins/cstack/skills/architect/agents/openai.yaml", (text: string) => text.replace('display_name: "architect"', 'display_name: "cstack"'), /duplicate skill display_name/],
      ["plugins/cstack/skills/cstack/SKILL.md", (text: string) => `${text}\n[Missing resource](references/does-not-exist.md)\n`, /broken or escaping link/],
      ["plugins/cstack/skills/cstack/SKILL.md", (text: string) => `${text}\nSee \`../missing-file.md\`.\n`, /unresolved plugin path/],
      ["plugins/cstack/skills/cstack/SKILL.md", (text: string) => `${text}\n[Missing heading](references/codex-runtime.md#not-a-real-heading)\n`, /missing heading for fragment/],
      ["plugins/cstack/skills/cstack/playbooks/feature.md", (text: string) => text.replace("### Feature", "## Feature"), /playbook must start with a ### title/],
      ["plugins/cstack/skills/cstack/playbooks/feature.md", (text: string) => text.replace("Follow [the Codex runtime contract](../references/codex-runtime.md).", "Skip the contract."), /playbook missing runtime-contract line/],
      ["plugins/cstack/skills/cstack/playbooks/feature.md", (text: string) => text.replace("**Reply:**", "**Answer:**"), /playbook missing Reply block/],
      ["plugins/cstack/skills/cstack/playbooks/feature.md", (text: string) => `${text}\nDo this when native capacity permits.\n`, /capacity-hedge regression/],
      ["plugins/cstack/skills/cstack/playbooks/bug-fix.md", (text: string) => text.replace("../../tdd/SKILL.md", "../../clarify/SKILL.md"), /tdd: skill is neither reachable/],
      ["plugins/cstack/LICENSE", (text: string) => `${text}\n`, /retained blob/],
      ["PORTING.json", (text: string) => {
        const value = JSON.parse(text);
        value.files.pop();
        return JSON.stringify(value);
      }, /coverage is incomplete/],
      ["PORTING.json", (text: string) => {
        const value = JSON.parse(text);
        value.original.push({ path: "plugins/cstack/does-not-exist.md", reason: "missing" });
        return JSON.stringify(value);
      }, /original path does not exist/],
      ["plugins/cstack/README.md", (text: string) => text.replace(/\b29 skills\b/g, "27 skills").replace(/\b28 skills\b/g, "27 skills"), /quoted skill count 27/],
      ["docs/VERIFICATION.md", (text: string) => text.replace("Le catalogue 0.4.0 contient 29 skills", "Le catalogue 0.4.0 contient 27 skills").replace("Le catalogue 0.3.0 contient 29 skills", "Le catalogue 0.3.0 contient 27 skills"), /quoted skill count 27/],
      ["plugins/cstack/.codex-plugin/plugin.json", (text: string) => text.replace('"version": "0.3.0"', '"version": "9.9.9"').replace('"version": "0.4.0"', '"version": "9.9.9"'), /missing changelog or evidence/],
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
    const extra = join(copy, "plugins/cstack/UNACCOUNTED.md");
    writeFileSync(extra, "orphan\n");
    expect(() => validate(copy)).toThrow(/unaccounted plugin file/);
    rmSync(extra);
    const executable = join(copy, "plugins/cstack/scripts/run-tool.sh");
    chmodSync(executable, 0o644);
    expect(() => validate(copy)).toThrow(/expected mode 0755/);
    chmodSync(executable, 0o755);
    const reference = "plugins/cstack/skills/cstack/references/principles/prove-it-works.md";
    rmSync(join(copy, reference));
    expect(() => validate(copy)).toThrow(/missing or escaping port target/);
    cpSync(join(root, reference), join(copy, reference));
    mkdirSync(join(copy, "plugins/cstack/skills/principle-prove-it-works"), { recursive: true });
    writeFileSync(join(copy, "plugins/cstack/skills/principle-prove-it-works/SKILL.md"), "---\nname: principle-prove-it-works\ndescription: stale\n---\n");
    const coveragePath = join(copy, "PORTING.json");
    const coverage = JSON.parse(readFileSync(coveragePath, "utf8"));
    coverage.original.push({ path: "plugins/cstack/skills/principle-prove-it-works/SKILL.md", reason: "stale fixture" });
    writeFileSync(coveragePath, JSON.stringify(coverage));
    expect(() => validate(copy)).toThrow(/principle skill entrypoints were moved to references/);
  } finally {
    rmSync(copy, { recursive: true, force: true });
  }
}, { timeout: 20000 });

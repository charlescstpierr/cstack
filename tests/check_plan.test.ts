import { expect, test } from "bun:test";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

const root = resolve(import.meta.dir, "..");
const checker = join(root, "plugins/cstack/skills/cstack/scripts/check-plan.mjs");

function example(): string {
  const playbook = readFileSync(join(root, "plugins/cstack/skills/cstack/playbooks/multi-phase-plan.md"), "utf8");
  const template = playbook.split("````markdown\n")[1]?.split("````")[0];
  if (!template) throw new Error("Missing bundled plan template");
  return template.replace(/<[^>]+>/g, "example")
    .replace(/^- \[ \] Lane (\d+)\..*$/gm, (_, number) => `- [ ] Lane ${number}. Run the scenario. Save \`evidence/lane-${number}.log\`. Pass when the observed result matches the contract.`);
}

test("the native plan checker accepts the bundled template and explicit unavailable lanes", () => {
  const dir = mkdtempSync(join(tmpdir(), "cstack-plan-"));
  try {
    const path = join(dir, "plan.md");
    writeFileSync(path, example().replace(/Lane 10\..*/, "Lane 10. n/a: no tenth distinct behavior applies."));
    const result = Bun.spawnSync(["bun", checker, path]);
    expect({ code: result.exitCode, errors: result.stderr.toString() }).toEqual({ code: 0, errors: "" });
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("the plan checker rejects missing verification and unreasoned skipped lanes", () => {
  const dir = mkdtempSync(join(tmpdir(), "cstack-plan-"));
  try {
    const path = join(dir, "plan.md");
    for (const invalid of [
      example().replace("**Verify, unit.**", "**Absent.**"),
      example().replace(/Lane 10\..*/, "Lane 10. n/a:"),
      example().replace("**Deliver.**", "**Absent.**"),
    ]) {
      writeFileSync(path, invalid);
      const result = Bun.spawnSync(["bun", checker, path]);
      expect(result.exitCode).toBe(1);
      expect(result.stderr.toString().length).toBeGreaterThan(0);
    }
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

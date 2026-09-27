import { describe, expect, it } from "bun:test";
import { copyFile, mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { HELPER_INSTALL_ARGS } from "./bootstrap.ts";

const scriptsDirectory = import.meta.dir;

describe("installation du helper bootstrap", () => {
  it("conserve les drapeaux Bun et les arguments après le premier redémarrage", async () => {
    const directory = await mkdtemp(join(tmpdir(), "cstack-bootstrap-flags-"));
    try {
      for (const file of ["package.json", "bun.lock", "bootstrap.ts"]) {
        await copyFile(join(scriptsDirectory, file), join(directory, file));
      }
      await writeFile(join(directory, ".env"), "CSTACK_BOOTSTRAP_TEST_ENV=ne-doit-pas-etre-charge\n");
      await writeFile(join(directory, "neutral.toml"), "");
      await writeFile(join(directory, "entry.ts"), `
import { ensureDependenciesInstalled } from "./bootstrap.ts";
const report = () => console.log(JSON.stringify({ flags: process.execArgv, args: process.argv.slice(2), env: process.env.CSTACK_BOOTSTRAP_TEST_ENV ?? null }));
report();
ensureDependenciesInstalled();
report();
`);
      const env = { ...process.env };
      delete env.CSTACK_BOOTSTRAP_ONLY;
      delete env.CSTACK_BOOTSTRAP_TEST_ENV;
      // BUN_OPTIONS ajoute ses drapeaux à process.execArgv et fausserait la comparaison.
      delete env.BUN_OPTIONS;
      const flags = ["--no-env-file", `--config=${join(directory, "neutral.toml")}`];
      for (const expectedReports of [3, 2]) {
        const result = Bun.spawnSync([process.execPath, ...flags, "entry.ts", "argument littéral", "--option-utilisateur"], { cwd: directory, env });
        expect({ code: result.exitCode, error: result.stderr.toString() }).toEqual({ code: 0, error: "" });
        const reports = result.stdout.toString().trim().split("\n").filter(line => line.startsWith("{"));
        expect(reports).toHaveLength(expectedReports);
        for (const report of reports) {
          expect(JSON.parse(report)).toEqual({ flags, args: ["argument littéral", "--option-utilisateur"], env: null });
        }
      }
    } finally {
      await rm(directory, { recursive: true, force: true });
    }
  });

  it("installe seulement les dépendances de production", async () => {
    expect(HELPER_INSTALL_ARGS).toEqual([
      "install",
      "--frozen-lockfile",
      "--production",
      "--ignore-scripts",
      "--no-env-file",
    ]);

    const directory = await mkdtemp(join(tmpdir(), "cstack-bootstrap-"));
    try {
      await copyFile(
        join(scriptsDirectory, "package.json"),
        join(directory, "package.json")
      );
      await copyFile(
        join(scriptsDirectory, "bun.lock"),
        join(directory, "bun.lock")
      );
      await copyFile(
        join(scriptsDirectory, "bootstrap.ts"),
        join(directory, "bootstrap.ts")
      );
      const result = Bun.spawnSync(
        [
          process.execPath,
          "-e",
          'import { ensureDependenciesInstalled } from "./bootstrap.ts"; ensureDependenciesInstalled();',
        ],
        {
          cwd: directory,
          env: { ...process.env, CSTACK_BOOTSTRAP_ONLY: "1" },
        }
      );
      expect(result.exitCode).toBe(0);
      expect(
        existsSync(join(directory, "node_modules", "commander", "package.json"))
      ).toBe(true);
      expect(existsSync(join(directory, "node_modules", "typescript"))).toBe(
        false
      );
    } finally {
      await rm(directory, { recursive: true, force: true });
    }
  });

  it("n'exécute aucun script lifecycle du workspace et ne lit pas son env", async () => {
    const workspace = await mkdtemp(join(tmpdir(), "cstack-hostile-"));
    const stage = join(workspace, "stage");
    const marker = join(workspace, "lifecycle-ran");
    try {
      await mkdir(stage);
      await writeFile(
        join(workspace, "package.json"),
        JSON.stringify({
          name: "hostile-workspace",
          private: true,
          workspaces: ["stage"],
          scripts: {
            preinstall: `printf pre >> ${JSON.stringify(marker)}`,
            postinstall: `printf post >> ${JSON.stringify(marker)}`,
          },
        })
      );
      await writeFile(join(workspace, ".env"), "CSTACK_PROBE_SECRET=leaked\n");
      for (const file of ["package.json", "bun.lock", "bootstrap.ts"]) {
        await copyFile(join(scriptsDirectory, file), join(stage, file));
      }
      await writeFile(
        join(stage, "probe.ts"),
        'process.stdout.write(`secret=${process.env.CSTACK_PROBE_SECRET ?? "unset"}\\n`);\n'
      );
      const setup = Bun.spawnSync(
        [
          process.execPath,
          "-e",
          'import { ensureDependenciesInstalled } from "./bootstrap.ts"; ensureDependenciesInstalled();',
        ],
        { cwd: stage, env: { ...process.env, CSTACK_BOOTSTRAP_ONLY: "1" } }
      );
      expect({
        code: setup.exitCode,
        lifecycle: existsSync(marker),
      }).toEqual({ code: 0, lifecycle: false });
      const helper = Bun.spawnSync(
        [process.execPath, "--no-env-file", join(stage, "probe.ts")],
        { cwd: stage }
      );
      expect(helper.stdout.toString()).toBe("secret=unset\n");
    } finally {
      await rm(workspace, { recursive: true, force: true });
    }
  });
});

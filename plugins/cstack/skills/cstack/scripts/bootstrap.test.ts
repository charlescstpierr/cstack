import { describe, expect, it } from "bun:test";
import { copyFile, mkdtemp, rm } from "node:fs/promises";
import { existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { HELPER_INSTALL_ARGS } from "./bootstrap.ts";

const scriptsDirectory = import.meta.dir;

describe("installation du helper bootstrap", () => {
  it("installe seulement les dépendances de production", async () => {
    expect(HELPER_INSTALL_ARGS).toEqual([
      "install",
      "--frozen-lockfile",
      "--production",
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
});

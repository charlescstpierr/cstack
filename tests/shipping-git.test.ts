import { test } from "bun:test";
import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import {
  mkdtempSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

function run(cwd: string, ...args: string[]): string {
  return execFileSync("git", args, {
    cwd,
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  }).trim();
}

function fixture(body: (root: string, commit: (file: string, content: string) => string) => void): void {
  const root = mkdtempSync(join(tmpdir(), "cstack-shipping-git-"));
  try {
    run(root, "init", "-b", "main");
    run(root, "config", "user.email", "fixture@example.invalid");
    run(root, "config", "user.name", "Fixture");
    const commit = (file: string, content: string): string => {
      writeFileSync(join(root, file), content);
      run(root, "add", file);
      run(root, "commit", "-m", `Update ${file}`);
      return run(root, "rev-parse", "HEAD");
    };
    commit("base.txt", "base\n");
    body(root, commit);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
}

test("après un squash parent, rejoue seulement les commits enfant", () =>
  fixture((root, commit) => {
    run(root, "checkout", "-b", "parent");
    commit("parent.txt", "first\n");
    const oldParent = commit("parent.txt", "parent final\n");
    run(root, "checkout", "-b", "child");
    commit("child.txt", "child only\n");
    run(root, "checkout", "main");
    run(root, "merge", "--squash", "parent");
    run(root, "commit", "-m", "Squash parent");
    const trunk = run(root, "rev-parse", "HEAD");

    run(root, "merge-base", "--is-ancestor", oldParent, "child");
    run(root, "rebase", "--onto", trunk, oldParent, "child");
    assert.equal(run(root, "rev-list", "--count", `${trunk}..child`), "1");
    assert.equal(run(root, "diff", "--name-only", `${trunk}..child`), "child.txt");
    assert.equal(readFileSync(join(root, "parent.txt"), "utf8"), "parent final\n");
    assert.equal(readFileSync(join(root, "child.txt"), "utf8"), "child only\n");
  })
);

test("un lease explicite refuse le travail concurrent après un fetch", () =>
  fixture((root, commit) => {
    const remote = join(root, "remote.git");
    run(root, "init", "--bare", remote);
    run(root, "remote", "add", "origin", remote);
    run(root, "checkout", "-b", "child");
    const captured = commit("child.txt", "original\n");
    run(root, "push", "origin", "child");
    const concurrent = commit("concurrent.txt", "someone else\n");
    run(root, "push", "origin", "child");
    run(root, "reset", "--hard", captured);
    commit("child.txt", "rewritten\n");
    run(root, "fetch", "origin");

    const push = spawnSync(
      "git",
      [
        "push",
        `--force-with-lease=refs/heads/child:${captured}`,
        "origin",
        "HEAD:refs/heads/child",
      ],
      { cwd: root, encoding: "utf8" }
    );
    assert.notEqual(push.status, 0);
    assert.match(push.stderr, /stale info|rejected/);
    assert.equal(
      run(root, "ls-remote", "origin", "refs/heads/child").split(/\s/)[0],
      concurrent
    );
  })
);

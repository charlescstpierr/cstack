import { describe, expect, it } from "bun:test";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { type CliRuntime, main, parseArgs } from "./cli.ts";
import { fakeReader, passingCheck } from "./fakes.test-helper.ts";
import {
  GhGitHubReader,
  WatcherQueryError,
  parseOpenPullRequests,
} from "./github.ts";
import { renderJson, renderPretty } from "./render.ts";
import type { GitHubReader, WatcherVerdict } from "./types.ts";
import { parsePrNumber } from "./types.ts";

const silentIo = { stdout: () => {}, stderr: () => {} };

function testRuntime(reader: GitHubReader): {
  readonly runtime: CliRuntime;
  readonly stdout: string[];
  readonly stderr: string[];
} {
  const stdout: string[] = [];
  const stderr: string[] = [];
  return {
    stdout,
    stderr,
    runtime: {
      reader,
      clock: {
        now: () => 0,
        observedAt: () => "2026-07-26T00:00:00.000Z",
        async sleep() {
          throw new Error("test unexpectedly slept");
        },
      },
      stdout: (value) => stdout.push(value),
      stderr: (value) => stderr.push(value),
    },
  };
}

describe("parseArgs", () => {
  it("utilise les défauts spécifiés", () => {
    expect(parseArgs([], silentIo)).toMatchObject({
      owner: null,
      repo: null,
      pr: null,
      mode: "single",
      stackPrs: [],
      statusOnly: false,
      pretty: false,
      polling: {
        interval: 60,
        sweepInterval: 300,
        timeout: 0,
        maxQueryErrors: 5,
        allowDraft: false,
      },
    });
  });

  it("analyse une pile en file gelée de bas en haut", () => {
    const parsed = parseArgs(
      [
        "--queued-stack",
        "--stack-prs",
        "#10, 11,#12",
        "--interval",
        "2.5",
        "--sweep-interval",
        "30",
        "--timeout",
        "0",
        "--max-query-errors",
        "3",
        "--allow-draft",
        "--pretty",
      ],
      silentIo
    );
    expect(parsed.mode).toBe("queued-stack");
    expect(parsed.stackPrs.map(Number)).toEqual([10, 11, 12]);
    expect(parsed.polling).toEqual({
      interval: 2.5,
      sweepInterval: 30,
      timeout: 0,
      maxQueryErrors: 3,
      allowDraft: true,
    });
    expect(parsed.pretty).toBe(true);
  });

  it("rejette chaque mode et forme numérique invalide comme usage", async () => {
    const invalid = [
      ["--unknown"],
      ["--interval", "0"],
      ["--sweep-interval", "-1"],
      ["--timeout", "-1"],
      ["--max-query-errors", "1.5"],
      ["--stack", "--queued-stack"],
      ["--stack-prs", "1,2"],
      ["--queued-stack", "--stack-prs", "1,1"],
    ];
    for (const argv of invalid) {
      const harness = testRuntime(fakeReader());
      expect(await main(argv, harness.runtime)).toBe(64);
      expect(harness.stdout).toEqual([]);
      expect(harness.stderr.join("")).toMatch(/(?:error|erreur):/);
    }
  });
});

describe("rendu", () => {
  const context = {
    owner: "owner",
    repo: "repo",
    number: parsePrNumber(1),
  };
  const status = {
    schemaVersion: 1,
    sequence: 1,
    observedAt: "2026-07-26T00:00:00.000Z",
    mode: "single",
    kind: "STATUS",
    terminal: true,
    exitCode: 0,
    reason: "status-only",
    rows: [
      {
        kind: "merged",
        context,
        facts: {
          context,
          mergeable: "MERGEABLE",
          mergeStateStatus: "CLEAN",
          reviewDecision: "APPROVED",
          headRefOid: "head",
          headRefName: "feature",
          baseRefName: "main",
          state: "MERGED",
          mergedAt: "now",
          isDraft: false,
        },
      },
    ],
  } satisfies WatcherVerdict;

  it("émet par défaut du JSON compact valide", () => {
    const rendered = renderJson(status);
    expect(rendered.endsWith("\n")).toBe(true);
    expect(JSON.parse(rendered)).toEqual(status);
  });

  it("rend le tableau Markdown seulement depuis le même verdict", () => {
    const rendered = renderPretty(status);
    expect(rendered).toContain("| PR | CI | Revue | Fusion |");
    expect(rendered).toContain(
      "| [#1](https://github.com/owner/repo/pull/1) | \u2014 | \u2014 | ✅ fusionnee |"
    );
  });
});

describe("main", () => {
  it("renvoie EX_USAGE 64 et écrit les erreurs d’usage seulement sur stderr", async () => {
    const harness = testRuntime(fakeReader());
    expect(await main(["--interval", "0"], harness.runtime)).toBe(64);
    expect(harness.stdout).toEqual([]);
    expect(harness.stderr.join("")).toContain(
      "option '--interval <seconds>' argument '0' is invalid"
    );
  });

  it("contourne la machine de file pour queued-stack status-only", async () => {
    const lecteur = fakeReader();
    const harness = testRuntime(lecteur);
    const code = await main(
      [
        "--owner",
        "owner",
        "--repo",
        "repo",
        "--queued-stack",
        "--stack-prs",
        "1",
        "--status-only",
      ],
      harness.runtime
    );
    expect(code).toBe(0);
    expect(harness.stdout).toHaveLength(1);
    const verdict: unknown = JSON.parse(harness.stdout[0]);
    expect(verdict).toMatchObject({
      kind: "STATUS",
      terminal: true,
      exitCode: 0,
      mode: "queued-stack",
    });
    expect(harness.stdout[0]).not.toContain('"kind":"QUEUE"');
  });

  it("renvoie la sortie 4 pour un refus CI caché côté GitHub", async () => {
    const lecteur = fakeReader({
      facts: { mergeStateStatus: "BLOCKED" },
      fastPath: { kind: "checks", checks: [passingCheck()] },
      commitRollups: [{ oid: "head", state: "FAILURE" }],
    });
    const harness = testRuntime(lecteur);
    const code = await main(
      ["--owner", "owner", "--repo", "repo", "--pr", "1"],
      harness.runtime
    );
    expect(code).toBe(4);
    expect(harness.stdout).toHaveLength(1);
    expect(JSON.parse(harness.stdout[0])).toMatchObject({
      kind: "BLOCKER",
      exitCode: 4,
      blocker: {
        kind: "failing-checks",
        ci: { kind: "ci-github-rejected" },
      },
    });
  });

  it("nomme l’absence de checks dans le tableau d’état et le verdict READY", async () => {
    const argv = [
      "--owner",
      "owner",
      "--repo",
      "repo",
      "--pr",
      "1",
      "--pretty",
    ];
    const noChecks = () =>
      testRuntime(
        fakeReader({
          facts: { reviewDecision: null },
          fastPath: { kind: "none-reported" },
          rollupPages: [{ kind: "no-rollup" }],
          commitRollups: [{ oid: "head", state: null }],
        })
      );
    const status = noChecks();
    expect(await main([...argv, "--status-only"], status.runtime)).toBe(0);
    expect(status.stdout.join("")).toContain(
      "| [#1](https://github.com/owner/repo/pull/1) | ➖ aucun check | ✅ | ✅ |"
    );
    const ready = noChecks();
    expect(await main(argv, ready.runtime)).toBe(0);
    expect(ready.stdout.join("")).toBe(
      "READY: aucun conflit de fusion, aucun fil de revue non résolu, aucun check en échec ou en attente\nmergeStateStatus=CLEAN\nreviewDecision=null\nisDraft=false\nchecks=aucun signalé sur le commit head\n"
    );
  });

  it("affiche l’aide sans toucher au lecteur", async () => {
    const lecteur = fakeReader();
    const harness = testRuntime(lecteur);
    expect(await main(["--help"], harness.runtime)).toBe(0);
    const help = harness.stdout.join("").replace(/\s+/g, " ");
    expect(help).toContain("JSON (NDJSON pendant le polling)");
    expect(help).toContain(
      "ancêtres et descendants ouverts de la PR sélectionnée"
    );
    expect(lecteur.calls).toEqual([]);
  });

  it("renvoie BLOCKER avec sortie 7 quand gh manque", async () => {
    const directory = await mkdtemp(join(tmpdir(), "watch-cli-missing-gh-"));
    const original = process.env.PATH;
    process.env.PATH = directory;
    try {
      const harness = testRuntime(new GhGitHubReader());
      const code = await main(
        ["--owner", "o", "--repo", "r", "--pr", "1", "--stack"],
        harness.runtime
      );
      expect(code).toBe(7);
      expect(JSON.parse(harness.stdout[0])).toMatchObject({
        kind: "BLOCKER",
        exitCode: 7,
        blocker: {
          kind: "status-query",
          failure: { kind: "missing-command", retryable: false },
        },
      });
    } finally {
      if (original === undefined) delete process.env.PATH;
      else process.env.PATH = original;
      await rm(directory, { recursive: true, force: true });
    }
  });

  it("renvoie immédiatement la sortie 7 pour un échec auth non réessayable", async () => {
    const lecteur = {
      ...fakeReader(),
      async pullRequest() {
        throw new WatcherQueryError({
          kind: "auth",
          retryable: false,
          code: 1,
          detail: "You are not logged into any GitHub hosts. Run gh auth login",
        });
      },
    };
    const harness = testRuntime(lecteur);
    expect(
      await main(
        ["--owner", "owner", "--repo", "repo", "--pr", "1"],
        harness.runtime
      )
    ).toBe(7);
    expect(JSON.parse(harness.stdout[0])).toMatchObject({
      kind: "BLOCKER",
      exitCode: 7,
      blocker: {
        kind: "status-query",
        failure: { kind: "auth", retryable: false },
      },
    });
  });

  it("ne déclare pas READY quand un fork homonyme masquerait le parent réel en conflit", async () => {
    const base = { owner: "owner", repo: "repo" };
    const raw = [
      {
        number: 1,
        headRefName: "root",
        headRepository: { nameWithOwner: "owner/repo" },
        headRepositoryOwner: { login: "owner" },
        baseRefName: "main",
      },
      {
        number: 2,
        headRefName: "child",
        headRepository: { nameWithOwner: "owner/repo" },
        headRepositoryOwner: { login: "owner" },
        baseRefName: "root",
      },
      {
        number: 4,
        headRefName: "root",
        headRepository: { nameWithOwner: "fork/repo" },
        headRepositoryOwner: { login: "fork" },
        baseRefName: "main",
      },
    ];
    const source = fakeReader({
      openPullRequests: parseOpenPullRequests(raw, base),
    });
    const requested: number[] = [];
    const reader: GitHubReader = {
      ...source,
      async pullRequest(request) {
        requested.push(request.number);
        const pr = raw.find((item) => item.number === request.number);
        expect(pr).toBeDefined();
        return {
          ...(await source.pullRequest(request)),
          headRefName: pr?.headRefName ?? "",
          baseRefName: pr?.baseRefName ?? "",
          mergeable: request.number === 1 ? "CONFLICTING" : "MERGEABLE",
        };
      },
    };
    const harness = testRuntime(reader);
    const code = await main(
      ["--owner", "owner", "--repo", "repo", "--pr", "2", "--stack"],
      harness.runtime
    );
    expect(requested).toEqual([1, 2]);
    expect(code).toBe(2);
    expect(
      JSON.parse(harness.stdout[harness.stdout.length - 1]!)
    ).toMatchObject({
      kind: "BLOCKER",
      blocker: {
        kind: "merge-conflicts",
        pr: { number: 1 },
      },
    });
  });
});

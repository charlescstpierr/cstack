import { describe, expect, it } from "bun:test";
import {
  ChecksUnavailable,
  GhGitHubReader,
  OPEN_PR_LIST_LIMIT,
  WatcherQueryError,
  mapRollupNode,
  orderStack,
  parseOpenPullRequests,
  parsePullRequest,
  parseReviewThreads,
  resolveChecks,
  resolveContext,
} from "./github.ts";
import { chmod, mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import {
  fakeReader,
  failedCheck,
  passingCheck,
  pendingCheck,
} from "./fakes.test-helper.ts";
import { parsePrNumber } from "./types.ts";

const context = {
  owner: "owner",
  repo: "repo",
  number: parsePrNumber(42),
};
const source = (owner: string, repo = "repo") => ({ owner, repo });
const openPr = (
  number: number,
  headRefName: string,
  baseRefName: string,
  headOwner = context.owner,
  headRepo = context.repo
) => ({
  number: parsePrNumber(number),
  headRepository: source(headOwner, headRepo),
  headRefName,
  baseRepository: source(context.owner, context.repo),
  baseRefName,
});

describe("chaîne de repli des vérifications", () => {
  it("utilise un résultat du chemin rapide non vide sans requête rollup", async () => {
    const reader = fakeReader({
      fastPath: { kind: "checks", checks: [passingCheck("fast")] },
    });
    const read = await resolveChecks(reader, context);
    expect(read.source).toBe("gh-pr-checks");
    expect(read.checks.map((check) => check.name)).toEqual(["fast"]);
    expect(reader.calls).toEqual(["checksFastPath"]);
  });

  it("pagine GraphQL quand le chemin rapide est inutilisable", async () => {
    const reader = fakeReader({
      fastPath: { kind: "unusable", exitCode: 8, stderr: "" },
      rollupPages: [
        { checks: [passingCheck("first")], endCursor: "next" },
        { checks: [failedCheck("second")], endCursor: null },
      ],
    });
    const read = await resolveChecks(reader, context);
    expect(read.source).toBe("graphql-rollup");
    expect(read.checks.map((check) => check.name)).toEqual(["first", "second"]);
    expect(reader.calls).toEqual([
      "checksFastPath",
      "checkRollupPage:null",
      "checkRollupPage:next",
    ]);
  });

  it("bascule en repli quand le JSON du chemin rapide valide représente une liste vide", async () => {
    const reader = fakeReader({
      fastPath: { kind: "checks", checks: [] },
      rollupPages: [{ checks: [pendingCheck("repli")], endCursor: null }],
    });
    expect((await resolveChecks(reader, context)).checks[0].name).toBe(
      "repli"
    );
    expect(reader.calls).toEqual(["checksFastPath", "checkRollupPage:null"]);
  });

  it("échoue ferme quand les deux chemins sont vides", async () => {
    const reader = fakeReader({
      fastPath: {
        kind: "unusable",
        exitCode: 8,
        stderr: "credential cannot read checks",
      },
    });
    await expect(resolveChecks(reader, context)).rejects.toBeInstanceOf(
      ChecksUnavailable
    );
    expect(reader.calls).toEqual(["checksFastPath", "checkRollupPage:null"]);
  });
});

describe("correspondance des nœuds rollup", () => {
  it("associe les états CheckRun terminaux et non terminaux en échec ferme", () => {
    const cases = [
      ["IN_PROGRESS", null, "pending", "PENDING"],
      ["COMPLETED", "SUCCESS", "passed", "SUCCESS"],
      ["COMPLETED", "NEUTRAL", "skipped", "NEUTRAL"],
      ["COMPLETED", "SKIPPED", "skipped", "SKIPPED"],
      ["COMPLETED", "ACTION_REQUIRED", "failed", "ACTION_REQUIRED"],
      ["COMPLETED", "TIMED_OUT", "failed", "FAILURE"],
      ["COMPLETED", "FUTURE_VALUE", "failed", "FAILURE"],
    ] as const;
    for (const [status, conclusion, kind, reportedState] of cases) {
      expect(
        mapRollupNode({
          __typename: "CheckRun",
          name: "ci",
          status,
          conclusion,
        })
      ).toMatchObject({ kind, reportedState });
    }
  });

  it("classe un Code Review Gate en cours depuis le rollup comme barrière", () => {
    expect(
      mapRollupNode({
        __typename: "CheckRun",
        name: "Code Review Gate",
        status: "IN_PROGRESS",
        conclusion: null,
      })
    ).toMatchObject({ kind: "code-review-gate" });
    expect(
      mapRollupNode({
        __typename: "StatusContext",
        context: "Code Review Gate",
        state: "PENDING",
      })
    ).toMatchObject({ kind: "code-review-gate" });
  });

  it("associe les états StatusContext et ignore les typenames inconnus", () => {
    expect(
      mapRollupNode({
        __typename: "StatusContext",
        context: "ci",
        state: "EXPECTED",
      })
    ).toMatchObject({ kind: "pending", reportedState: "PENDING" });
    expect(
      mapRollupNode({
        __typename: "StatusContext",
        context: "ci",
        state: "FUTURE_VALUE",
      })
    ).toMatchObject({ kind: "failed", reportedState: "FUTURE_VALUE" });
    expect(mapRollupNode({ __typename: "FutureNode" })).toBeNull();
  });
});

describe("analyse ferme des énumérations", () => {
  const rawPullRequest = {
    mergeable: "MERGEABLE",
    mergeStateStatus: "CLEAN",
    reviewDecision: "APPROVED",
    headRefOid: "head",
    headRefName: "feature",
    baseRefName: "main",
    state: "OPEN",
    mergedAt: null,
    isDraft: false,
  };

  it("accepte mergeStateStatus CONFLICTING", () => {
    expect(
      parsePullRequest(
        { ...rawPullRequest, mergeStateStatus: "CONFLICTING" },
        context
      ).mergeStateStatus
    ).toBe("CONFLICTING");
  });

  it("lit reviewDecision vide de gh comme absence de décision plutôt qu’échec d’analyse", () => {
    expect(
      parsePullRequest({ ...rawPullRequest, reviewDecision: "" }, context)
        .reviewDecision
    ).toBeNull();
  });

  it("rejette encore un reviewDecision inconnu", () => {
    expect(() =>
      parsePullRequest({ ...rawPullRequest, reviewDecision: "MAYBE" }, context)
    ).toThrow(WatcherQueryError);
  });

  it("rejette les valeurs enum inconnues comme erreurs réessayables portant la valeur brute", () => {
    try {
      parsePullRequest(
        { ...rawPullRequest, mergeStateStatus: "FUTURE_STATE" },
        context
      );
      throw new Error("parseur attendu en echec");
    } catch (error) {
      expect(error).toBeInstanceOf(WatcherQueryError);
      if (!(error instanceof WatcherQueryError)) throw error;
      expect(error.failure).toMatchObject({
        kind: "missing-key",
        retryable: true,
        rawValue: '"FUTURE_STATE"',
      });
    }
  });
});

it("annote les fils Bugbot avec des comptes distincts de passes de revue", () => {
  const response = {
    data: {
      repository: {
        pullRequest: {
          reviewThreads: {
            pageInfo: { hasNextPage: false },
            nodes: [
              {
                id: "one",
                isResolved: false,
                comments: {
                  nodes: [
                    {
                      body: "RUN_ID: run-1",
                      createdAt: "now",
                      path: "a.ts",
                      line: 1,
                      author: { login: "bugbot" },
                    },
                  ],
                },
              },
              {
                id: "two",
                isResolved: false,
                comments: {
                  nodes: [
                    {
                      body: "CURSOR_AUTOMATION_ID: run-2 severity high",
                      createdAt: "now",
                      path: null,
                      line: null,
                      author: { login: "cursor" },
                    },
                  ],
                },
              },
              {
                id: "resolved",
                isResolved: true,
                comments: {
                  nodes: [
                    {
                      body: "RUN_ID: run-3",
                      createdAt: "now",
                      path: null,
                      line: null,
                      author: { login: "bugbot" },
                    },
                  ],
                },
              },
            ],
          },
        },
      },
    },
  };
  const threads = parseReviewThreads(response);
  expect(threads).toHaveLength(2);
  expect(threads.map((thread) => thread.isBugbot)).toEqual([true, true]);
  expect(threads.map((thread) => thread.bugbotReviewPasses)).toEqual([3, 3]);
});

describe("découverte du contexte et de la pile", () => {
  it("renvoie un contexte entièrement explicite sans appel au lecteur", async () => {
    const reader = fakeReader();
    expect(
      await resolveContext({
        reader,
        owner: "explicit",
        repo: "repo",
        pr: context.number,
      })
    ).toEqual({ owner: "explicit", repo: "repo", number: context.number });
    expect(reader.calls).toEqual([]);
  });

  it("utilise l’origine locale avant currentPr pour un numéro explicite", async () => {
    const reader = fakeReader({ origin: { owner: "local", repo: "checkout" } });
    expect(
      await resolveContext({
        reader,
        owner: null,
        repo: null,
        pr: context.number,
      })
    ).toEqual({ owner: "local", repo: "checkout", number: context.number });
    expect(reader.calls).toEqual(["originRepo"]);
  });

  it("ordonne la pile connectée de bas en haut", () => {
    const ordered = orderStack(context, [
      openPr(41, "base-feature", "main"),
      openPr(Number(context.number), "feature", "base-feature"),
      openPr(43, "upstack", "feature"),
    ]);
    expect(ordered.map((item) => Number(item.number))).toEqual([41, 42, 43]);
  });

  it("conserve les descendants bifurqués de la PR sélectionnée", () => {
    const ordered = orderStack(context, [
      openPr(Number(context.number), "root", "main"),
      openPr(43, "child-a", "root"),
      openPr(44, "child-b", "root"),
      openPr(45, "grandchild", "child-a"),
    ]);
    expect(ordered.map((item) => Number(item.number))).toEqual([
      42, 43, 45, 44,
    ]);
  });

  it("n’inclut pas les frères quand la PR sélectionnée est un enfant", () => {
    const ordered = orderStack(context, [
      openPr(41, "root", "main"),
      openPr(Number(context.number), "child-a", "root"),
      openPr(43, "child-b", "root"),
      openPr(44, "grandchild", "child-a"),
    ]);
    expect(ordered.map((item) => Number(item.number))).toEqual([41, 42, 44]);
  });

  it("ne confond pas un fork homonyme avec le parent réel", () => {
    const ordered = orderStack(context, [
      openPr(41, "base-feature", "main"),
      openPr(Number(context.number), "feature", "base-feature"),
      openPr(43, "upstack", "feature"),
      openPr(44, "base-feature", "main", "fork"),
    ]);
    expect(ordered.map((item) => Number(item.number))).toEqual([41, 42, 43]);
  });

  it("ne dépend pas de l’ordre d’une PR de fork homonyme", () => {
    const ordered = orderStack(context, [
      openPr(44, "base-feature", "main", "fork"),
      openPr(43, "upstack", "feature"),
      openPr(Number(context.number), "feature", "base-feature"),
      openPr(41, "base-feature", "main"),
    ]);
    expect(ordered.map((item) => Number(item.number))).toEqual([41, 42, 43]);
  });

  it("ne crée ni cycle ni enfants entre fork main et dépôt cible main", () => {
    const ordered = orderStack(
      { owner: context.owner, repo: context.repo, number: parsePrNumber(44) },
      [
        openPr(41, "feature", "main"),
        openPr(44, "main", "main", "fork"),
      ]
    );
    expect(ordered.map((item) => Number(item.number))).toEqual([44]);
  });

  it("accepte une PR sélectionnée depuis un fork", () => {
    const ordered = orderStack(
      { owner: context.owner, repo: context.repo, number: parsePrNumber(44) },
      [
        openPr(41, "base-feature", "main"),
        openPr(44, "fork-feature", "base-feature", "fork"),
      ]
    );
    expect(ordered.map((item) => Number(item.number))).toEqual([41, 44]);
  });

  it("compare owner/repo sans casse mais garde la casse des branches", () => {
    const ordered = orderStack(context, [
      {
        ...openPr(41, "Base", "main", "OWNER", "REPO"),
        baseRepository: source("OWNER", "REPO"),
      },
      openPr(Number(context.number), "feature", "Base"),
      openPr(43, "case-mismatch", "base"),
    ]);
    expect(ordered.map((item) => Number(item.number))).toEqual([41, 42]);
  });

  it("échoue ferme sur un cycle de base-ref", () => {
    const cyclic = [
      openPr(Number(context.number), "feature", "base-feature"),
      openPr(41, "base-feature", "feature"),
    ];
    expect(() => orderStack(context, cyclic)).toThrow(WatcherQueryError);
    try {
      orderStack(context, cyclic);
      throw new Error("cycle attendu en echec");
    } catch (error) {
      expect(error).toBeInstanceOf(WatcherQueryError);
      if (!(error instanceof WatcherQueryError)) throw error;
      expect(error.failure).toMatchObject({
        kind: "stack-cycle",
        retryable: false,
      });
    }
  });

  it("échoue ferme quand deux parents ont la même identité source", () => {
    const ambiguous = [
      openPr(Number(context.number), "feature", "base-feature"),
      openPr(41, "base-feature", "main"),
      openPr(40, "base-feature", "release"),
    ];
    expect(() => orderStack(context, ambiguous)).toThrow(WatcherQueryError);
    try {
      orderStack(context, ambiguous);
      throw new Error("parent ambigu attendu en echec");
    } catch (error) {
      expect(error).toBeInstanceOf(WatcherQueryError);
      if (!(error instanceof WatcherQueryError)) throw error;
      expect(error.failure).toMatchObject({
        kind: "stack-ambiguous",
        retryable: false,
      });
    }
  });
});


function threadResponse(hasNextPage: boolean, nodeCount = 1) {
  return {
    data: {
      repository: {
        pullRequest: {
          reviewThreads: {
            pageInfo: { hasNextPage },
            nodes: Array.from({ length: nodeCount }, (_, index) => ({
              id: `thread-${index}`,
              isResolved: false,
              comments: {
                nodes: [
                  {
                    body: "note",
                    createdAt: "now",
                    path: "a.ts",
                    line: 1,
                    author: { login: "reviewer" },
                  },
                ],
              },
            })),
          },
        },
      },
    },
  };
}

describe("pagination des fils de revue", () => {
  it("échoue ferme quand la page reviewThreads a plus de résultats", () => {
    expect(() => parseReviewThreads(threadResponse(true, 100))).toThrow(
      WatcherQueryError
    );
    try {
      parseReviewThreads(threadResponse(true, 100));
      throw new Error("fils tronques attendus en echec");
    } catch (error) {
      expect(error).toBeInstanceOf(WatcherQueryError);
      if (!(error instanceof WatcherQueryError)) throw error;
      expect(error.failure).toMatchObject({
        kind: "truncated",
        retryable: false,
      });
    }
  });

  it("accepte une page pleine quand GraphQL signale aucune page suivante", () => {
    expect(parseReviewThreads(threadResponse(false, 100))).toHaveLength(100);
  });
});

describe("troncature de la liste des PR ouvertes", () => {
  it("échoue ferme quand gh pr list atteint la limite de découverte", () => {
    const rows = Array.from({ length: OPEN_PR_LIST_LIMIT }, (_, index) => ({
      number: index + 1,
      headRefName: `branch-${index}`,
      headRepository: { nameWithOwner: "owner/repo" },
      headRepositoryOwner: { login: "owner" },
      baseRefName: "main",
    }));
    expect(() => parseOpenPullRequests(rows, context)).toThrow(
      WatcherQueryError
    );
    try {
      parseOpenPullRequests(rows, context);
      throw new Error("decouverte de pile tronquee attendue en echec");
    } catch (error) {
      expect(error).toBeInstanceOf(WatcherQueryError);
      if (!(error instanceof WatcherQueryError)) throw error;
      expect(error.failure).toMatchObject({
        kind: "truncated",
        retryable: false,
        detail: `gh pr list a renvoyé ${OPEN_PR_LIST_LIMIT} PR; la découverte de pile peut être incomplète`,
      });
    }
  });

  it("analyse une liste juste sous la limite de découverte", () => {
    const rows = Array.from(
      { length: OPEN_PR_LIST_LIMIT - 1 },
      (_, index) => ({
        number: index + 1,
        headRefName: `branch-${index}`,
        headRepository: { nameWithOwner: "owner/repo" },
        headRepositoryOwner: { login: "owner" },
        baseRefName: "main",
      })
    );
    expect(parseOpenPullRequests(rows, context)).toHaveLength(
      OPEN_PR_LIST_LIMIT - 1
    );
  });

  it("analyse strictement l’identité source des PR ouvertes", () => {
    expect(
      parseOpenPullRequests(
        [
          {
            number: 41,
            headRefName: "feature",
            headRepository: { nameWithOwner: "Fork/Repo" },
            headRepositoryOwner: { login: "fork" },
            baseRefName: "main",
          },
        ],
        context
      )
    ).toEqual([
      {
        number: parsePrNumber(41),
        headRefName: "feature",
        headRepository: { owner: "Fork", repo: "Repo" },
        baseRefName: "main",
        baseRepository: { owner: context.owner, repo: context.repo },
      },
    ]);
  });

  it("échoue ferme quand l’identité source d’une PR ouverte manque", () => {
    expect(() =>
      parseOpenPullRequests(
        [{ number: 41, headRefName: "feature", baseRefName: "main" }],
        context
      )
    ).toThrow(WatcherQueryError);
  });
});

describe("échecs de lancement de gh", () => {
  async function withPath(
    directory: string,
    operation: () => Promise<void>,
    prepend = false
  ): Promise<void> {
    const original = process.env.PATH;
    process.env.PATH = prepend && original
      ? `${directory}:${original}`
      : directory;
    try {
      await operation();
    } finally {
      if (original === undefined) delete process.env.PATH;
      else process.env.PATH = original;
    }
  }

  it("enveloppe un binaire gh manquant comme erreur de requête non réessayable", async () => {
    const directory = await mkdtemp(join(tmpdir(), "watch-missing-gh-"));
    try {
      await withPath(directory, async () => {
        try {
          await new GhGitHubReader().currentPr(null);
          throw new Error("gh manquant attendu en echec");
        } catch (error) {
          expect(error).toBeInstanceOf(WatcherQueryError);
          if (!(error instanceof WatcherQueryError)) throw error;
          expect(error.failure).toMatchObject({
            kind: "missing-command",
            retryable: false,
          });
          expect(error.failure.detail).toContain("gh");
        }
      });
    } finally {
      await rm(directory, { recursive: true, force: true });
    }
  });

  it("classe les échecs d’authentification gh comme non réessayables", async () => {
    const directory = await mkdtemp(join(tmpdir(), "watch-auth-gh-"));
    const gh = join(directory, "gh");
    await writeFile(
      gh,
      `#!/bin/bash
echo "You are not logged into any GitHub hosts. Run gh auth login" >&2
exit 1
`
    );
    await chmod(gh, 0o755);
    try {
      await withPath(
        directory,
        async () => {
        try {
          await new GhGitHubReader().currentPr(null);
          throw new Error("echec auth attendu");
        } catch (error) {
          expect(error).toBeInstanceOf(WatcherQueryError);
          if (!(error instanceof WatcherQueryError)) throw error;
          expect(error.failure).toMatchObject({
            kind: "auth",
            retryable: false,
          });
        }
      },
        true
      );
    } finally {
      await rm(directory, { recursive: true, force: true });
    }
  });
});

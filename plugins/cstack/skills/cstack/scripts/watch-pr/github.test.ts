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
import type { CheckRead, ReportedChecks } from "./types.ts";
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

function reported(read: CheckRead): ReportedChecks {
  if (read.kind !== "reported")
    throw new Error(`checks attendus : ${read.kind}`);
  return read;
}

describe("lecture des vérifications du commit immuable", () => {
  it("lit le rollup du SHA demandé sans utiliser les checks du head mutable", async () => {
    const reader = fakeReader({
      fastPath: { kind: "checks", checks: [passingCheck("fast")] },
    });
    const read = reported(await resolveChecks(reader, context, "head"));
    expect(read.source).toBe("graphql-rollup");
    expect(read.checks.map((check) => check.name)).toEqual(["fast"]);
    expect(reader.calls).toEqual(["checkRollupPage:null"]);
  });

  it("pagine GraphQL en conservant le même SHA", async () => {
    const reader = fakeReader({
      fastPath: { kind: "unusable", exitCode: 8, stderr: "" },
      rollupPages: [
        {
          kind: "contexts",
          checks: [passingCheck("first")],
          endCursor: "next",
        },
        { kind: "contexts", checks: [failedCheck("second")], endCursor: null },
      ],
    });
    const readPage = reader.checkRollupPage;
    reader.checkRollupPage = async (request, after, headRefOid) => {
      expect(headRefOid).toBe("head");
      return readPage(request, after, headRefOid);
    };
    const read = reported(await resolveChecks(reader, context, "head"));
    expect(read.source).toBe("graphql-rollup");
    expect(read.checks.map((check) => check.name)).toEqual(["first", "second"]);
    expect(reader.calls).toEqual([
      "checkRollupPage:null",
      "checkRollupPage:next",
    ]);
  });

  it("lit les checks GraphQL même si le chemin gh pr checks est vide", async () => {
    const reader = fakeReader({
      fastPath: { kind: "checks", checks: [] },
      rollupPages: [
        {
          kind: "contexts",
          checks: [pendingCheck("repli")],
          endCursor: null,
        },
      ],
    });
    expect(reported(await resolveChecks(reader, context, "head")).checks[0].name).toBe(
      "repli"
    );
    expect(reader.calls).toEqual(["checkRollupPage:null"]);
  });

  it("échoue ferme quand le rollup n’a aucun contexte lisible", async () => {
    const reader = fakeReader({
      fastPath: {
        kind: "unusable",
        exitCode: 8,
        stderr: "credential cannot read checks",
      },
    });
    await expect(resolveChecks(reader, context, "head")).rejects.toBeInstanceOf(
      ChecksUnavailable
    );
    expect(reader.calls).toEqual(["checkRollupPage:null"]);
  });

  it("lit l’absence de checks quand gh n’en signale aucun et que le commit head n’a pas de rollup", async () => {
    const reader = fakeReader({
      fastPath: { kind: "none-reported" },
      rollupPages: [{ kind: "no-rollup" }],
    });
    expect(await resolveChecks(reader, context, "head")).toEqual({ kind: "no-checks" });
    expect(reader.calls).toEqual(["checkRollupPage:null", "checksFastPath"]);
  });

  it("échoue ferme quand une seule lecture dit qu’il n’y a pas de checks", async () => {
    const oneSided = [
      {
        fastPath: { kind: "unusable", exitCode: 1, stderr: "HTTP 401" },
        rollupPages: [{ kind: "no-rollup" }],
      },
      {
        fastPath: { kind: "checks", checks: [] },
        rollupPages: [{ kind: "no-rollup" }],
      },
      {
        fastPath: { kind: "none-reported" },
        rollupPages: [{ kind: "contexts", checks: [], endCursor: null }],
      },
    ] as const;
    for (const options of oneSided)
      await expect(
        resolveChecks(fakeReader(options), context, "head")
      ).rejects.toBeInstanceOf(ChecksUnavailable);
  });

  it("propage une requête rollup en échec au lieu de la lire comme une absence de checks", async () => {
    const reader = fakeReader({ fastPath: { kind: "none-reported" } });
    const failure = new WatcherQueryError({
      kind: "command-exit",
      retryable: true,
      code: 1,
      detail: "HTTP 502",
    });
    reader.checkRollupPage = async () => {
      throw failure;
    };
    await expect(resolveChecks(reader, context, "head")).rejects.toBe(failure);
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
    createdAt: "2026-10-07T15:00:00Z",
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

describe("lecture gh d’une PR sans checks configurés", () => {
  // Rejoue ce que gh renvoie pour une PR d’un dépôt sans CI : `gh pr checks`
  // sort en 1 avec « no checks reported » et le rollup du commit head est nul.
  async function withFakeGh(
    checksStderr: string,
    operation: (reader: GhGitHubReader) => Promise<void>,
    responseOid = "head"
  ): Promise<void> {
    const directory = await mkdtemp(join(tmpdir(), "watch-no-ci-gh-"));
    const gh = join(directory, "gh");
    await writeFile(
      gh,
      `#!/bin/bash
if [ "$1" = "pr" ] && [ "$2" = "checks" ]; then
  echo ${JSON.stringify(checksStderr)} >&2
  exit 1
fi
case "$*" in
  *"query PrCheckRollup"*)
    case "$*" in *"head=head"*) ;; *) exit 2;; esac
    case "$*" in *'object(expression: $head)'*) ;; *) exit 2;; esac
    echo '${JSON.stringify({ data: { repository: { object: { oid: responseOid, statusCheckRollup: null } } } })}'
    exit 0;;
esac
echo "appel gh inattendu: $*" >&2
exit 2
`
    );
    await chmod(gh, 0o755);
    const original = process.env.PATH;
    process.env.PATH = original ? `${directory}:${original}` : directory;
    try {
      await operation(new GhGitHubReader());
    } finally {
      if (original === undefined) delete process.env.PATH;
      else process.env.PATH = original;
      await rm(directory, { recursive: true, force: true });
    }
  }

  it("lit « no checks reported » et un rollup nul comme une absence de checks", async () => {
    await withFakeGh("no checks reported on the 'feature' branch", async (reader) => {
      expect(await reader.checksFastPath(context)).toEqual({
        kind: "none-reported",
      });
      expect(await reader.checkRollupPage(context, null, "head")).toEqual({
        kind: "no-rollup",
      });
      expect(await resolveChecks(reader, context, "head")).toEqual({
        kind: "no-checks",
      });
    });
  });

  it("échoue ferme quand gh pr checks sort en 1 pour une autre raison", async () => {
    await withFakeGh(
      "HTTP 401: Bad credentials (https://api.github.com/graphql)",
      async (reader) => {
        expect(await reader.checksFastPath(context)).toMatchObject({
          kind: "unusable",
          exitCode: 1,
        });
        await expect(resolveChecks(reader, context, "head")).rejects.toBeInstanceOf(
          ChecksUnavailable
        );
      }
    );
  });

  it("rejette un rollup portant un SHA différent de celui demandé", async () => {
    await withFakeGh("no checks reported on the 'feature' branch", async (reader) => {
      await expect(reader.checkRollupPage(context, null, "head")).rejects.toBeInstanceOf(ChecksUnavailable);
    }, "other-head");
  });
});

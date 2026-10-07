import { describe, expect, it } from "bun:test";
import { WatcherQueryError } from "./github.ts";
import {
  applyQueueSnapshot,
  assessGitHubMerge,
  classifyPr,
  createQueueState,
  evaluateQueue,
  planQueue,
  queryBackoffSeconds,
  readSnapshot,
  runQueued,
  selectTierMajorStackDecision,
} from "./policy.ts";
import {
  fakeReader,
  failedCheck,
  passingCheck,
  pendingCheck,
} from "./fakes.test-helper.ts";
import type {
  GitHubReader,
  NonEmpty,
  PollingOptions,
  PrContext,
  ProgressVerdict,
  PullRequestFacts,
  RollupState,
} from "./types.ts";
import { parsePrNumber } from "./types.ts";

const context = (number: number): PrContext => ({
  owner: "owner",
  repo: "repo",
  number: parsePrNumber(number),
});
const options = {
  interval: 10,
  sweepInterval: 300,
  timeout: 0,
  maxQueryErrors: 5,
  allowDraft: false,
} satisfies PollingOptions;

describe("table de vérité de l’état prêt", () => {
  it("couvre chaque ligne spécifiée et chaque valeur rollup UNKNOWN", () => {
    const cases: readonly [
      PullRequestFacts["mergeStateStatus"],
      RollupState,
      "allowed" | "refused",
    ][] = [
      ["BLOCKED", "FAILURE", "refused"],
      ["BLOCKED", "ERROR", "refused"],
      ["BLOCKED", "PENDING", "allowed"],
      ["UNSTABLE", "FAILURE", "allowed"],
      ["UNKNOWN", "ERROR", "allowed"],
      ["UNKNOWN", "EXPECTED", "allowed"],
      ["UNKNOWN", "FAILURE", "allowed"],
      ["UNKNOWN", "PENDING", "allowed"],
      ["UNKNOWN", "SUCCESS", "allowed"],
      ["UNKNOWN", null, "allowed"],
      ["CLEAN", "SUCCESS", "allowed"],
    ];
    for (const [mergeStateStatus, headRollupState, expected] of cases) {
      expect(
        assessGitHubMerge({ mergeStateStatus, headRollupState }).kind
      ).toBe(expected);
    }
  });

  it("transforme une liste visible propre plus un refus GitHub en bloqueur CI explicite", async () => {
    const reader = fakeReader({
      facts: { mergeStateStatus: "BLOCKED" },
      fastPath: { kind: "checks", checks: [passingCheck()] },
      commitRollups: [{ oid: "head", state: "FAILURE" }],
    });
    const snapshot = await readSnapshot({
      reader,
      context: context(1),
      pendingHistory: "include",
      allowDraft: false,
    });
    expect(snapshot.kind).toBe("open");
    if (snapshot.kind !== "open") throw new Error("snapshot open attendu");
    expect(snapshot.ci.kind).toBe("ci-github-rejected");
    expect(classifyPr(snapshot)).toMatchObject({
      kind: "blocker",
      blocker: { kind: "failing-checks" },
    });
  });
});

describe("planification des requêtes de snapshot", () => {
  it("refuse un head remplacé après les checks verts de l’ancien commit", async () => {
    const base = fakeReader();
    let pushed = false;
    const reader: GitHubReader = {
      ...base,
      async pullRequest(request) {
        const facts = await base.pullRequest(request);
        return pushed
          ? { ...facts, headRefOid: "new-head", mergeStateStatus: "UNSTABLE" }
          : facts;
      },
      async checkRollupPage(request, after, headRefOid) {
        expect(headRefOid).toBe(pushed ? "new-head" : "head");
        return pushed
          ? { kind: "contexts", checks: [failedCheck("new-ci")], endCursor: null }
          : base.checkRollupPage(request, after, headRefOid);
      },
      async commitRollups() {
        pushed = true;
        return [
          { oid: "head", state: "SUCCESS" },
          { oid: "new-head", state: "FAILURE" },
        ];
      },
    };
    await expect(readSnapshot({
      reader, context: context(1), pendingHistory: "include", allowDraft: false,
    })).rejects.toBeInstanceOf(WatcherQueryError);
    const current = await readSnapshot({
      reader, context: context(1), pendingHistory: "include", allowDraft: false,
    });
    expect(classifyPr(current)).toMatchObject({
      kind: "blocker", blocker: { kind: "failing-checks" },
    });
  });

  it("inclut le SHA observé dans la preuve READY", async () => {
    const snapshot = await readSnapshot({
      reader: fakeReader(), context: context(1), pendingHistory: "include", allowDraft: false,
    });
    expect(classifyPr(snapshot)).toMatchObject({
      kind: "ready", pr: { headRefOid: "head" },
    });
  });

  it("refuse un snapshot ouvert dont le SHA est absent", async () => {
    const reader = fakeReader({ facts: { headRefOid: null } });
    await expect(readSnapshot({
      reader, context: context(1), pendingHistory: "include", allowDraft: false,
    })).rejects.toBeInstanceOf(WatcherQueryError);
    expect(reader.calls).toEqual(["pullRequest"]);
  });

  it("ne demande pas les rollups de commit pendant que les vérifications en file sont pending", async () => {
    const reader = fakeReader({
      fastPath: { kind: "checks", checks: [pendingCheck()] },
    });
    const snapshot = await readSnapshot({
      reader,
      context: context(2),
      pendingHistory: "omit",
      allowDraft: false,
    });
    expect(snapshot.kind).toBe("open");
    if (snapshot.kind !== "open") throw new Error("snapshot open attendu");
    expect(snapshot.ci.kind).toBe("ci-pending");
    expect(reader.calls).toEqual([
      "pullRequest",
      "reviewThreads",
      "checkRollupPage:null",
      "pullRequest",
    ]);
  });

  it("demande les rollups pour les listes réglées et échouées", async () => {
    const settled = fakeReader();
    await readSnapshot({
      reader: settled,
      context: context(3),
      pendingHistory: "omit",
      allowDraft: false,
    });
    expect(settled.calls).toContain("commitRollups");

    const failed = fakeReader({
      fastPath: { kind: "checks", checks: [failedCheck()] },
    });
    await readSnapshot({
      reader: failed,
      context: context(4),
      pendingHistory: "omit",
      allowDraft: false,
    });
    expect(failed.calls).toContain("commitRollups");
  });

  it("court-circuite les lignes fusionnées avant fils et vérifications", async () => {
    const reader = fakeReader({
      facts: { state: "MERGED", mergedAt: "2026-07-26T00:00:00Z" },
    });
    expect(
      (
        await readSnapshot({
          reader,
          context: context(5),
          pendingHistory: "include",
          allowDraft: false,
        })
      ).kind
    ).toBe("merged");
    expect(reader.calls).toEqual(["pullRequest"]);
  });
});

it("scanne les piles par tier-major afin qu’un conflit upstack prime sur la CI de frontière", async () => {
  const frontier = await readSnapshot({
    reader: fakeReader({
      fastPath: { kind: "checks", checks: [failedCheck()] },
      commitRollups: [{ oid: "head", state: "FAILURE" }],
    }),
    context: context(10),
    pendingHistory: "omit",
    allowDraft: false,
  });
  const upstack = await readSnapshot({
    reader: fakeReader({ facts: { mergeable: "CONFLICTING" } }),
    context: context(11),
    pendingHistory: "omit",
    allowDraft: false,
  });
  const decision = selectTierMajorStackDecision([frontier, upstack]);
  expect(decision).toMatchObject({
    kind: "blocker",
    blocker: { kind: "merge-conflicts", pr: { number: 11 } },
  });
});

it("attribue une attente de pile à la PR dont les vérifications sont pending, pas au bas", async () => {
  const readyBottom = await readSnapshot({
    reader: fakeReader(),
    context: context(20),
    pendingHistory: "omit",
    allowDraft: false,
  });
  const pendingUpstack = await readSnapshot({
    reader: fakeReader({
      fastPath: { kind: "checks", checks: [pendingCheck("upstack-build")] },
    }),
    context: context(21),
    pendingHistory: "omit",
    allowDraft: false,
  });
  const decision = selectTierMajorStackDecision([readyBottom, pendingUpstack]);
  expect(decision).toMatchObject({
    kind: "waiting",
    frontier: { number: 21 },
    pending: [{ name: "upstack-build" }],
  });
});

it("attend sur un brouillon pendant que les vérifications sont pending, puis rapporte la barrière de brouillon", async () => {
  const pending = await readSnapshot({
    reader: fakeReader({
      facts: { isDraft: true },
      fastPath: { kind: "checks", checks: [pendingCheck()] },
    }),
    context: context(12),
    pendingHistory: "omit",
    allowDraft: false,
  });
  expect(classifyPr(pending).kind).toBe("waiting");

  const settled = await readSnapshot({
    reader: fakeReader({ facts: { isDraft: true } }),
    context: context(12),
    pendingHistory: "omit",
    allowDraft: false,
  });
  expect(classifyPr(settled)).toMatchObject({
    kind: "blocker",
    blocker: { kind: "merge-gate", reason: "draft-pr" },
  });
});

describe("cadence queued-stack", () => {
  async function openSnapshot(pr: PrContext) {
    return readSnapshot({
      reader: fakeReader(),
      context: pr,
      pendingHistory: "omit",
      allowDraft: false,
    });
  }

  it("retire une tête de sweep seulement après le succès de son snapshot", async () => {
    const queue = [
      context(20),
      context(21),
      context(22),
    ] satisfies NonEmpty<PrContext>;
    let state = createQueueState(queue, 0);
    const first = await openSnapshot(queue[0]);
    state = applyQueueSnapshot(state, first, 0, options).state;
    expect(state.work).toMatchObject({
      kind: "whole-stack-sweep",
      remaining: [{ number: 21 }, { number: 22 }],
    });
    const second = await openSnapshot(queue[1]);
    state = applyQueueSnapshot(state, second, 60, options).state;
    expect(state.work).toMatchObject({
      kind: "whole-stack-sweep",
      remaining: [{ number: 22 }],
    });
  });

  it("reprend le sweep à la PR dont la lecture a échoué", async () => {
    const middle = context(21);
    const base = fakeReader();
    let failNext = true;
    const timeline: string[] = [];
    const reader = {
      ...base,
      async pullRequest(pr: PrContext) {
        if (pr.number === middle.number && failNext) {
          failNext = false;
          timeline.push(`fail:${pr.number}`);
          throw new WatcherQueryError({
            kind: "command-exit",
            retryable: true,
            detail: "limite de debit",
            code: 1,
          });
        }
        timeline.push(`read:${pr.number}`);
        return base.pullRequest(pr);
      },
    } satisfies GitHubReader;
    let now = 0;
    let sleeps = 0;
    const running = runQueued({
      dependencies: {
        reader,
        clock: {
          now: () => now,
          observedAt: () => "2026-07-26T00:00:00.000Z",
          async sleep(seconds) {
            timeline.push("sleep");
            now += seconds;
            sleeps += 1;
            if (sleeps === 2) throw new Error("arret apres preuve de reprise");
          },
        },
        emit(verdict) {
          timeline.push(`emit:${verdict.kind}`);
        },
      },
      contexts: [context(20), middle, context(22)],
      options,
    });
    await expect(running).rejects.toThrow("arret apres preuve de reprise");
    expect(timeline).toEqual([
      "emit:QUEUE",
      "read:20",
      "read:20",
      "fail:21",
      "emit:RETRY",
      "sleep",
      "read:21",
      "read:21",
      "read:22",
      "read:22",
      "emit:STATUS",
      "emit:WAITING",
      "sleep",
    ]);
  });

  it("émet un sweep terminé seulement après son dernier snapshot réussi", async () => {
    const queue = [context(30), context(31)] satisfies NonEmpty<PrContext>;
    let state = createQueueState(queue, 0);
    const first = applyQueueSnapshot(
      state,
      await openSnapshot(queue[0]),
      0,
      options
    );
    expect(first.completedSweepRows).toBeNull();
    state = first.state;
    const second = applyQueueSnapshot(
      state,
      await openSnapshot(queue[1]),
      5,
      options
    );
    expect(
      second.completedSweepRows?.map((row) => Number(row.context.number))
    ).toEqual([30, 31]);
    expect(second.state.nextSweepAt).toBe(305);
  });

  it("ADVANCE continue directement vers la nouvelle frontière sans sleep", async () => {
    const one = context(40);
    const two = context(41);
    const base = fakeReader();
    const reads = new Map<number, number>();
    const timeline: string[] = [];
    const reader = {
      ...base,
      async pullRequest(pr: PrContext) {
        timeline.push(`read:${pr.number}`);
        const facts = await base.pullRequest(pr);
        const count = (reads.get(pr.number) ?? 0) + 1;
        reads.set(pr.number, count);
        return pr.number === one.number && count > 2
          ? {
              ...facts,
              state: "MERGED" as const,
              mergedAt: "2026-07-26T00:00:00Z",
            }
          : facts;
      },
    } satisfies GitHubReader;
    let now = 0;
    let sleeps = 0;
    const emitted: ProgressVerdict[] = [];
    const running = runQueued({
      dependencies: {
        reader,
        clock: {
          now: () => now,
          observedAt: () => "2026-07-26T00:00:00.000Z",
          async sleep(seconds) {
            timeline.push("sleep");
            now += seconds;
            sleeps += 1;
            if (sleeps === 2) throw new Error("arret apres preuve ADVANCE");
          },
        },
        emit(verdict) {
          emitted.push(verdict);
          timeline.push(`emit:${verdict.kind}`);
        },
      },
      contexts: [one, two],
      options,
    });
    await expect(running).rejects.toThrow("arret apres preuve ADVANCE");
    expect(emitted.some((event) => event.kind === "ADVANCE")).toBe(true);
    const firstSleep = timeline.indexOf("sleep");
    expect(timeline.slice(firstSleep, firstSleep + 6)).toEqual([
      "sleep",
      "read:40",
      "emit:ADVANCE",
      "read:41",
      "read:41",
      "emit:WAITING",
    ]);
  });

  it("dédoublonne les attentes identiques et planifie le prochain sweep suivant", async () => {
    const queue = [context(50)] satisfies NonEmpty<PrContext>;
    let state = createQueueState(queue, 0);
    state = applyQueueSnapshot(
      state,
      await openSnapshot(queue[0]),
      0,
      options
    ).state;
    const first = evaluateQueue(state, 0, options);
    expect(first.kind).toBe("waiting");
    if (first.kind !== "waiting") throw new Error("waiting attendu");
    expect(first.emit).toBe(true);
    const second = evaluateQueue(first.state, 10, options);
    expect(second.kind).toBe("waiting");
    if (second.kind !== "waiting") throw new Error("waiting attendu");
    expect(second.emit).toBe(false);
    expect(planQueue(second.state, 300).work?.kind).toBe("whole-stack-sweep");
  });
});

it("utilise le plancher et le plafond de réessai spécifiés", () => {
  expect(queryBackoffSeconds(1, 1)).toBe(60);
  expect(queryBackoffSeconds(1, 2)).toBe(120);
  expect(queryBackoffSeconds(60, 4)).toBe(300);
});

describe("barrière de revue", () => {
  it("bloque sur une revue requise au lieu de déclarer prête une PR bloquée", async () => {
    const snapshot = await readSnapshot({
      reader: fakeReader({
        facts: { reviewDecision: "REVIEW_REQUIRED", mergeStateStatus: "BLOCKED" },
      }),
      context: context(23),
      pendingHistory: "omit",
      allowDraft: false,
    });
    expect(classifyPr(snapshot)).toEqual({
      kind: "blocker",
      blocker: { kind: "merge-gate", pr: context(23), reason: "review-required" },
    });
    expect(
      selectTierMajorStackDecision([snapshot] as NonEmpty<typeof snapshot>)
    ).toMatchObject({
      kind: "blocker",
      blocker: { kind: "merge-gate", reason: "review-required" },
    });
  });

  it("bloque quand une protection de branche retient une PR approuvée à la CI propre", async () => {
    const snapshot = await readSnapshot({
      reader: fakeReader({ facts: { mergeStateStatus: "BLOCKED" } }),
      context: context(24),
      pendingHistory: "omit",
      allowDraft: false,
    });
    expect(classifyPr(snapshot)).toMatchObject({
      kind: "blocker",
      blocker: { kind: "merge-gate", reason: "merge-blocked" },
    });
  });

  it("attend les checks en cours avant de signaler la barrière de revue", async () => {
    const snapshot = await readSnapshot({
      reader: fakeReader({
        facts: { reviewDecision: "REVIEW_REQUIRED", mergeStateStatus: "BLOCKED" },
        fastPath: { kind: "checks", checks: [pendingCheck()] },
      }),
      context: context(26),
      pendingHistory: "omit",
      allowDraft: false,
    });
    expect(classifyPr(snapshot)).toMatchObject({ kind: "waiting" });
  });

  it("signale toujours les changements demandés comme barrière de fusion", async () => {
    const snapshot = await readSnapshot({
      reader: fakeReader({
        facts: { reviewDecision: "CHANGES_REQUESTED", mergeStateStatus: "BLOCKED" },
      }),
      context: context(25),
      pendingHistory: "omit",
      allowDraft: false,
    });
    expect(classifyPr(snapshot)).toMatchObject({
      kind: "blocker",
      blocker: { kind: "merge-gate", reason: "changes-requested" },
    });
  });
});

describe("une PR sans checks configurés", () => {
  const noChecks = {
    fastPath: { kind: "none-reported" },
    rollupPages: [{ kind: "no-rollup" }],
    commitRollups: [{ oid: "head", state: null }],
  } as const;
  const read = (overrides: Parameters<typeof fakeReader>[0] = {}) =>
    readSnapshot({
      reader: fakeReader({ ...noChecks, ...overrides }),
      context: context(30),
      pendingHistory: "omit",
      allowDraft: false,
    });

  it("est prête quand GitHub la déclare fusionnable", async () => {
    const snapshot = await read({ facts: { reviewDecision: null } });
    expect(classifyPr(snapshot)).toMatchObject({
      kind: "ready",
      pr: { proof: { ci: { kind: "ci-none" } } },
    });
  });

  it("s’arrête toujours sur les conflits, les fils de revue et les barrières de fusion", async () => {
    const thread = {
      id: "thread",
      firstComment: null,
      isBugbot: false,
      bugbotReviewPasses: 0,
    };
    const cases = [
      [{ facts: { mergeable: "CONFLICTING" } }, { kind: "merge-conflicts" }],
      [{ threads: [thread] }, { kind: "review-threads" }],
      [
        { facts: { reviewDecision: "REVIEW_REQUIRED" } },
        { kind: "merge-gate", reason: "review-required" },
      ],
      [
        { facts: { mergeStateStatus: "BLOCKED" } },
        { kind: "merge-gate", reason: "merge-blocked" },
      ],
      [{ facts: { isDraft: true } }, { kind: "merge-gate", reason: "draft-pr" }],
    ] as const;
    for (const [overrides, blocker] of cases)
      expect(classifyPr(await read(overrides))).toMatchObject({
        kind: "blocker",
        blocker,
      });
  });

  it("échoue ferme tant que le head n’a peut-être pas encore rapporté", async () => {
    const unsettled = [
      {
        commitRollups: [
          { oid: "earlier", state: "SUCCESS" },
          { oid: "head", state: null },
        ],
      },
      { commitRollups: [{ oid: "head", state: "PENDING" }] },
      { facts: { mergeable: "UNKNOWN", mergeStateStatus: "UNKNOWN" } },
    ] as const;
    for (const overrides of unsettled)
      await expect(read(overrides)).rejects.toMatchObject({
        failure: { kind: "checks-unavailable", retryable: true },
      });
  });
});

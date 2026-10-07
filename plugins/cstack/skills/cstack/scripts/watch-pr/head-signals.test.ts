import { describe, expect, it } from "bun:test";
import { chmod, mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fakeReader } from "./fakes.test-helper.ts";
import { GhGitHubReader, WatcherQueryError } from "./github.ts";
import { classifyPr, readSnapshot } from "./policy.ts";
import { parsePrNumber } from "./types.ts";
import type { GitHubReader, PrSnapshot } from "./types.ts";

const head = "84c02ea31c2e5bc80e5476321b5ed2acd7b660de";
const oldHead = "1".repeat(40);
const context = { owner: "owner", repo: "repo", number: parsePrNumber(90) };
const workflowRun = {
  id: 37642917873,
  workflow_id: 377554138,
  event: "pull_request",
  head_sha: head,
  name: "",
  status: "completed",
  conclusion: "startup_failure",
  run_attempt: 1,
  run_started_at: "2026-10-07T17:00:00Z",
  html_url: "https://github.com/owner/repo/actions/runs/37642917873",
};
const summary = {
  user: { login: "chatgpt-codex-connector[bot]" },
  updated_at: "2026-10-07T15:19:26.066172Z",
  html_url: "https://github.com/owner/repo/pull/90#issuecomment-1",
  body: `<!-- codex-pull-request-review-summary -->

## Codex Review Summary

This comment shows the latest Codex review activity on this pull request.

| Review | Status | Commit | Review trigger |
| --- | --- | --- | --- |
| 📝 **Code Review** | 🔄 **Running** since <relative-time datetime="2026-10-07T15:19:26.066172Z">2026-10-07T15:19:26.066172Z</relative-time> | \`84c02ea\` | PR opened |
`,
};

async function snapshotFromGh(args: {
  readonly runs?: readonly unknown[];
  readonly comments?: readonly unknown[];
  readonly actionsPages?: unknown;
  readonly commentsPages?: unknown;
  readonly actionsError?: boolean;
  readonly commentsError?: boolean;
}): Promise<PrSnapshot> {
  const directory = await mkdtemp(join(tmpdir(), "watch-head-signals-gh-"));
  const gh = join(directory, "gh");
  const runs = args.runs ?? [];
  const actions = args.actionsPages ?? [{ total_count: runs.length, workflow_runs: runs }];
  const comments = args.commentsPages ?? [args.comments ?? []];
  await writeFile(gh, `#!/bin/bash
case "$*" in
  *"repos/owner/repo/actions/runs?head_sha=${head}&per_page=100"*)
    ${args.actionsError ? 'echo "HTTP 502" >&2; exit 1' : ""}
    cat <<'ACTIONS_JSON'
${JSON.stringify(actions)}
ACTIONS_JSON
    ;;
  *"repos/owner/repo/issues/90/comments?per_page=100"*)
    ${args.commentsError ? 'echo "HTTP 502" >&2; exit 1' : ""}
    cat <<'COMMENTS_JSON'
${JSON.stringify(comments)}
COMMENTS_JSON
    ;;
  *) echo "appel gh inattendu: $*" >&2; exit 2;;
esac
`);
  await chmod(gh, 0o755);
  const original = process.env.PATH;
  process.env.PATH = original ? `${directory}:${original}` : directory;
  try {
    const client = new GhGitHubReader();
    const base = fakeReader({
      facts: { headRefOid: head },
      fastPath: { kind: "none-reported" },
      commitRollups: [{ oid: head, state: null }],
    });
    const reader: GitHubReader = {
      ...base,
      headSignals: (pr, sha) => client.headSignals(pr, sha),
    };
    return await readSnapshot({ reader, context, pendingHistory: "include", allowDraft: false });
  } finally {
    if (original === undefined) delete process.env.PATH;
    else process.env.PATH = original;
    await rm(directory, { recursive: true, force: true });
  }
}

describe("signaux du head lus via gh", () => {
  it("conserve chaque run actif même si un ID plus grand est déjà vert", async () => {
    for (const status of ["queued", "in_progress"]) {
      for (const started of ["2026-10-07T16:00:00Z", "2026-10-07T18:00:00Z", null]) {
        const row = await snapshotFromGh({ runs: [
          { ...workflowRun, id: 100, run_attempt: 2, status, conclusion: null, run_started_at: started },
          { ...workflowRun, id: 101, conclusion: "success" },
        ] });
        expect(classifyPr(row)).toMatchObject({
          kind: "waiting", pending: [{ reportedState: status.toUpperCase() }],
        });
      }
    }
  });

  it("conserve les résultats contradictoires quand leur chronologie est identique", async () => {
    const row = await snapshotFromGh({ runs: [
      { ...workflowRun, id: 100, conclusion: "failure" },
      { ...workflowRun, id: 101, conclusion: "success" },
    ] });
    expect(classifyPr(row)).toMatchObject({
      kind: "blocker", blocker: { kind: "failing-checks" },
    });
  });

  it("ordonne les résultats terminés par tentative récente, pas par ID", async () => {
    const newerSuccess = await snapshotFromGh({ runs: [
      { ...workflowRun, id: 100, run_attempt: 2, conclusion: "success", run_started_at: "2026-10-07T18:00:00Z" },
      { ...workflowRun, id: 101, conclusion: "cancelled" },
    ] });
    expect(classifyPr(newerSuccess)).toMatchObject({ kind: "ready" });
    const newerCancelled = await snapshotFromGh({ runs: [
      { ...workflowRun, id: 100, run_attempt: 2, conclusion: "cancelled", run_started_at: "2026-10-07T18:00:00Z" },
      { ...workflowRun, id: 101, conclusion: "success" },
    ] });
    expect(classifyPr(newerCancelled)).toMatchObject({
      kind: "blocker", blocker: { kind: "failing-checks" },
    });
  });

  it("attend le commentaire Codex Running rattaché au SHA abrégé actuel", async () => {
    const row = await snapshotFromGh({ comments: [summary] });
    expect(classifyPr(row)).toMatchObject({
      kind: "waiting", pending: [{ name: "Codex Code Review", reportedState: "RUNNING" }],
    });
    expect(row).toMatchObject({ reviewAutomationRunning: true });
  });

  it("bloque le startup_failure Actions sans check reporté", async () => {
    await expect(snapshotFromGh({ runs: [workflowRun] })).rejects.toThrow("CI indisponible: Actions startup_failure");
  });

  it("attend Actions en cours et conserve les vrais échecs comme bloqueurs CI", async () => {
    const pending = await snapshotFromGh({
      runs: [{ ...workflowRun, status: "in_progress", conclusion: null }],
    });
    expect(classifyPr(pending)).toMatchObject({ kind: "waiting" });
    const failed = await snapshotFromGh({ runs: [{ ...workflowRun, conclusion: "failure" }] });
    expect(classifyPr(failed)).toMatchObject({
      kind: "blocker", blocker: { kind: "failing-checks" },
    });
  });

  it("laisse prête une PR dont les deux sources ne rapportent aucun signal", async () => {
    expect(classifyPr(await snapshotFromGh({}))).toMatchObject({
      kind: "ready", pr: { headRefOid: head, proof: { ci: { kind: "ci-none" } } },
    });
  });

  it("ignore les signaux d’un autre SHA et les marqueurs copiés par un humain", async () => {
    const row = await snapshotFromGh({
      runs: [{ ...workflowRun, head_sha: oldHead }],
      comments: [
        { ...summary, body: summary.body.replace("84c02ea", oldHead.slice(0, 7)) },
        { ...summary, user: { login: "human" } },
      ],
    });
    expect(classifyPr(row)).toMatchObject({ kind: "ready", pr: { proof: { ci: { kind: "ci-none" } } } });
  });

  it("remplace une ancienne exécution échouée et un ancien résumé Running par leurs résultats récents", async () => {
    const row = await snapshotFromGh({
      runs: [workflowRun, { ...workflowRun, id: workflowRun.id + 1, conclusion: "success", run_started_at: "2026-10-07T18:00:00Z" }],
      comments: [summary, {
        ...summary,
        updated_at: "2026-10-07T16:00:00Z",
        body: summary.body.replace("Running", "Completed"),
      }],
    });
    expect(classifyPr(row)).toMatchObject({ kind: "ready", pr: { headRefOid: head } });
    expect(row).toMatchObject({ reviewAutomationRunning: false });
  });

  it("lit toutes les pages Actions et commentaires", async () => {
    const row = await snapshotFromGh({
      actionsPages: [
        { total_count: 2, workflow_runs: [{ ...workflowRun, conclusion: "success" }] },
        { total_count: 2, workflow_runs: [{ ...workflowRun, id: workflowRun.id + 1, workflow_id: 13, conclusion: "failure" }] },
      ],
      commentsPages: [[], [summary]],
    });
    expect(classifyPr(row)).toMatchObject({ kind: "blocker", blocker: { kind: "failing-checks" } });
  });

  it("échoue fermé sur les sources indisponibles, tronquées ou inconnues", async () => {
    const invalid = [
      { actionsError: true },
      { commentsError: true },
      { actionsPages: [] },
      { commentsPages: [] },
      { actionsPages: [{ total_count: 1, workflow_runs: [] }] },
      { runs: [workflowRun, workflowRun] },
      { runs: [{ ...workflowRun, status: "future_state" }] },
      { runs: [{ ...workflowRun, conclusion: null }] },
      { runs: [{ ...workflowRun, conclusion: "success", run_started_at: null }] },
      { runs: [{ ...workflowRun, conclusion: "success", run_started_at: "unknown" }] },
      { runs: [{ ...workflowRun, conclusion: "success", run_attempt: 0 }] },
      { comments: [{ ...summary, body: summary.body.replace("Running", "Starting") }] },
      { comments: [{ ...summary, body: summary.body.replace("84c02ea", "unknown") }] },
    ];
    for (const args of invalid)
      await expect(snapshotFromGh(args)).rejects.toBeInstanceOf(WatcherQueryError);
  });
});

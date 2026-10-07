import { spawn } from "node:child_process";
import type * as T from "./types.ts";
import { nonEmpty, parsePrNumber } from "./types.ts";
export const REVIEW_THREAD_PAGE_SIZE = 100;
export const OPEN_PR_LIST_LIMIT = 300;
export const REVIEW_THREADS_QUERY =
  "\nquery ReviewThreads($owner: String!, $repo: String!, $pr: Int!) {\n  repository(owner: $owner, name: $repo) {\n    pullRequest(number: $pr) {\n      reviewThreads(first: 100) {\n        pageInfo {\n          hasNextPage\n        }\n        nodes {\n          id\n          isResolved\n          comments(first: 10) {\n            nodes {\n              body\n              createdAt\n              path\n              line\n              author { login }\n            }\n          }\n        }\n      }\n    }\n  }\n}\n";
export const PR_COMMIT_STATUS_QUERY =
  "\nquery PrCommitStatuses($owner: String!, $repo: String!, $pr: Int!) {\n  repository(owner: $owner, name: $repo) {\n    pullRequest(number: $pr) {\n      commits(last: 50) {\n        nodes {\n          commit {\n            oid\n            statusCheckRollup {\n              state\n            }\n          }\n        }\n      }\n    }\n  }\n}\n";
export const PR_CHECK_ROLLUP_QUERY = `
query PrCheckRollup($owner: String!, $repo: String!, $head: String!, $after: String) {
  repository(owner: $owner, name: $repo) {
    object(expression: $head) {
      ... on Commit {
        oid
        statusCheckRollup {
          contexts(first: 100, after: $after) {
            pageInfo { hasNextPage endCursor }
            nodes {
              __typename
              ... on CheckRun { name status conclusion detailsUrl }
              ... on StatusContext { context state targetUrl }
            }
          }
        }
      }
    }
  }
}
`;

interface CommandResult {
  readonly code: number;
  readonly stdout: string;
  readonly stderr: string;
}
export class WatcherQueryError extends Error {
  readonly failure: T.QueryFailure;
  constructor(failure: T.QueryFailure) {
    super(failure.detail);
    this.name = "WatcherQueryError";
    this.failure = failure;
  }
}
export class ChecksUnavailable extends WatcherQueryError {
  constructor(detail: string) {
    super({ kind: "checks-unavailable", retryable: true, detail });
    this.name = "ChecksUnavailable";
  }
}
const firstLine = (value: string): string =>
  value.trim().split(/\r?\n/, 1)[0]?.slice(0, 240) ?? "";
function spawnFailure(command: string, error: unknown): WatcherQueryError {
  const code =
    error !== null &&
    typeof error === "object" &&
    "code" in error &&
    typeof error.code === "string"
      ? error.code
      : null;
  if (code === "ENOENT") {
    return new WatcherQueryError({
      kind: "missing-command",
      retryable: false,
      detail: `${command} n'est pas installe`,
    });
  }
  return new WatcherQueryError({
    kind: "command-exit",
    retryable: true,
    code: -1,
    detail: `${command} n'a pas demarre: ${error instanceof Error ? error.message : String(error)}`,
  });
}
function isAuthFailure(stderr: string): boolean {
  const text = stderr.toLowerCase();
  return (
    text.includes("not logged into any github hosts") ||
    text.includes("gh auth login") ||
    text.includes("authentication required") ||
    text.includes("bad credentials") ||
    text.includes("must re-authenticate") ||
    text.includes("authorization failed") ||
    text.includes("resource not accessible by integration") ||
    /\bhttp\s*40[13]\b/.test(text)
  );
}
function run(argv: readonly [string, ...string[]]): Promise<CommandResult> {
  return new Promise((resolve, reject) => {
    const child = spawn(argv[0], argv.slice(1), {
      stdio: ["ignore", "pipe", "pipe"],
    });
    let stdout = "";
    let stderr = "";
    let settled = false;
    const fail = (error: unknown): void => {
      if (settled) return;
      settled = true;
      reject(spawnFailure(argv[0], error));
    };
    const succeed = (result: CommandResult): void => {
      if (settled) return;
      settled = true;
      resolve(result);
    };
    if (child.stdout === null || child.stderr === null) {
      fail(new Error(`${argv[0]} spawned without stdio pipes`));
      return;
    }
    child.stdout.setEncoding("utf8");
    child.stderr.setEncoding("utf8");
    child.stdout.on("data", (chunk: string) => {
      stdout += chunk;
    });
    child.stderr.on("data", (chunk: string) => {
      stderr += chunk;
    });
    child.on("error", fail);
    child.on("close", (code) =>
      succeed({ code: code ?? -1, stdout, stderr })
    );
  });
}
function parseJson(text: string, label: string): unknown {
  try {
    return JSON.parse(text);
  } catch (error) {
    throw new WatcherQueryError({
      kind: "json-parse",
      retryable: true,
      detail: `${label}: ${error instanceof Error ? error.message : String(error)}`,
    });
  }
}
export async function runJson(argv: readonly [string, ...string[]]): Promise<unknown> {
  const result = await run(argv);
  if (result.code !== 0) {
    const detail =
      firstLine(result.stderr) || `${argv.join(" ")} s'est termine avec ${result.code}`;
    if (isAuthFailure(result.stderr))
      throw new WatcherQueryError({
        kind: "auth",
        retryable: false,
        code: result.code,
        detail,
      });
    throw new WatcherQueryError({
      kind: "command-exit",
      retryable: true,
      code: result.code,
      detail,
    });
  }
  return parseJson(result.stdout, argv.join(" "));
}
function raw(value: unknown): string {
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}
function missing(path: string, value?: unknown): never {
  throw new WatcherQueryError({
    kind: "missing-key",
    retryable: true,
    detail:
      value === undefined
        ? `${path} manquant`
        : `${path} invalide: ${raw(value)}`,
    ...(value === undefined ? {} : { rawValue: raw(value) }),
  });
}
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
function record(value: unknown, path: string): Record<string, unknown> {
  if (!isRecord(value)) missing(path, value);
  return value;
}
function list(value: unknown, path: string): readonly unknown[] {
  if (!Array.isArray(value)) missing(path, value);
  return value;
}
function at(value: unknown, path: readonly string[]): unknown {
  let current = value;
  for (const key of path) {
    const object = record(current, path.join("."));
    if (!(key in object)) missing(path.join("."));
    current = object[key];
  }
  return current;
}
function string(value: unknown, path: string): string {
  if (typeof value !== "string") missing(path, value);
  return value;
}
const optionalString = (value: unknown, path: string): string | null =>
  value === null ? null : string(value, path);
function repositoryIdentity(repository: T.Repository): string {
  return `${repository.owner.toLowerCase()}/${repository.repo.toLowerCase()}`;
}
function refIdentity(repository: T.Repository, refName: string): string {
  return `${repositoryIdentity(repository)}:${refName}`;
}
function parseNameWithOwner(value: unknown, path: string): T.Repository {
  const text = string(value, path);
  const parts = text.split("/");
  if (parts.length !== 2 || parts[0] === "" || parts[1] === "")
    missing(path, value);
  return { owner: parts[0], repo: parts[1] };
}
function parseOpenPullRequestRepository(
  object: Record<string, unknown>,
  path: string
): T.Repository {
  const repository = parseNameWithOwner(
    at(object, ["headRepository", "nameWithOwner"]),
    `${path}.headRepository.nameWithOwner`
  );
  const owner = string(
    at(object, ["headRepositoryOwner", "login"]),
    `${path}.headRepositoryOwner.login`
  );
  if (repository.owner.toLowerCase() !== owner.toLowerCase())
    missing(`${path}.headRepositoryOwner.login`, owner);
  return repository;
}
function enumValue<const V extends readonly string[]>(
  value: unknown,
  values: V,
  path: string
): V[number] {
  if (typeof value === "string")
    for (const candidate of values) if (candidate === value) return candidate;
  return missing(path, value);
}
const nullableEnum = <const V extends readonly string[]>(
  value: unknown,
  values: V,
  path: string
): V[number] | null => (value === null ? null : enumValue(value, values, path));
const MERGE_STATES = [
  "BEHIND",
  "BLOCKED",
  "CLEAN",
  "CONFLICTING",
  "DIRTY",
  "DRAFT",
  "HAS_HOOKS",
  "UNKNOWN",
  "UNSTABLE",
] as const satisfies readonly T.MergeStateStatus[];
const ROLLUP_STATES = [
  "ERROR",
  "EXPECTED",
  "FAILURE",
  "PENDING",
  "SUCCESS",
] as const;
const REVIEW_DECISIONS = [
  "APPROVED",
  "CHANGES_REQUESTED",
  "REVIEW_REQUIRED",
] as const;
// `gh pr view` signale l'absence de decision de revue par "", pas par null.
// Seul ce champ le fait; la normalisation reste donc ici plutot que dans
// nullableEnum, où elle empêcherait un état rollup vraiment inattendu
// d’échouer fermé.
const reviewDecision = (value: unknown): T.ReviewDecision =>
  nullableEnum(
    value === "" ? null : value,
    REVIEW_DECISIONS,
    "pull request.reviewDecision"
  );
function parseRemote(value: string): T.Repository | null {
  let normalized = value.trim();
  if (normalized.startsWith("git@github.com:"))
    normalized = `https://github.com/${normalized.slice(15)}`;
  if (normalized.startsWith("ssh://git@github.com/"))
    normalized = `https://github.com/${normalized.slice(21)}`;
  try {
    const url = new URL(normalized);
    const parts = url.pathname
      .replace(/\.git$/, "")
      .split("/")
      .filter(Boolean);
    if (
      url.protocol !== "https:" ||
      url.hostname !== "github.com" ||
      url.port ||
      url.username ||
      url.password ||
      url.search ||
      url.hash ||
      parts.length !== 2
    )
      return null;
    return { owner: parts[0], repo: parts[1] };
  } catch {
    return null;
  }
}
function parsePrUrl(value: string): T.PrContext {
  try {
    const url = new URL(value);
    const parts = url.pathname.split("/").filter(Boolean);
    if (
      url.protocol !== "https:" ||
      url.hostname !== "github.com" ||
      url.port ||
      url.username ||
      url.password ||
      url.search ||
      url.hash ||
      parts.length !== 4 ||
      parts[2] !== "pull"
    )
      throw new Error("URL de pull GitHub non canonique");
    return {
      owner: parts[0],
      repo: parts[1],
      number: parsePrNumber(Number(parts[3])),
    };
  } catch (error) {
    throw new WatcherQueryError({
      kind: "invalid-context-url",
      retryable: false,
      rawValue: value,
      detail: `impossible de deduire owner/repo depuis l'URL de PR: ${value} (${error instanceof Error ? error.message : String(error)})`,
    });
  }
}
function checkDetails(value: Record<string, unknown>, nameKey: string) {
  return {
    name: string(value[nameKey], nameKey),
    description: typeof value.description === "string" ? value.description : "",
    link:
      typeof value.link === "string"
        ? value.link
        : typeof value.detailsUrl === "string"
          ? value.detailsUrl
          : "",
    workflow: typeof value.workflow === "string" ? value.workflow : "",
  };
}
export function parseFastCheck(value: unknown): T.Check {
  const object = record(value, "check");
  const details = checkDetails(object, "name");
  const state = string(object.state, "check.state").toUpperCase();
  const bucket = string(object.bucket, "check.bucket");
  if (
    bucket === "fail" ||
    ["FAILURE", "ERROR", "ACTION_REQUIRED"].includes(state)
  )
    return { ...details, kind: "failed", reportedState: state };
  if (bucket === "pending") return pendingOrGate(details, state);
  if (bucket === "pass")
    return { ...details, kind: "passed", reportedState: state };
  if (bucket === "skipping")
    return { ...details, kind: "skipped", reportedState: state };
  return { ...details, kind: "failed", reportedState: state };
}
// The owner-approval gate is excluded from pending everywhere, so the rule has
// one home. Classifying it as pending on either read path makes the watcher
// wait on a human, which is the behaviour #172004 removed from the Python.
function pendingOrGate(
  details: {
    readonly name: string;
    readonly description: string;
    readonly link: string;
    readonly workflow: string;
  },
  reportedState: string
): T.Check {
  return details.name === "Code Review Gate"
    ? {
        ...details,
        kind: "code-review-gate",
        name: "Code Review Gate",
        reportedState,
      }
    : { ...details, kind: "pending", reportedState };
}
export function mapRollupNode(value: unknown): T.Check | null {
  const object = record(value, "rollup node");
  const typename = object.__typename;
  if (typename !== "CheckRun" && typename !== "StatusContext") return null;
  const details = checkDetails(
    object,
    typename === "CheckRun" ? "name" : "context"
  );
  const link =
    typeof object.targetUrl === "string" ? object.targetUrl : details.link;
  if (typename === "CheckRun") {
    const status =
      typeof object.status === "string" ? object.status.toUpperCase() : "";
    const conclusion =
      typeof object.conclusion === "string"
        ? object.conclusion.toUpperCase()
        : "";
    if (status !== "COMPLETED")
      return pendingOrGate({ ...details, link }, "PENDING");
    if (conclusion === "SUCCESS")
      return { ...details, link, kind: "passed", reportedState: "SUCCESS" };
    if (conclusion === "NEUTRAL" || conclusion === "SKIPPED")
      return { ...details, link, kind: "skipped", reportedState: conclusion };
    return {
      ...details,
      link,
      kind: "failed",
      reportedState: conclusion === "ACTION_REQUIRED" ? conclusion : "FAILURE",
    };
  }
  const state =
    typeof object.state === "string" ? object.state.toUpperCase() : "";
  if (state === "PENDING" || state === "EXPECTED")
    return pendingOrGate({ ...details, link }, "PENDING");
  return state === "SUCCESS"
    ? { ...details, link, kind: "passed", reportedState: state }
    : { ...details, link, kind: "failed", reportedState: state || "FAILURE" };
}
function parseComment(value: unknown): T.ReviewComment {
  const object = record(value, "review comment");
  const author =
    object.author === null
      ? null
      : record(object.author, "review comment.author");
  return {
    authorLogin:
      author === null
        ? null
        : optionalString(author.login, "review comment.author.login"),
    body: string(object.body, "review comment.body"),
    path: optionalString(object.path, "review comment.path"),
    line:
      object.line === null
        ? null
        : Number.isInteger(object.line)
          ? Number(object.line)
          : missing("review comment.line", object.line),
    createdAt: string(object.createdAt, "review comment.createdAt"),
  };
}
function isBugbot(comment: T.ReviewComment | null): boolean {
  if (comment === null) return false;
  const author = (comment.authorLogin ?? "").toLowerCase();
  const body = comment.body.toLowerCase();
  return (
    author.includes("bugbot") ||
    (author === "cursor" &&
      [
        "bugbot",
        "cursor_automation_id",
        "agentic security review",
        "description start",
        "severity",
      ].some((token) => body.includes(token)))
  );
}
function passKey(comment: T.ReviewComment | null): string | null {
  if (comment === null) return null;
  for (const pattern of [
    /RUN_ID:\s*([a-zA-Z0-9_.:-]+)/,
    /CURSOR_AUTOMATION_ID:\s*([a-zA-Z0-9_.:-]+)/,
  ]) {
    const match = pattern.exec(comment.body);
    if (match?.[1]) return match[1];
  }
  return null;
}
export function parseReviewThreads(value: unknown): readonly T.ReviewThread[] {
  const connection = record(
    at(value, ["data", "repository", "pullRequest", "reviewThreads"]),
    "reviewThreads"
  );
  const page = record(connection.pageInfo, "reviewThreads.pageInfo");
  if (typeof page.hasNextPage !== "boolean")
    missing("reviewThreads.pageInfo.hasNextPage", page.hasNextPage);
  if (page.hasNextPage) {
    throw new WatcherQueryError({
      kind: "truncated",
      retryable: false,
      detail:
        "la page reviewThreads est pleine et d’autres pages existent; des fils non résolus peuvent être masqués",
    });
  }
  const nodes = list(connection.nodes, "reviewThreads.nodes");
  const threads: {
    readonly id: string;
    readonly firstComment: T.ReviewComment | null;
    readonly resolved: boolean;
  }[] = [];
  for (const node of nodes) {
    const thread = record(node, "review thread");
    if (typeof thread.isResolved !== "boolean")
      missing("review thread.isResolved", thread.isResolved);
    const comments = list(
      at(thread, ["comments", "nodes"]),
      "review thread.comments.nodes"
    );
    threads.push({
      id: string(thread.id, "review thread.id"),
      firstComment: comments.length === 0 ? null : parseComment(comments[0]),
      resolved: thread.isResolved,
    });
  }
  const keys = new Set<string>();
  let keyless = false;
  for (const thread of threads) {
    if (!isBugbot(thread.firstComment)) continue;
    const key = passKey(thread.firstComment);
    if (key === null) keyless = true;
    else keys.add(key);
  }
  const passes = keys.size > 0 ? keys.size : keyless ? 1 : 0;
  return threads
    .filter((thread) => !thread.resolved)
    .map(({ id, firstComment }) => ({
      id,
      firstComment,
      isBugbot: isBugbot(firstComment),
      bugbotReviewPasses: passes,
    }));
}
export function parsePullRequest(
  value: unknown,
  context: T.PrContext
): T.PullRequestFacts {
  const object = record(value, "pull request");
  if (typeof object.isDraft !== "boolean")
    missing("pull request.isDraft", object.isDraft);
  return {
    context,
    mergeable: enumValue(
      object.mergeable,
      ["MERGEABLE", "CONFLICTING", "UNKNOWN"] as const,
      "pull request.mergeable"
    ),
    mergeStateStatus: enumValue(
      object.mergeStateStatus,
      MERGE_STATES,
      "pull request.mergeStateStatus"
    ),
    reviewDecision: reviewDecision(object.reviewDecision),
    headRefOid: optionalString(object.headRefOid, "pull request.headRefOid"),
    headRefName: string(object.headRefName, "pull request.headRefName"),
    baseRefName: string(object.baseRefName, "pull request.baseRefName"),
    state: enumValue(
      object.state,
      ["OPEN", "CLOSED", "MERGED"] as const,
      "pull request.state"
    ),
    mergedAt: optionalString(object.mergedAt, "pull request.mergedAt"),
    isDraft: object.isDraft,
  };
}
function graphqlArgs(
  query: string,
  context: T.PrContext
): [string, ...string[]] {
  return [
    "gh",
    "api",
    "graphql",
    "-f",
    `query=${query}`,
    "-f",
    `owner=${context.owner}`,
    "-f",
    `repo=${context.repo}`,
    "-F",
    `pr=${context.number}`,
  ];
}

export function parseOpenPullRequests(
  value: unknown,
  baseRepository: T.Repository
): readonly T.OpenPullRequest[] {
  const rows = list(value, "open PRs");
  if (rows.length >= OPEN_PR_LIST_LIMIT) {
    throw new WatcherQueryError({
      kind: "truncated",
      retryable: false,
      detail: `gh pr list a renvoyé ${OPEN_PR_LIST_LIMIT} PR; la découverte de pile peut être incomplète`,
    });
  }
  return rows.map((item, index) => {
    const object = record(item, `open PRs[${index}]`);
    const path = `open PRs[${index}]`;
    return {
      number: parsePrNumber(object.number, `${path}.number`),
      headRepository: parseOpenPullRequestRepository(object, path),
      headRefName: string(object.headRefName, `${path}.headRefName`),
      baseRepository: {
        owner: baseRepository.owner,
        repo: baseRepository.repo,
      },
      baseRefName: string(object.baseRefName, `${path}.baseRefName`),
    };
  });
}
function actionSignals(
  value: unknown,
  context: T.PrContext,
  headRefOid: string,
  headRefName: string
): readonly T.Check[] {
  const pages = list(value, "actions pages");
  if (pages.length === 0) missing("actions pages");
  const runs: unknown[] = [];
  let expected: number | null = null;
  for (const item of pages) {
    const page = record(item, "actions page");
    if (typeof page.total_count !== "number" || !Number.isSafeInteger(page.total_count) || page.total_count < 0)
      missing("actions total_count", page.total_count);
    if (expected !== null && expected !== page.total_count)
      throw new ChecksUnavailable("la liste Actions a changé pendant la pagination");
    expected = page.total_count;
    runs.push(...list(page.workflow_runs, "workflow_runs"));
  }
  if (runs.length !== expected)
    throw new ChecksUnavailable("la liste Actions est tronquée pour le head demandé");
  const latest = new Map<string, { readonly started: number; readonly runs: readonly Record<string, unknown>[] }>();
  const active: Record<string, unknown>[] = [];
  const seen = new Set<number>();
  for (const item of runs) {
    const run = record(item, "workflow run");
    if (typeof run.id !== "number" || !Number.isSafeInteger(run.id) || run.id <= 0)
      missing("workflow run.id", run.id);
    if (seen.has(run.id)) throw new ChecksUnavailable("la pagination Actions contient un run en double");
    seen.add(run.id);
    if (string(run.head_sha, "workflow run.head_sha") !== headRefOid) continue;
    const event = string(run.event, "workflow run.event");
    const associations = list(run.pull_requests, "workflow run.pull_requests");
    if (associations.length > 0) {
      let matches = false;
      for (const item of associations) {
        const association = record(item, "workflow run.pull_requests entry");
        if (typeof association.number !== "number" || !Number.isSafeInteger(association.number) || association.number <= 0)
          missing("workflow run.pull_requests number", association.number);
        if (association.number !== context.number) continue;
        const base = record(at(association, ["base", "repo"]), "workflow run.pull_requests base repo");
        const repositoryUrl = string(base.url, "workflow run.pull_requests base repo.url");
        if (repositoryUrl.toLowerCase() !== `https://api.github.com/repos/${context.owner}/${context.repo}`.toLowerCase()) continue;
        const head = record(association.head, "workflow run.pull_requests head");
        if (string(head.sha, "workflow run.pull_requests head.sha") !== headRefOid ||
            string(head.ref, "workflow run.pull_requests head.ref") !== headRefName)
          throw new ChecksUnavailable(`association PR Actions incohérente pour #${context.number}, run=${run.id}`);
        matches = true;
      }
      if (!matches) continue;
    } else {
      if (headRefName.length === 0)
        throw new ChecksUnavailable("branche du head indisponible pour les signaux Actions");
      if (string(run.head_branch, "workflow run.head_branch") !== headRefName) continue;
      if (event === "pull_request" || event === "pull_request_target")
        throw new ChecksUnavailable(`association PR Actions indisponible pour #${context.number}, run=${run.id}`);
    }
    if (typeof run.workflow_id !== "number" || !Number.isSafeInteger(run.workflow_id) || run.workflow_id <= 0)
      missing("workflow run.workflow_id", run.workflow_id);
    if (typeof run.run_attempt !== "number" || !Number.isSafeInteger(run.run_attempt) || run.run_attempt <= 0)
      missing("workflow run.run_attempt", run.run_attempt);
    const key = `${run.workflow_id}:${event}`;
    if (string(run.status, "workflow run.status") !== "completed") {
      active.push(run);
      continue;
    }
    const started = Date.parse(string(run.run_started_at, "workflow run.run_started_at"));
    if (!Number.isFinite(started))
      throw new ChecksUnavailable(`chronologie Actions inconnue pour ${headRefOid}, run=${run.id}`);
    const previous = latest.get(key);
    if (previous === undefined || started > previous.started)
      latest.set(key, { started, runs: [run] });
    else if (started === previous.started)
      latest.set(key, { started, runs: [...previous.runs, run] });
  }
  return [...active, ...[...latest.values()].flatMap((entry) => entry.runs)].map((run): T.Check => {
    const status = string(run.status, "workflow run.status");
    const conclusion = optionalString(run.conclusion, "workflow run.conclusion");
    const details = {
      name: `Actions: ${string(run.name, "workflow run.name") || `workflow ${run.workflow_id}`}`,
      description: `workflow run ${run.id}, attempt=${run.run_attempt}, head=${headRefOid}`,
      link: string(run.html_url, "workflow run.html_url"),
      workflow: String(run.workflow_id),
    };
    let check: T.Check;
    if (["queued", "in_progress", "waiting", "pending", "requested"].includes(status))
      check = { ...details, kind: "pending", reportedState: status.toUpperCase() };
    else if (status !== "completed")
      throw new ChecksUnavailable(`état Actions inconnu pour ${headRefOid}: ${status}`);
    else if (conclusion === "startup_failure")
      throw new ChecksUnavailable(`CI indisponible: Actions startup_failure pour ${headRefOid}, run=${run.id}, ${details.link}`);
    else if (conclusion === "success")
      check = { ...details, kind: "passed", reportedState: "SUCCESS" };
    else if (conclusion === "neutral" || conclusion === "skipped")
      check = { ...details, kind: "skipped", reportedState: conclusion.toUpperCase() };
    else if (conclusion !== null && ["failure", "timed_out", "cancelled", "action_required", "stale"].includes(conclusion))
      check = { ...details, kind: "failed", reportedState: conclusion.toUpperCase() };
    else
      throw new ChecksUnavailable(`conclusion Actions inconnue pour ${headRefOid}: ${conclusion}`);
    return check;
  });
}

function codexReviewSignals(value: unknown, headRefOid: string): readonly T.Check[] {
  const pages = list(value, "comments pages");
  if (pages.length === 0) missing("comments pages");
  let latest: { readonly updated: number; readonly checks: readonly T.Check[] } | null = null;
  let expected = false;
  for (const item of pages.flatMap((page) => list(page, "comments page"))) {
    const comment = record(item, "issue comment");
    const user = record(comment.user, "issue comment.user");
    if (string(user.login, "issue comment.user.login") !== "chatgpt-codex-connector[bot]") continue;
    const body = string(comment.body, "issue comment.body");
    if (!body.includes("<!-- codex-pull-request-review-summary -->")) continue;
    expected = true;
    const updated = Date.parse(string(comment.updated_at, "issue comment.updated_at"));
    if (!Number.isFinite(updated)) missing("issue comment.updated_at", comment.updated_at);
    const rows = body.split(/\r?\n/).filter((line) => /\|[^|]*\bCode Review\b[^|]*\|/.test(line));
    if (rows.length === 0) throw new ChecksUnavailable("résumé Codex sans état Code Review lisible");
    const checks: T.Check[] = [];
    let current = false;
    for (const row of rows) {
      const cells = row.split("|").slice(1, -1);
      const sha = cells[2]?.match(/`([0-9a-f]{7,40})`/i)?.[1]?.toLowerCase();
      if (sha === undefined) throw new ChecksUnavailable("résumé Codex sans SHA vérifiable");
      if (!headRefOid.toLowerCase().startsWith(sha)) continue;
      current = true;
      const state = cells[1]?.match(/\b(Running|Queued|Pending|Completed|Failed|Cancelled|Error)\b/i)?.[1]?.toLowerCase();
      if (state === undefined) throw new ChecksUnavailable(`état de revue Codex inconnu pour ${headRefOid}`);
      if (state === "completed") continue;
      checks.push({
        kind: ["running", "queued", "pending"].includes(state) ? "pending" : "failed",
        name: "Codex Code Review",
        reportedState: state.toUpperCase(),
        description: `résumé Codex ${state}, head=${headRefOid}`,
        link: string(comment.html_url, "issue comment.html_url"),
        workflow: "",
      });
    }
    if (current && (latest === null || updated >= latest.updated)) latest = { updated, checks };
  }
  if (latest !== null) return latest.checks;
  if (!expected) return [];
  return [{
    kind: "pending",
    name: "Codex Code Review",
    reportedState: "AWAITING_CURRENT_HEAD",
    description: `revue Codex attendue pour le head ${headRefOid}; seul un ancien résumé est disponible`,
    link: "",
    workflow: "",
  }];
}

export class GhGitHubReader implements T.GitHubReader {
  async headSignals(context: T.PrContext, headRefOid: string, headRefName: string): Promise<readonly T.Check[]> {
    const repository = `repos/${context.owner}/${context.repo}`;
    const runs = await runJson([
      "gh", "api", "--paginate", "--slurp",
      `${repository}/actions/runs?head_sha=${encodeURIComponent(headRefOid)}&per_page=100`,
    ]);
    const comments = await runJson([
      "gh", "api", "--paginate", "--slurp",
      `${repository}/issues/${context.number}/comments?per_page=100`,
    ]);
    return [...actionSignals(runs, context, headRefOid, headRefName), ...codexReviewSignals(comments, headRefOid)];
  }
  async originRepo(): Promise<T.Repository | null> {
    const result = await run(["git", "remote", "get-url", "origin"]);
    return result.code === 0 ? parseRemote(result.stdout) : null;
  }
  async currentPr(pr: T.PrNumber | null): Promise<T.PrContext> {
    const argv: [string, ...string[]] = ["gh", "pr", "view"];
    if (pr !== null) argv.push(String(pr));
    argv.push("--json", "number,url");
    const object = record(await runJson(argv), "current PR");
    const parsed = parsePrUrl(string(object.url, "current PR.url"));
    return {
      ...parsed,
      number: pr ?? parsePrNumber(object.number, "current PR.number"),
    };
  }
  async pullRequest(context: T.PrContext): Promise<T.PullRequestFacts> {
    return parsePullRequest(
      await runJson([
        "gh",
        "pr",
        "view",
        String(context.number),
        "--repo",
        `${context.owner}/${context.repo}`,
        "--json",
        "mergeable,mergeStateStatus,reviewDecision,headRefOid,headRefName,baseRefName,state,mergedAt,isDraft",
      ]),
      context
    );
  }
  async openPullRequests(
    repository: T.Repository
  ): Promise<readonly T.OpenPullRequest[]> {
    const value = await runJson([
      "gh",
      "pr",
      "list",
      "--repo",
      `${repository.owner}/${repository.repo}`,
      "--state",
      "open",
      "--limit",
      String(OPEN_PR_LIST_LIMIT),
      "--json",
      "number,headRepository,headRepositoryOwner,headRefName,baseRefName",
    ]);
    return parseOpenPullRequests(value, repository);
  }
  async checksFastPath(context: T.PrContext): Promise<T.ChecksFastPath> {
    const result = await run([
      "gh",
      "pr",
      "checks",
      String(context.number),
      "--repo",
      `${context.owner}/${context.repo}`,
      "--json",
      "name,state,description,link,workflow,bucket",
    ]);
    if ([0, 1, 8].includes(result.code) && result.stdout.trim()) {
      try {
        const value = parseJson(result.stdout, "gh pr checks");
        if (Array.isArray(value))
          return { kind: "checks", checks: value.map(parseFastCheck) };
      } catch (error) {
        if (!(error instanceof WatcherQueryError)) throw error;
      }
    }
    // Seule cette ligne stderr de gh signifie qu'il a lu le commit head sans y
    // trouver de check. Toute autre sortie 1 est une requête en échec.
    if (
      result.code === 1 &&
      firstLine(result.stderr).startsWith("no checks reported on the ")
    )
      return { kind: "none-reported" };
    return { kind: "unusable", exitCode: result.code, stderr: result.stderr };
  }
  async checkRollupPage(
    context: T.PrContext,
    after: string | null,
    headRefOid: string
  ): Promise<T.RollupPage> {
    const argv: [string, ...string[]] = [
      "gh",
      "api",
      "graphql",
      "-f",
      `query=${PR_CHECK_ROLLUP_QUERY}`,
      "-f",
      `owner=${context.owner}`,
      "-f",
      `repo=${context.repo}`,
      "-f",
      `head=${headRefOid}`,
    ];
    if (after !== null) argv.push("-f", `after=${after}`);
    const value = await runJson(argv);
    const commit = record(at(value, ["data", "repository", "object"]), "commit");
    if (string(commit.oid, "commit.oid") !== headRefOid)
      throw new ChecksUnavailable(
        `le rollup ne correspond pas au head ${headRefOid}`
      );
    if (commit.statusCheckRollup === null) return { kind: "no-rollup" };
    const contexts = record(
      at(commit, ["statusCheckRollup", "contexts"]),
      "contexts"
    );
    const checks = list(contexts.nodes, "contexts.nodes")
      .map(mapRollupNode)
      .filter((check): check is T.Check => check !== null);
    const page = record(contexts.pageInfo, "contexts.pageInfo");
    if (typeof page.hasNextPage !== "boolean")
      missing("contexts.pageInfo.hasNextPage", page.hasNextPage);
    const cursor = optionalString(
      page.endCursor,
      "contexts.pageInfo.endCursor"
    );
    return {
      kind: "contexts",
      checks,
      endCursor: page.hasNextPage && cursor ? cursor : null,
    };
  }
  async reviewThreads(
    context: T.PrContext
  ): Promise<readonly T.ReviewThread[]> {
    return parseReviewThreads(
      await runJson(graphqlArgs(REVIEW_THREADS_QUERY, context))
    );
  }
  async commitRollups(
    context: T.PrContext
  ): Promise<readonly T.CommitRollup[]> {
    const value = await runJson(graphqlArgs(PR_COMMIT_STATUS_QUERY, context));
    const commits = list(
      at(value, ["data", "repository", "pullRequest", "commits", "nodes"]),
      "commits.nodes"
    );
    return commits.map((item, index) => {
      const commit = record(at(item, ["commit"]), `commits[${index}].commit`);
      const rollup = commit.statusCheckRollup;
      return {
        oid: string(commit.oid, `commits[${index}].oid`),
        state:
          rollup === null
            ? null
            : nullableEnum(
                at(rollup, ["state"]),
                ROLLUP_STATES,
                `commits[${index}].statusCheckRollup.state`
              ),
      };
    });
  }
}

export async function resolveChecks(
  reader: T.GitHubReader,
  context: T.PrContext,
  headRefOid: string
): Promise<T.CheckRead> {
  const checks: T.Check[] = [];
  let after: string | null = null;
  let headHasRollup = true;
  do {
    const page = await reader.checkRollupPage(context, after, headRefOid);
    if (page.kind === "no-rollup") {
      headHasRollup = false;
      break;
    }
    checks.push(...page.checks);
    after = page.endCursor;
  } while (after !== null);
  const fallback = nonEmpty(checks);
  if (fallback !== null)
    return { kind: "reported", source: "graphql-rollup", checks: fallback };
  if (!headHasRollup) {
    // Confirme l'absence depuis gh, puis readSnapshot revalide le head de la PR.
    const fast = await reader.checksFastPath(context);
    if (fast.kind === "none-reported") return { kind: "no-checks" };
  }
  throw new ChecksUnavailable(`impossible de lire les checks du head ${headRefOid}`);
}
export async function resolveContext(args: {
  readonly reader: T.GitHubReader;
  readonly owner: string | null;
  readonly repo: string | null;
  readonly pr: T.PrNumber | null;
}): Promise<T.PrContext> {
  if (args.pr !== null && args.owner !== null && args.repo !== null)
    return { owner: args.owner, repo: args.repo, number: args.pr };
  if (args.pr !== null) {
    const origin = await args.reader.originRepo();
    if (origin !== null)
      return {
        owner: args.owner ?? origin.owner,
        repo: args.repo ?? origin.repo,
        number: args.pr,
      };
  }
  const inferred = await args.reader.currentPr(args.pr);
  return {
    owner: args.owner ?? inferred.owner,
    repo: args.repo ?? inferred.repo,
    number: args.pr ?? inferred.number,
  };
}
export function orderStack(
  context: T.PrContext,
  open: readonly T.OpenPullRequest[]
): T.NonEmpty<T.PrContext> {
  const byNumber = new Map(open.map((pr) => [pr.number, pr]));
  const byHead = new Map<string, T.OpenPullRequest[]>();
  for (const pr of open) {
    const key = refIdentity(pr.headRepository, pr.headRefName);
    byHead.set(key, [...(byHead.get(key) ?? []), pr]);
  }
  const children = new Map<string, T.OpenPullRequest[]>();
  for (const pr of open) {
    const key = refIdentity(pr.baseRepository, pr.baseRefName);
    children.set(key, [...(children.get(key) ?? []), pr]);
  }
  for (const values of children.values())
    values.sort((a, b) => a.number - b.number);
  const start = byNumber.get(context.number);
  if (start === undefined) return [context];
  const parentFor = (child: T.OpenPullRequest): T.OpenPullRequest | null => {
    const key = refIdentity(child.baseRepository, child.baseRefName);
    const matches = byHead.get(key) ?? [];
    if (matches.length > 1) {
      throw new WatcherQueryError({
        kind: "stack-ambiguous",
        retryable: false,
        detail:
          `la pile de PR contient ${matches.length} parents possibles pour ` +
          `${child.baseRepository.owner}/${child.baseRepository.repo}:${child.baseRefName}`,
      });
    }
    return matches[0] ?? null;
  };
  const seen = new Set<T.PrNumber>([start.number]);
  const down: T.OpenPullRequest[] = [];
  let current = start;
  while (true) {
    const parent = parentFor(current);
    if (parent === null) break;
    if (seen.has(parent.number)) {
      throw new WatcherQueryError({
        kind: "stack-cycle",
        retryable: false,
        detail:
          `la pile de PR contient un cycle a ` +
          `${parent.headRepository.owner}/${parent.headRepository.repo}:${parent.headRefName}`,
      });
    }
    seen.add(parent.number);
    down.push(parent);
    current = parent;
  }
  const up: T.OpenPullRequest[] = [];
  const visit = (parent: T.OpenPullRequest): void => {
    for (const child of
      children.get(refIdentity(parent.headRepository, parent.headRefName)) ??
      []) {
      if (seen.has(child.number)) continue;
      seen.add(child.number);
      up.push(child);
      visit(child);
    }
  };
  visit(start);
  return (
    nonEmpty(
      [...down.reverse(), start, ...up].map((pr) => ({
        ...context,
        number: pr.number,
      }))
    ) ?? [context]
  );
}
export async function discoverStack(
  reader: T.GitHubReader,
  context: T.PrContext
): Promise<T.NonEmpty<T.PrContext>> {
  return orderStack(context, await reader.openPullRequests(context));
}

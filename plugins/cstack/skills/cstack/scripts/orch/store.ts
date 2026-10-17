import { execFileSync } from "node:child_process";
import { randomUUID } from "node:crypto";
import type { Dirent, Stats } from "node:fs";
import {
  access,
  lstat,
  mkdir,
  readFile,
  readdir,
  rename,
  rm,
  rmdir,
  unlink,
  writeFile,
} from "node:fs/promises";
import { basename, dirname, join, resolve } from "node:path";

import { loadHorizon, horizonBrief, overlappingScopes, type HorizonDefinition } from "./horizon.ts";

const LEGACY_UNIT_HEADER = "id\ttrack\tstate\tbranch\tpr\tsha\tbrief";
const UNIT_HEADER = `${LEGACY_UNIT_HEADER}\towner`;
const LEDGER_HEADER = "pr\tsha\tverdict\tevidence\tverifier\tts";
const LOCK_FILE = ".orch.lock";
const LOCK_CONFLICT_CODES = new Set(["EEXIST", "ENOTEMPTY", "ENOTDIR", "EISDIR", "EPERM"]);

export type Verdict =
  | "live-ui-verified"
  | "unit-test-verified"
  | "type-check-only"
  | "verifier-blocked"
  | "verifier-failed";

export interface Unit {
  readonly owner?: string;
  readonly id: string;
  readonly track: string;
  readonly state: string;
  readonly branch: string;
  readonly pr: string;
  readonly sha: string;
  readonly brief: string;
}

export interface LedgerEntry {
  readonly pr: string;
  readonly sha: string;
  readonly verdict: Verdict;
  readonly evidence: string;
  readonly verifier: string;
  readonly ts: string;
}

export interface InboxPointer {
  readonly ts: string;
  readonly agent: string;
  readonly unit: string;
  readonly status: string;
  readonly report: string;
}

export interface InboxPushResult {
  readonly pointer: InboxPointer;
  readonly filename: string;
}

export interface OpenGate {
  readonly kind: "open";
  readonly id: string;
  readonly question: string;
  readonly options: string;
  readonly defaultAnswer: string;
}

export interface ResolvedGate {
  readonly kind: "resolved";
  readonly id: string;
  readonly question: string;
  readonly options: string;
  readonly defaultAnswer: string;
  readonly answer: string;
}

export type Gate = OpenGate | ResolvedGate;

export type FrontierPrState = "OPEN" | "MERGED" | "CLOSED";

export interface FrontierPr {
  readonly pr: number;
  readonly branches: string;
  readonly sha: string;
  readonly state: FrontierPrState;
}

export interface Frontier {
  readonly generation: number;
  readonly prs: readonly FrontierPr[];
  readonly lowestUnmerged: number | null;
  readonly closedGap: number | null;
}

export interface StandingLine {
  readonly number: number;
  readonly line: string;
}

export type Counts = Readonly<Record<string, number>>;

export interface StatusSummary {
  readonly unitStates: Counts;
  readonly ledgerVerdicts: Counts;
  readonly frontierGeneration: number;
  readonly openGateIds: readonly string[];
}

export interface StatusReport {
  readonly units: readonly Unit[];
  readonly ledger: readonly LedgerEntry[];
  readonly frontier: Frontier;
  readonly gates: readonly Gate[];
  readonly summary: StatusSummary;
  readonly changed: string;
}

export interface AddUnitParams {
  readonly id: string;
  readonly track: string;
  readonly brief?: string;
}

export interface SetUnitParams {
  readonly id: string;
  readonly state: string;
  readonly branch?: string;
  readonly pr?: number;
  readonly sha?: string;
}

export interface ListUnitsParams {
  readonly state?: string;
  readonly track?: string;
}

export interface RecordLedgerParams {
  readonly pr: number;
  readonly sha: string;
  readonly verdict: Verdict;
  readonly evidence: string;
  readonly verifier?: string;
}

export interface CheckLedgerParams {
  readonly pr: number;
  readonly sha: string;
}

export interface PushInboxParams {
  readonly agent: string;
  readonly unit: string;
  readonly status: string;
  readonly report?: string;
}

export interface ParkGateParams {
  readonly id: string;
  readonly question: string;
  readonly options: string;
  readonly defaultAnswer: string;
}

export interface ResolveGateParams {
  readonly id: string;
  readonly answer: string;
}

export interface SetFrontierParams {
  readonly repo: string;
  readonly prs?: readonly number[];
}

export interface AddStandingParams {
  readonly line: string;
}

export interface OpenStoreOptions {
  readonly force?: boolean;
  // Les rappels signalent une tentative de reprise, pas une acquisition réussie.
  readonly onLockStolen?: (holder: string) => void;
  readonly onStaleLock?: (holder: string) => void;
}

export interface ReadyUnits {
  readonly ready: readonly string[];
  readonly blocked: readonly { readonly id: string; readonly reason: string }[];
}

export interface Store {
  readonly handoff: {
    readonly import: (spec: string) => Promise<{ readonly added: readonly string[]; readonly reused: readonly string[]; readonly digest: string }>;
    readonly ready: (repo: string) => Promise<ReadyUnits>;
    readonly claim: (params: { readonly id: string; readonly owner: string; readonly branch: string; readonly repo: string }) => Promise<Unit>;
  };
  readonly units: {
    readonly add: (params: AddUnitParams) => Promise<Unit>;
    readonly set: (params: SetUnitParams) => Promise<Unit>;
    readonly get: (id: string) => Promise<Unit>;
    readonly list: (params?: ListUnitsParams) => Promise<readonly Unit[]>;
    readonly counts: () => Promise<Counts>;
  };
  readonly ledger: {
    readonly record: (params: RecordLedgerParams) => Promise<LedgerEntry>;
    readonly check: (params: CheckLedgerParams) => Promise<LedgerEntry>;
    readonly summary: () => Promise<Counts>;
  };
  readonly inbox: {
    readonly push: (params: PushInboxParams) => Promise<InboxPushResult>;
    readonly drain: () => Promise<readonly InboxPointer[]>;
    readonly peek: () => Promise<readonly InboxPointer[]>;
    readonly count: () => Promise<number>;
  };
  readonly gates: {
    readonly park: (params: ParkGateParams) => Promise<OpenGate>;
    readonly list: () => Promise<readonly OpenGate[]>;
    readonly resolve: (params: ResolveGateParams) => Promise<ResolvedGate>;
  };
  readonly frontier: {
    readonly set: (params: SetFrontierParams) => Promise<Frontier>;
    readonly show: () => Promise<Frontier>;
  };
  readonly standing: {
    readonly show: () => Promise<readonly StandingLine[]>;
    readonly add: (params: AddStandingParams) => Promise<StandingLine>;
  };
  readonly status: {
    readonly render: () => Promise<StatusReport>;
  };
  readonly init: () => Promise<{ readonly store: string }>;
  readonly close: () => Promise<void>;
}

export interface NotFoundOutput {
  readonly compact: string;
  readonly json: unknown;
}

export class UserError extends Error {}
export class UsageError extends UserError {}
export class NotFoundError extends UserError {
  public constructor(
    message: string,
    public readonly output?: NotFoundOutput
  ) {
    super(message);
  }
}

function errorCode(error: unknown): string | null {
  if (
    error !== null &&
    typeof error === "object" &&
    "code" in error &&
    typeof error.code === "string"
  ) {
    return error.code;
  }
  return null;
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function isUnknownArray(value: unknown): value is readonly unknown[] {
  return Array.isArray(value);
}

function verdictOrNull(value: string): Verdict | null {
  switch (value) {
    case "live-ui-verified":
    case "unit-test-verified":
    case "type-check-only":
    case "verifier-blocked":
    case "verifier-failed":
      return value;
    default:
      return null;
  }
}

function frontierPrStateOrNull(value: unknown): FrontierPrState | null {
  switch (value) {
    case "OPEN":
    case "MERGED":
    case "CLOSED":
      return value;
    default:
      return null;
  }
}

export function parseVerdict(value: string): Verdict {
  const verdict = verdictOrNull(value);
  if (verdict === null) {
    throw new UserError(
      "le verdict doit être live-ui-verified, unit-test-verified, type-check-only, verifier-blocked ou verifier-failed"
    );
  }
  return verdict;
}

function cleanCell(value: string): string {
  const cleaned = value.replace(/[\t\n\r]/g, " ");
  return /^[=+\-@]/.test(cleaned) ? `'${cleaned}` : cleaned;
}

function requiredCell(value: string, label: string): string {
  const cleaned = cleanCell(value);
  if (cleaned.trim().length === 0) {
    throw new UserError(`${label} ne doit pas être vide`);
  }
  return cleaned;
}

function requiredLine(value: string, label: string): string {
  const cleaned = value.replace(/[\n\r]/g, " ").trim();
  if (cleaned.length === 0) {
    throw new UserError(`${label} ne doit pas être vide`);
  }
  return cleaned;
}

function positiveInteger(value: number, label: string): number {
  if (!Number.isSafeInteger(value) || value < 1) {
    throw new UserError(`${label} doit être un entier positif`);
  }
  return value;
}

async function exists(path: string): Promise<boolean> {
  try {
    await access(path);
    return true;
  } catch (error) {
    if (errorCode(error) === "ENOENT") {
      return false;
    }
    throw error;
  }
}

async function atomicWrite(path: string, contents: string): Promise<void> {
  const temporary = join(
    dirname(path),
    `.${basename(path)}.${process.pid}.${randomUUID()}.tmp`
  );
  try {
    await writeFile(temporary, contents, { flag: "wx" });
    await rename(temporary, path);
  } finally {
    await rm(temporary, { force: true });
  }
}

async function writeIfMissing(path: string, contents: string): Promise<void> {
  if (!(await exists(path))) {
    await atomicWrite(path, contents);
  }
}

async function requiredFile(path: string): Promise<string> {
  try {
    return await readFile(path, "utf8");
  } catch (error) {
    if (errorCode(error) === "ENOENT") {
      throw new UserError(
        `le magasin n'est pas initialise dans ${dirname(path)}; lancer orch init`
      );
    }
    throw error;
  }
}

async function firstLineOf(path: string): Promise<string | null> {
  try {
    return (await readFile(path, "utf8")).replace(/\r/g, "").split("\n", 1)[0] ?? "";
  } catch (error) {
    if (errorCode(error) === "ENOENT") {
      return null;
    }
    throw error;
  }
}

async function requireInitializedStore(store: string): Promise<void> {
  const unitsHeader = await firstLineOf(join(store, "units.tsv"));
  const ledgerHeader = await firstLineOf(join(store, "ledger.tsv"));
  if ((unitsHeader !== UNIT_HEADER && unitsHeader !== LEGACY_UNIT_HEADER) || ledgerHeader !== LEDGER_HEADER) {
    throw new UserError(
      `le magasin n'est pas initialise dans ${store}; lancer orch init`
    );
  }
}

function holderIsDead(holder: string): boolean {
  const pid = Number.parseInt(holder, 10);
  if (!Number.isSafeInteger(pid) || pid <= 0 || String(pid) !== holder) {
    return false;
  }
  try {
    process.kill(pid, 0);
    return false;
  } catch (error) {
    return errorCode(error) === "ESRCH";
  }
}

function throwLockError(error: unknown): never {
  if (["ENOENT", "ENOTEMPTY", "EEXIST"].includes(errorCode(error) ?? "")) {
    throw new UserError("verrou de magasin modifié par un autre processus; réessayez");
  }
  throw error;
}

async function acquireDirectoryLock(
  path: string,
  options: OpenStoreOptions
) {
  const pid = String(process.pid);
  const generation = randomUUID();
  const marker = `owner.${pid}.${generation}`;
  const ownMarker = join(path, marker);
  const candidate = `${path}.tmp.${pid}.${generation}`;
  await mkdir(candidate);
  try {
    await writeFile(join(candidate, marker), "", { flag: "wx" });
    try {
      // Le répertoire publié contient déjà son propriétaire ; un verrou actif
      // non vide ne peut pas être remplacé par ce renommage.
      await rename(candidate, path);
    } catch (error) {
      if (!LOCK_CONFLICT_CODES.has(errorCode(error) ?? "")) {
        throw error;
      }
      const info = await lstat(path).catch(throwLockError);
      if (info.isSymbolicLink()) {
        throw new UserError("verrou de magasin invalide : lien symbolique interdit");
      }
      if (!info.isDirectory()) throw error;
      const entries = await readdir(path, { withFileTypes: true }).catch(throwLockError);
      const owner = entries[0];
      const match = owner && /^owner\.([1-9]\d*)\.[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.exec(owner.name);
      if (entries.length === 0) {
        await rmdir(path).catch(throwLockError);
        await rename(candidate, path).catch(throwLockError);
      } else if (entries.length !== 1 || !owner?.isFile() || !match || !Number.isSafeInteger(Number(match[1]))) {
        throw new UserError("verrou de magasin invalide : propriétaire indéterminé");
      } else {
        const holder = match[1];
        if (holderIsDead(holder)) options.onStaleLock?.(holder);
        else if (options.force) options.onLockStolen?.(holder);
        else throw new UserError(`verrou de magasin detenu par le pid ${holder}`);
        await rm(candidate, { recursive: true });
        // Seule la génération observée est remplacée : un repreneur retardé
        // ne peut pas déplacer le marqueur d'un nouveau propriétaire.
        await rename(join(path, owner.name), ownMarker).catch(throwLockError);
      }
    }
  } finally {
    await rm(candidate, { recursive: true, force: true });
  }

  return {
    assertOwned: async (): Promise<void> => {
      try {
        if ((await lstat(ownMarker)).isFile()) return;
      } catch (error) {
        if (!["ENOENT", "ENOTDIR"].includes(errorCode(error) ?? "")) throw error;
      }
      throw new UserError("verrou de magasin perdu; ouvrir un nouveau handle avant de modifier le magasin");
    },
    release: async (): Promise<void> => {
      try {
        await unlink(ownMarker);
      } catch (error) {
        if (errorCode(error) === "ENOENT") return;
        throw error;
      }
      try {
        await rmdir(path);
      } catch (error) {
        // Un successeur peut publier son répertoire après le retrait du marqueur.
        if (!["ENOENT", "ENOTEMPTY", "EEXIST"].includes(errorCode(error) ?? "")) {
          throw error;
        }
      }
    },
  };
}

async function acquireLock(
  store: string,
  options: OpenStoreOptions
): ReturnType<typeof acquireDirectoryLock> {
  const path = join(store, LOCK_FILE);
  try {
    return await acquireDirectoryLock(path, options);
  } catch (error) {
    if (!LOCK_CONFLICT_CODES.has(errorCode(error) ?? "") || !(await lstat(path).catch(throwLockError)).isFile()) {
      throw error;
    }
  }

  // Les anciens fichiers PID sont migrés sous le même protocole de verrouillage,
  // y compris lorsque le processus de migration précédent est mort.
  const migrationLock = await acquireDirectoryLock(`${path}.migration`, {});
  try {
    let info: Stats | undefined;
    try {
      info = await lstat(path);
    } catch (error) {
      if (errorCode(error) !== "ENOENT") throw error;
    }
    if (info?.isFile()) {
      const holder = (await readFile(path, "utf8")).trim() || "unknown";
      if (holderIsDead(holder)) options.onStaleLock?.(holder);
      else if (options.force) options.onLockStolen?.(holder);
      else throw new UserError(`verrou de magasin detenu par le pid ${holder}`);
      await unlink(path);
    }
    return await acquireDirectoryLock(path, options);
  } finally {
    await migrationLock.release();
  }
}

async function readTsv(
  path: string,
  header: string,
  width: number
): Promise<readonly (readonly string[])[]> {
  const lines = (await requiredFile(path)).replace(/\r/g, "").split("\n");
  if (lines.shift() !== header) {
    throw new UserError(`${basename(path)} a un en-tete invalide`);
  }
  return lines
    .filter((value) => value.length > 0)
    .map((value) => {
      const cells = value.split("\t");
      if (cells.length !== width) {
        throw new UserError(`${basename(path)} contient une ligne mal formee`);
      }
      return cells;
    });
}

async function writeTsv(
  path: string,
  header: string,
  rows: readonly (readonly string[])[]
): Promise<void> {
  const body = rows.map((row) => row.map(cleanCell).join("\t")).join("\n");
  await atomicWrite(path, `${header}\n${body}${body.length > 0 ? "\n" : ""}`);
}

async function readUnits(store: string): Promise<readonly Unit[]> {
  const header = await firstLineOf(join(store, "units.tsv"));
  const legacy = header === LEGACY_UNIT_HEADER;
  return (await readTsv(join(store, "units.tsv"), legacy ? LEGACY_UNIT_HEADER : UNIT_HEADER, legacy ? 7 : 8)).map(
    (row) => ({
      id: row[0] ?? "",
      track: row[1] ?? "",
      state: row[2] ?? "",
      branch: row[3] ?? "",
      pr: row[4] ?? "",
      sha: row[5] ?? "",
      brief: row[6] ?? "",
      ...(row[7] ? { owner: row[7] } : {}),
    })
  );
}

function unitCells(unit: Unit): readonly string[] {
  return [
    unit.id,
    unit.track,
    unit.state,
    unit.branch,
    unit.pr,
    unit.sha,
    unit.brief,
    unit.owner ?? "",
  ];
}

async function saveUnits(store: string, rows: readonly Unit[]): Promise<void> {
  await writeTsv(
    join(store, "units.tsv"),
    rows.some(row => row.owner) ? UNIT_HEADER : LEGACY_UNIT_HEADER,
    rows.map(row => rows.some(unit => unit.owner) ? unitCells(row) : unitCells(row).slice(0, 7))
  );
}

async function readLedger(store: string): Promise<readonly LedgerEntry[]> {
  return (await readTsv(join(store, "ledger.tsv"), LEDGER_HEADER, 6)).map(
    (row) => {
      const rawVerdict = row[2] ?? "";
      const verdict = verdictOrNull(rawVerdict);
      if (verdict === null) {
        throw new UserError(`ledger.tsv contient le verdict invalide ${rawVerdict}`);
      }
      return {
        pr: row[0] ?? "",
        sha: row[1] ?? "",
        verdict,
        evidence: row[3] ?? "",
        verifier: row[4] ?? "",
        ts: row[5] ?? "",
      };
    }
  );
}

function ledgerCells(row: LedgerEntry): readonly string[] {
  return [
    row.pr,
    row.sha,
    row.verdict,
    row.evidence,
    row.verifier,
    row.ts,
  ];
}

async function saveLedger(
  store: string,
  rows: readonly LedgerEntry[]
): Promise<void> {
  await writeTsv(
    join(store, "ledger.tsv"),
    LEDGER_HEADER,
    rows.map(ledgerCells)
  );
}

function pointerCells(pointer: InboxPointer): readonly string[] {
  return [
    pointer.ts,
    pointer.agent,
    pointer.unit,
    pointer.status,
    pointer.report,
  ];
}

async function pointerFileNames(
  directory: string
): Promise<readonly string[]> {
  let entries: Dirent[];
  try {
    entries = await readdir(directory, { withFileTypes: true });
  } catch (error) {
    if (errorCode(error) === "ENOENT") {
      throw new UserError(
        `le magasin n'est pas initialise dans ${dirname(directory)}; lancer orch init`
      );
    }
    throw error;
  }
  return entries
    .filter((entry) => entry.isFile() && entry.name.endsWith(".tsv"))
    .map((entry) => entry.name)
    .sort((left, right) => left.localeCompare(right));
}

async function parsePointerFile(
  directory: string,
  name: string
): Promise<InboxPointer> {
  const raw = (await readFile(join(directory, name), "utf8")).replace(
    /\r?\n$/,
    ""
  );
  const row = raw.split("\t");
  if (/[\r\n]/.test(raw) || row.length !== 5) {
    throw new UserError(`le pointeur de boite de reception ${name} est mal forme`);
  }
  return {
    ts: row[0] ?? "",
    agent: row[1] ?? "",
    unit: row[2] ?? "",
    status: row[3] ?? "",
    report: row[4] ?? "",
  };
}

async function readPointers(
  directory: string
): Promise<readonly InboxPointer[]> {
  const names = await pointerFileNames(directory);
  const result: InboxPointer[] = [];
  for (const name of names) {
    result.push(await parsePointerFile(directory, name));
  }
  return result;
}

function renderGates(rows: readonly Gate[]): string {
  if (rows.length === 0) {
    return "";
  }
  const blocks = rows.map((gate) => {
    const answer =
      gate.kind === "resolved" ? `\n- Reponse: ${gate.answer}` : "";
    return `## ${gate.id}

- Statut: ${gate.kind}
- Question: ${gate.question}
- Options: ${gate.options}
- Defaut: ${gate.defaultAnswer}${answer}`;
  });
  return `# Barrieres\n\n${blocks.join("\n\n")}\n`;
}

async function readGates(store: string): Promise<readonly Gate[]> {
  const raw = (await requiredFile(join(store, "gates.md")))
    .replace(/\r/g, "")
    .trim();
  if (raw.length === 0) {
    return [];
  }
  const prefix = raw.startsWith("# Gates\n\n## ")
    ? "# Gates\n\n## "
    : "# Barrieres\n\n## ";
  if (!raw.startsWith(prefix)) {
    throw new UserError("gates.md a un titre invalide");
  }
  const result: Gate[] = [];
  for (const block of raw.slice(prefix.length).split("\n\n## ")) {
    const lines = block.split("\n").filter((value) => value.length > 0);
    const id = lines.shift() ?? "";
    const fields = new Map<string, string>();
    for (const value of lines) {
      const match = /^- ([^:]+): (.*)$/.exec(value);
      if (match === null) {
        throw new UserError(`gates.md contient une barrière mal formée ${id}`);
      }
      fields.set(match[1] ?? "", match[2] ?? "");
    }
    const status = fields.get("Status") ?? fields.get("Statut");
    const question = fields.get("Question");
    const options = fields.get("Options");
    const defaultAnswer = fields.get("Default") ?? fields.get("Defaut");
    if (
      id.length === 0 ||
      question === undefined ||
      options === undefined ||
      defaultAnswer === undefined
    ) {
      throw new UserError(`gates.md contient une barrière mal formée ${id}`);
    }
    if (status === "open") {
      result.push({ kind: "open", id, question, options, defaultAnswer });
    } else if (status === "resolved" && (fields.has("Answer") || fields.has("Reponse"))) {
      result.push({
        kind: "resolved",
        id,
        question,
        options,
        defaultAnswer,
        answer: fields.get("Answer") ?? fields.get("Reponse") ?? "",
      });
    } else {
      throw new UserError(`gates.md contient le statut invalide ${status ?? ""}`);
    }
  }
  if (new Set(result.map((gate) => gate.id)).size !== result.length) {
    throw new UserError("gates.md contient des ids de barrière en double");
  }
  return result;
}

function parseFrontier(raw: string): Frontier {
  let value: unknown;
  try {
    value = JSON.parse(raw);
  } catch {
    throw new UserError("frontier.json n'est pas un JSON valide");
  }
  if (!isRecord(value)) {
    throw new UserError("frontier.json doit contenir un objet");
  }
  if (Object.keys(value).length === 0) {
    return { generation: 0, prs: [], lowestUnmerged: null, closedGap: null };
  }
  if (
    typeof value.generation !== "number" ||
    !Number.isSafeInteger(value.generation) ||
    value.generation < 0 ||
    !isUnknownArray(value.prs) ||
    !(
      value.lowestUnmerged === null ||
      (typeof value.lowestUnmerged === "number" &&
        Number.isSafeInteger(value.lowestUnmerged))
    ) ||
    !(
      value.closedGap === undefined ||
      value.closedGap === null ||
      (typeof value.closedGap === "number" &&
        Number.isSafeInteger(value.closedGap))
    )
  ) {
    throw new UserError("frontier.json a une forme invalide");
  }
  const prs: FrontierPr[] = [];
  for (const row of value.prs) {
    const state = isRecord(row)
      ? frontierPrStateOrNull(row.state)
      : null;
    if (
      !isRecord(row) ||
      typeof row.pr !== "number" ||
      !Number.isSafeInteger(row.pr) ||
      row.pr < 1 ||
      typeof row.branches !== "string" ||
      row.branches.length === 0 ||
      typeof row.sha !== "string" ||
      state === null
    ) {
      throw new UserError("frontier.json contient une ligne de PR invalide");
    }
    prs.push({
      pr: row.pr,
      branches: row.branches,
      sha: row.sha,
      state,
    });
  }
  return {
    generation: value.generation,
    prs,
    lowestUnmerged: value.lowestUnmerged,
    closedGap: value.closedGap ?? null,
  };
}

async function readFrontier(store: string): Promise<Frontier> {
  return parseFrontier(await requiredFile(join(store, "frontier.json")));
}

async function readStanding(
  store: string
): Promise<readonly StandingLine[]> {
  const raw = (await requiredFile(join(store, "preferences.md"))).replace(
    /\r/g,
    ""
  );
  if (raw.trim().length === 0) {
    return [];
  }
  const result: StandingLine[] = [];
  for (const value of raw.split("\n").filter((item) => item.length > 0)) {
    const match = /^([1-9]\d*)\. (.+)$/.exec(value);
    const number = Number(match?.[1] ?? 0);
    if (match === null || number !== result.length + 1) {
      throw new UserError("preferences.md a une numérotation mal formée");
    }
    result.push({ number, line: match[2] ?? "" });
  }
  return result;
}

function countValues(values: readonly string[]): Counts {
  const result: Record<string, number> = {};
  for (const value of values) {
    result[value] = (result[value] ?? 0) + 1;
  }
  return Object.fromEntries(
    Object.entries(result).sort(([left], [right]) =>
      left.localeCompare(right)
    )
  );
}

function summarize(
  unitRows: readonly Unit[],
  ledgerRows: readonly LedgerEntry[],
  currentFrontier: Frontier,
  gateRows: readonly Gate[]
): StatusSummary {
  return {
    unitStates: countValues(unitRows.map((unit) => unit.state)),
    ledgerVerdicts: countValues(ledgerRows.map((row) => row.verdict)),
    frontierGeneration: currentFrontier.generation,
    openGateIds: gateRows
      .filter((gate): gate is OpenGate => gate.kind === "open")
      .map((gate) => gate.id)
      .sort(),
  };
}

function countRecord(value: unknown): Record<string, number> | null {
  if (!isRecord(value)) {
    return null;
  }
  const result: Record<string, number> = {};
  for (const [name, count] of Object.entries(value)) {
    if (
      typeof count !== "number" ||
      !Number.isSafeInteger(count) ||
      count < 0
    ) {
      return null;
    }
    result[name] = count;
  }
  return result;
}

function previousSummary(raw: string): StatusSummary | null {
  const match = /<!-- orch-summary (.+) -->/.exec(raw);
  if (match === null) {
    return null;
  }
  let value: unknown;
  try {
    value = JSON.parse(match[1] ?? "");
  } catch {
    return null;
  }
  if (
    !isRecord(value) ||
    typeof value.frontierGeneration !== "number" ||
    !isUnknownArray(value.openGateIds)
  ) {
    return null;
  }
  const unitStates = countRecord(value.unitStates);
  const ledgerVerdicts = countRecord(value.ledgerVerdicts);
  const openGateIds = value.openGateIds.filter(
    (item): item is string => typeof item === "string"
  );
  if (
    unitStates === null ||
    ledgerVerdicts === null ||
    openGateIds.length !== value.openGateIds.length
  ) {
    return null;
  }
  return {
    unitStates,
    ledgerVerdicts,
    frontierGeneration: value.frontierGeneration,
    openGateIds,
  };
}

function changed(before: StatusSummary | null, after: StatusSummary): string {
  if (before === null) {
    return "premier rendu";
  }
  const result: string[] = [];
  const groups: readonly {
    readonly label: string;
    readonly oldCounts: Counts;
    readonly newCounts: Counts;
  }[] = [
    {
      label: "unités",
      oldCounts: before.unitStates,
      newCounts: after.unitStates,
    },
    {
      label: "registre",
      oldCounts: before.ledgerVerdicts,
      newCounts: after.ledgerVerdicts,
    },
  ];
  for (const { label, oldCounts, newCounts } of groups) {
    const names = [
      ...new Set([...Object.keys(oldCounts), ...Object.keys(newCounts)]),
    ].sort();
    for (const name of names) {
      const oldCount = oldCounts[name] ?? 0;
      const newCount = newCounts[name] ?? 0;
      if (oldCount !== newCount) {
        result.push(`${label} ${name} ${oldCount}->${newCount}`);
      }
    }
  }
  if (before.frontierGeneration !== after.frontierGeneration) {
    result.push(
      `generation de frontiere ${before.frontierGeneration}->${after.frontierGeneration}`
    );
  }
  if (before.openGateIds.join("\0") !== after.openGateIds.join("\0")) {
    result.push(
      `barrières ouvertes ${before.openGateIds.length}->${after.openGateIds.length}`
    );
  }
  return result.length === 0 ? "aucun changement derive" : result.join("; ");
}

function markdown(value: string): string {
  return value.replace(/\\/g, "\\\\").replace(/\|/g, "\\|");
}

function table(
  headers: readonly string[],
  rows: readonly (readonly string[])[]
): string {
  if (rows.length === 0) {
    return "(aucun)";
  }
  return [
    `| ${headers.join(" | ")} |`,
    `| ${headers.map(() => "---").join(" | ")} |`,
    ...rows.map((row) => `| ${row.map(markdown).join(" | ")} |`),
  ].join("\n");
}

function statusMarkdown(
  unitRows: readonly Unit[],
  ledgerRows: readonly LedgerEntry[],
  currentFrontier: Frontier,
  gateRows: readonly Gate[],
  currentSummary: StatusSummary
): string {
  return `# Statut d'orchestration

Genere: ${new Date().toISOString()}

## Unites

Etats: ${countLine(currentSummary.unitStates)}

${table(
  ["ID", "Piste", "Etat", "Branche", "PR", "SHA", "Brief", "Owner"],
  unitRows.map(unitCells)
)}

## Registre de verification

Verdicts: ${countLine(currentSummary.ledgerVerdicts)}

${table(
  ["PR", "SHA", "Verdict", "Preuve", "Verificateur", "Horodatage"],
  ledgerRows.map(ledgerCells)
)}

## Frontiere

Generation: ${currentFrontier.generation}
Plus basse non fusionnee: ${currentFrontier.lowestUnmerged ?? "aucune"}
Trou ferme non fusionne: ${currentFrontier.closedGap ?? "aucun"}

${table(
  ["Branche", "PR", "SHA", "Etat"],
  currentFrontier.prs.map((row) => [
    row.branches,
    String(row.pr),
    row.sha,
    row.state,
  ])
)}

## Barrieres

${table(
  ["ID", "Statut", "Question", "Options", "Defaut", "Reponse"],
  gateRows.map((gate) => [
    gate.id,
    gate.kind,
    gate.question,
    gate.options,
    gate.defaultAnswer,
    gate.kind === "resolved" ? gate.answer : "",
  ])
)}

<!-- orch-summary ${JSON.stringify(currentSummary)} -->
`;
}

function countLine(value: Counts): string {
  const entries = Object.entries(value);
  return entries.length === 0
    ? "aucun"
    : entries.map(([name, count]) => `${name}=${count}`).join(", ");
}

interface GitHubPullRequest {
  readonly pr: number;
  readonly branches: string;
  readonly base: string;
  readonly sha: string;
  readonly state: FrontierPrState;
}

function commandOutput({
  command,
  args,
  repo,
  label,
}: {
  command: string;
  args: readonly string[];
  repo: string;
  label: string;
}): string {
  let raw: string;
  try {
    raw = execFileSync(command, args, {
      cwd: repo,
      encoding: "utf8",
      env: process.env,
      stdio: ["ignore", "pipe", "pipe"],
    });
  } catch (error) {
    throw new UserError(`${label} a échoué: ${errorMessage(error)}`);
  }
  return raw.trim();
}

function parseCommandJson(raw: string, label: string): unknown {
  try {
    return JSON.parse(raw);
  } catch (error) {
    throw new UserError(`${label} a renvoye un JSON invalide: ${errorMessage(error)}`);
  }
}

function requiredString(value: unknown, label: string): string {
  if (typeof value !== "string" || value.length === 0) {
    throw new UserError(`la sortie de gh contient ${label} invalide`);
  }
  return value;
}

function githubPullRequests(repo: string): readonly GitHubPullRequest[] {
  const value = parseCommandJson(
    commandOutput({
      command: "gh",
      args: [
        "pr",
        "list",
        "--state",
        "all",
        "--limit",
        "1000",
        "--json",
        "number,state,headRefName,baseRefName,headRefOid",
      ],
      repo,
      label: "gh pr list",
    }),
    "gh pr list"
  );
  if (!isUnknownArray(value)) {
    throw new UserError("la sortie de gh pr list doit être un tableau");
  }
  // ponytail: échouer fermé à la limite de gh; paginer si un dépôt dépasse 1 000 PR.
  if (value.length >= 1000) {
    throw new UserError(
      "gh pr list a renvoyé 1000 PR; l’historique de pile peut être incomplet"
    );
  }
  return value.map((item, index) => {
    if (!isRecord(item)) {
      throw new UserError(`la ligne ${index + 1} de gh pr list est invalide`);
    }
    const pr = item.number;
    const state = frontierPrStateOrNull(item.state);
    const sha = requiredString(item.headRefOid, "headRefOid");
    if (!Number.isSafeInteger(pr) || Number(pr) <= 0 || state === null) {
      throw new UserError(`la ligne ${index + 1} de gh pr list est invalide`);
    }
    if (!/^[0-9a-f]{40,64}$/i.test(sha)) {
      throw new UserError(`la ligne ${index + 1} de gh pr list a un SHA de tete invalide`);
    }
    return {
      pr: Number(pr),
      branches: requiredString(item.headRefName, "headRefName"),
      base: requiredString(item.baseRefName, "baseRefName"),
      sha,
      state,
    };
  });
}

function currentBranch(repo: string): string {
  return commandOutput({
    command: "git",
    args: ["symbolic-ref", "--quiet", "--short", "HEAD"],
    repo,
    label: "recherche de la branche courante git",
  });
}

function defaultBranch(repo: string): string {
  const value = parseCommandJson(
    commandOutput({
      command: "gh",
      args: ["repo", "view", "--json", "defaultBranchRef"],
      repo,
      label: "gh repo view",
    }),
    "gh repo view"
  );
  if (!isRecord(value) || !isRecord(value.defaultBranchRef)) {
    throw new UserError("la sortie de gh repo view ne contient pas de branche par defaut");
  }
  return requiredString(value.defaultBranchRef.name, "branche par defaut");
}

function livePreferred(
  rows: readonly GitHubPullRequest[]
): readonly GitHubPullRequest[] {
  const live = rows.filter((row) => row.state !== "CLOSED");
  return live.length > 0 ? live : rows;
}

function oneByHead(
  rows: readonly GitHubPullRequest[],
  branch: string
): GitHubPullRequest | undefined {
  const matches = livePreferred(
    rows.filter((row) => row.branches === branch)
  );
  if (matches.length > 1) {
    throw new UserError(
      `GitHub a renvoye plusieurs PR pour la branche de tete ${branch}: ${matches
        .map((row) => row.pr)
        .sort((a, b) => a - b)
        .join(",")}`
    );
  }
  return matches[0];
}

function verifyLocalHead(repo: string, row: GitHubPullRequest): FrontierPr {
  let local: string;
  try {
    local = commandOutput({
      command: "git",
      args: ["rev-parse", "--verify", `refs/heads/${row.branches}`],
      repo,
      label: `git branch ${row.branches}`,
    });
  } catch {
    throw new UserError(`la branche de pile GitHub ${row.branches} manque localement`);
  }
  if (!/^[0-9a-f]{40,64}$/i.test(local)) {
    throw new UserError(`git branch ${row.branches} a renvoye un SHA invalide`);
  }
  if (local.toLowerCase() !== row.sha.toLowerCase()) {
    throw new UserError(
      `SHA de tete non concordant pour la PR #${row.pr} sur la branche ${row.branches}: GitHub ${row.sha}; local ${local}`
    );
  }
  return {
    pr: row.pr,
    branches: row.branches,
    sha: row.sha,
    state: row.state,
  };
}

function resolveFrontier(repo: string): readonly FrontierPr[] {
  const rows = githubPullRequests(repo);
  const branch = currentBranch(repo);
  const trunk = defaultBranch(repo);
  const start = oneByHead(rows, branch);
  if (start === undefined) {
    throw new UserError(`GitHub n'a pas de PR pour la branche courante ${branch}`);
  }

  const down: GitHubPullRequest[] = [];
  const seen = new Set([start.branches]);
  let cursor = start;
  while (cursor.base !== trunk) {
    const parent = oneByHead(rows, cursor.base);
    if (parent === undefined) {
      throw new UserError(
        `la pile GitHub n'a pas de PR pour la branche de base ${cursor.base}`
      );
    }
    if (seen.has(parent.branches)) {
      throw new UserError(
        `la pile de PR GitHub contient un cycle a ${parent.branches}`
      );
    }
    seen.add(parent.branches);
    down.push(parent);
    cursor = parent;
  }

  const up: GitHubPullRequest[] = [];
  cursor = start;
  while (true) {
    const children = livePreferred(
      rows.filter((row) => row.base === cursor.branches)
    );
    if (children.length > 1) {
      throw new UserError(
        `la pile de PR GitHub bifurque à ${cursor.branches}: ${children
          .map((row) => row.pr)
          .sort((a, b) => a - b)
          .join(",")}`
      );
    }
    const child = children[0];
    if (child === undefined) {
      break;
    }
    if (seen.has(child.branches)) {
      throw new UserError(
        `la pile de PR GitHub contient un cycle a ${child.branches}`
      );
    }
    seen.add(child.branches);
    up.push(child);
    cursor = child;
  }

  return [...down.reverse(), start, ...up].map((row) =>
    verifyLocalHead(repo, row)
  );
}

function validateFrontierPin({
  actual,
  expected,
}: {
  actual: readonly number[];
  expected: readonly number[];
}): void {
  if (
    actual.length === expected.length &&
    actual.every((pr, index) => pr === expected[index])
  ) {
    return;
  }
  const actualSet = new Set(actual);
  const expectedSet = new Set(expected);
  const missing = expected.filter((pr) => !actualSet.has(pr));
  const extra = actual.filter((pr) => !expectedSet.has(pr));
  const drift: string[] = [];
  if (missing.length > 0) {
    drift.push(`manquantes dans GitHub: ${missing.join(",")}`);
  }
  if (extra.length > 0) {
    drift.push(`en trop dans GitHub: ${extra.join(",")}`);
  }
  if (missing.length === 0 && extra.length === 0) {
    drift.push(
      `ordre différent: attendu ${expected.join(",")}; GitHub ${actual.join(",")}`
    );
  }
  throw new UserError(`l'ancrage de frontiere ne correspond pas: ${drift.join("; ")}`);
}

interface HandoffReceipt {
  readonly definition: HorizonDefinition;
  readonly committed: boolean;
}

async function handoffReceipt(store: string): Promise<HandoffReceipt> {
  const raw: unknown = JSON.parse(await requiredFile(join(store, "horizon.json")));
  if (!isRecord(raw) || !isRecord(raw.definition) || typeof raw.definition.spec !== "string" || typeof raw.committed !== "boolean") {
    throw new UserError("reçu Horizon invalide");
  }
  const current = await loadHorizon(raw.definition.spec);
  if (JSON.stringify(raw.definition) !== JSON.stringify(current)) {
    const before = isRecord(raw.definition.sources) ? raw.definition.sources : {};
    const paths = new Set([...Object.keys(before), ...Object.keys(current.sources)]);
    const changed = [...paths].filter(path => before[path] !== current.sources[path]);
    throw new UserError(`dérive Horizon; aucune définition, propriété ou preuve écrasée: ${changed.join(", ") || "métadonnées du reçu"}`);
  }
  return { definition: current, committed: raw.committed };
}

function briefPath(store: string, id: string): string { return join(store, "briefs", `${id}.md`); }

async function checkHandoffFiles(store: string, definition: HorizonDefinition, complete: boolean): Promise<readonly Unit[]> {
  const rows = await readUnits(store);
  const imported = rows.filter(row => definition.units.some(unit => unit.id === row.id));
  if (imported.length !== 0 && imported.length !== definition.units.length) throw new UserError("handoff partiel dans units.tsv; réconcilier sans recréer les unités manquantes");
  if (new Set(imported.map(row => row.id)).size !== imported.length) throw new UserError("ids dupliqués dans units.tsv");
  if (complete && imported.length !== definition.units.length) throw new UserError("handoff incomplet; reprendre import avant dispatch");
  for (const unit of definition.units) {
    const path = briefPath(store, unit.id);
    if (await exists(path)) {
      if (await readFile(path, "utf8") !== horizonBrief(definition, unit)) throw new UserError(`dérive du brief ${path}; écrasement interdit`);
    } else if (complete) throw new UserError(`brief manquant: ${path}`);
    const row = imported.find(row => row.id === unit.id);
    if (row && (row.brief !== path || row.track !== "horizon")) throw new UserError(`collision d'unité Horizon: ${unit.id}`);
  }
  return rows;
}

function localHead(repo: string, branch: string): string {
  if (!branch) throw new UserError("branche locale manquante");
  return commandOutput({command: "git", args: ["rev-parse", "--verify", `refs/heads/${branch}`], repo: resolve(repo), label: `head local ${branch}`});
}

async function readyHandoff(store: string, repo: string): Promise<ReadyUnits> {
  const receipt = await handoffReceipt(store);
  if (!receipt.committed) throw new UserError("handoff incomplet; reprendre import avant dispatch");
  const rows = await checkHandoffFiles(store, receipt.definition, true);
  const ledger = await readLedger(store);
  const verified = async (id: string): Promise<boolean> => {
    const row = rows.find(row => row.id === id);
    if (!row || row.state !== "done" || !row.owner || !row.sha || !row.pr) return false;
    try { if (localHead(repo, row.branch) !== row.sha) return false; } catch { return false; }
    const proof = ledger.find(entry => entry.pr === row.pr && entry.sha === row.sha);
    if (!proof || !["unit-test-verified", "live-ui-verified"].includes(proof.verdict) || !proof.verifier || proof.verifier === row.owner) return false;
    try { return (await readFile(resolve(repo, proof.evidence), "utf8")).trim().length > 0; } catch { return false; }
  };
  const ready: string[] = [];
  const blocked: { id: string; reason: string }[] = [];
  for (const unit of receipt.definition.units) {
    const row = rows.find(row => row.id === unit.id);
    let reason = row?.state !== "pending" || row.owner ? `état ${row?.state}; owner ${row?.owner || "aucun"}` : "";
    for (const blocker of unit.blocked_by) {
      if (!reason && !(await verified(blocker))) reason = `bloqueur ${blocker} sans preuve de comportement au head local courant`;
    }
    for (const other of receipt.definition.units) {
      const active = rows.find(row => row.id === other.id);
      if (!reason && other.id !== unit.id && active?.owner && active.state !== "done" && overlappingScopes(unit, other)) reason = `écritures partagées avec ${other.id}`;
    }
    if (reason) blocked.push({id: unit.id, reason}); else ready.push(unit.id);
  }
  return {ready, blocked};
}

export function openStore(
  directory: string,
  options: OpenStoreOptions = {}
): Store {
  const store = resolve(directory);
  let closed = false;
  let heldLock: Awaited<ReturnType<typeof acquireLock>> | null = null;
  let lockRequest: Promise<void> | null = null;

  const ensureOpen = (): void => {
    if (closed) {
      throw new UserError("le magasin est ferme");
    }
  };

  const ensureLock = async (): Promise<void> => {
    ensureOpen();
    if (heldLock !== null) {
      await heldLock.assertOwned();
      return;
    }
    if (lockRequest === null) {
      lockRequest = acquireLock(store, options).then((lock) => {
        heldLock = lock;
      });
    }
    try {
      await lockRequest;
    } catch (error) {
      lockRequest = null;
      throw error;
    }
  };

  const beginWrite = async (): Promise<void> => {
    ensureOpen();
    await requireInitializedStore(store);
    await ensureLock();
  };

  const api: Store = {
    handoff: {
      import: async (spec) => {
        await beginWrite();
        const definition = await loadHorizon(spec);
        const receiptPath = join(store, "horizon.json");
        const previous = await exists(receiptPath) ? await handoffReceipt(store) : null;
        if (previous && JSON.stringify(previous.definition) !== JSON.stringify(definition)) throw new UserError("dérive Horizon: ce magasin appartient déjà à une autre spec");
        const rows = await checkHandoffFiles(store, definition, previous?.committed ?? false);
        const imported = rows.filter(row => definition.units.some(unit => unit.id === row.id));
        if (!previous && imported.length) throw new UserError("collision: unités déjà présentes sans provenance Horizon");
        // Pin before writing briefs. Claims require the committed receipt, so a
        // crash can resume preparation without confusing it with execution.
        if (!previous) await atomicWrite(receiptPath, `${JSON.stringify({definition, committed: false}, null, 2)}\n`);
        await mkdir(join(store, "briefs"), {recursive: true});
        for (const unit of definition.units) await writeIfMissing(briefPath(store, unit.id), horizonBrief(definition, unit));
        const added = imported.length ? [] : definition.units.map(unit => unit.id);
        if (added.length) await saveUnits(store, [...rows, ...definition.units.map(unit => ({id: unit.id, track: "horizon", state: "pending", branch: "", pr: "", sha: "", brief: briefPath(store, unit.id)}))]);
        await atomicWrite(receiptPath, `${JSON.stringify({definition, committed: true}, null, 2)}\n`);
        return {added, reused: imported.map(row => row.id), digest: definition.digest};
      },
      ready: async (repo) => {
        await beginWrite();
        return readyHandoff(store, repo);
      },
      claim: async (params) => {
        await beginWrite();
        const owner = requiredCell(params.owner, "owner");
        const branch = requiredCell(params.branch, "branch");
        if (!(await readyHandoff(store, params.repo)).ready.includes(params.id)) throw new UserError(`unité ${params.id} non dispatchable; aucune nouvelle revendication`);
        const rows = [...await readUnits(store)];
        if (rows.some(row => row.branch === branch)) throw new UserError(`branche déjà attribuée: ${branch}`);
        const {definition} = await handoffReceipt(store);
        const unit = definition.units.find(unit => unit.id === params.id);
        for (const id of unit?.blocked_by ?? []) {
          const blocker = rows.find(row => row.id === id);
          try {
            commandOutput({command: "git", args: ["merge-base", "--is-ancestor", blocker?.sha ?? "", `refs/heads/${branch}`], repo: resolve(params.repo), label: `intégration de ${id}`});
          } catch { throw new UserError(`intégrer le head vérifié de ${id} dans ${branch} avant dispatch`); }
        }
        const index = rows.findIndex(row => row.id === params.id);
        const old = rows[index];
        if (!old) throw new NotFoundError(params.id);
        const row: Unit = {...old, state: "claimed", owner, branch, sha: localHead(params.repo, branch)};
        rows[index] = row;
        await saveUnits(store, rows);
        return row;
      },
    },
    units: {
      add: async (params) => {
        await beginWrite();
        const row: Unit = {
          id: requiredCell(params.id, "unit id"),
          track: requiredCell(params.track, "track"),
          state: "pending",
          branch: "",
          pr: "",
          sha: "",
          brief:
            params.brief === undefined
              ? ""
              : requiredCell(params.brief, "brief"),
        };
        const rows = [...(await readUnits(store))];
        if (rows.some((unit) => unit.id === row.id)) {
          throw new UserError(`l’unité ${row.id} existe déjà`);
        }
        rows.push(row);
        await saveUnits(store, rows);
        return row;
      },
      set: async (params) => {
        await beginWrite();
        const id = requiredCell(params.id, "unit id");
        const state = requiredCell(params.state, "state");
        const rows = [...(await readUnits(store))];
        const index = rows.findIndex((unit) => unit.id === id);
        const old = rows[index];
        if (index < 0 || old === undefined) {
          throw new NotFoundError(`unité ${id} introuvable`);
        }
        if (await exists(join(store, "horizon.json"))) {
          const {definition} = await handoffReceipt(store);
          if (definition.units.some(unit => unit.id === id)) {
            if (old.state === "done" && state !== "done") throw new UserError("unité Horizon terminée; réouverture implicite interdite");
            if (!old.owner || state === "pending" || state === "claimed") throw new UserError("unité Horizon: utiliser handoff claim; réattribution interdite");
            if (!["working", "verifying", "done", "blocked"].includes(state)) throw new UserError("état Horizon invalide");
            if (params.branch !== undefined && params.branch !== old.branch) throw new UserError("branche Horizon attribuée; changement silencieux interdit");
          }
        }
        const row: Unit = {
          ...old,
          state,
          branch:
            params.branch === undefined
              ? old.branch
              : requiredCell(params.branch, "branch"),
          pr:
            params.pr === undefined
              ? old.pr
              : String(positiveInteger(params.pr, "PR")),
          sha:
            params.sha === undefined
              ? old.sha
              : requiredCell(params.sha, "SHA"),
        };
        rows[index] = row;
        await saveUnits(store, rows);
        return row;
      },
      get: async (id) => {
        ensureOpen();
        const cleanId = requiredCell(id, "unit id");
        const row = (await readUnits(store)).find(
          (unit) => unit.id === cleanId
        );
        if (row === undefined) {
          throw new NotFoundError(`unité ${cleanId} introuvable`);
        }
        return row;
      },
      list: async (params = {}) => {
        ensureOpen();
        const state =
          params.state === undefined
            ? undefined
            : requiredCell(params.state, "state");
        const track =
          params.track === undefined
            ? undefined
            : requiredCell(params.track, "track");
        return (await readUnits(store)).filter(
          (unit) =>
            (state === undefined || unit.state === state) &&
            (track === undefined || unit.track === track)
        );
      },
      counts: async () => {
        ensureOpen();
        return countValues(
          (await readUnits(store)).map((unit) => unit.state)
        );
      },
    },
    ledger: {
      record: async (params) => {
        await beginWrite();
        const verdict = parseVerdict(params.verdict);
        const row: LedgerEntry = {
          pr: String(positiveInteger(params.pr, "PR")),
          sha: requiredCell(params.sha, "SHA"),
          verdict,
          evidence: requiredCell(params.evidence, "evidence"),
          verifier:
            params.verifier === undefined
              ? ""
              : requiredCell(params.verifier, "verifier"),
          ts: new Date().toISOString(),
        };
        const rows = [...(await readLedger(store))];
        const index = rows.findIndex(
          (old) => old.pr === row.pr && old.sha === row.sha
        );
        if (index < 0) {
          rows.push(row);
        } else {
          rows[index] = row;
        }
        await saveLedger(store, rows);
        return row;
      },
      check: async (params) => {
        ensureOpen();
        const pr = String(positiveInteger(params.pr, "PR"));
        const sha = requiredCell(params.sha, "SHA");
        const row = (await readLedger(store)).find(
          (value) => value.pr === pr && value.sha === sha
        );
        if (row === undefined) {
          throw new NotFoundError("NOT-VERIFIED", {
            compact: "NOT-VERIFIED",
            json: { pr, sha, verdict: "NOT-VERIFIED" },
          });
        }
        return row;
      },
      summary: async () => {
        ensureOpen();
        return countValues(
          (await readLedger(store)).map((row) => row.verdict)
        );
      },
    },
    inbox: {
      push: async (params) => {
        ensureOpen();
        await requireInitializedStore(store);
        const pointer: InboxPointer = {
          ts: new Date().toISOString(),
          agent: requiredCell(params.agent, "agent"),
          unit: requiredCell(params.unit, "unit"),
          status: requiredCell(params.status, "status"),
          report:
            params.report === undefined
              ? ""
              : requiredCell(params.report, "report"),
        };
        const inbox = join(store, "inbox");
        if (!(await exists(inbox))) {
          throw new UserError(
            `le magasin n'est pas initialise dans ${store}; lancer orch init`
          );
        }
        const timestamp = pointer.ts.replace(/[:.]/g, "-");
        const filename = `${timestamp}-${process.pid}-${randomUUID()}.tsv`;
        const contents = `${pointerCells(pointer).map(cleanCell).join("\t")}\n`;
        await atomicWrite(join(inbox, filename), contents);
        return { pointer, filename };
      },
      drain: async () => {
        await beginWrite();
        const inbox = join(store, "inbox");
        const names = await pointerFileNames(inbox);
        const rows: InboxPointer[] = [];
        for (const name of names) {
          rows.push(await parsePointerFile(inbox, name));
        }
        for (const name of names) {
          await unlink(join(inbox, name));
        }
        return rows;
      },
      peek: async () => {
        ensureOpen();
        return readPointers(join(store, "inbox"));
      },
      count: async () => {
        ensureOpen();
        return (await readPointers(join(store, "inbox"))).length;
      },
    },
    gates: {
      park: async (params) => {
        await beginWrite();
        const gate: OpenGate = {
          kind: "open",
          id: requiredLine(params.id, "gate id"),
          question: requiredLine(params.question, "question"),
          options: requiredLine(params.options, "options"),
          defaultAnswer: requiredLine(
            params.defaultAnswer,
            "default"
          ),
        };
        const rows = [...(await readGates(store))];
        const index = rows.findIndex((old) => old.id === gate.id);
        if (index < 0) {
          rows.push(gate);
        } else {
          rows[index] = gate;
        }
        await atomicWrite(join(store, "gates.md"), renderGates(rows));
        return gate;
      },
      list: async () => {
        ensureOpen();
        return (await readGates(store)).filter(
          (gate): gate is OpenGate => gate.kind === "open"
        );
      },
      resolve: async (params) => {
        await beginWrite();
        const id = requiredLine(params.id, "gate id");
        const rows = [...(await readGates(store))];
        const index = rows.findIndex((gate) => gate.id === id);
        const old = rows[index];
        if (index < 0 || old === undefined) {
          throw new NotFoundError(`barrière ${id} introuvable`);
        }
        const gate: ResolvedGate = {
          kind: "resolved",
          id: old.id,
          question: old.question,
          options: old.options,
          defaultAnswer: old.defaultAnswer,
          answer: requiredLine(params.answer, "answer"),
        };
        rows[index] = gate;
        await atomicWrite(join(store, "gates.md"), renderGates(rows));
        return gate;
      },
    },
    frontier: {
      set: async (params) => {
        await beginWrite();
        const repo = resolve(requiredLine(params.repo, "repo directory"));
        const pin =
          params.prs === undefined
            ? undefined
            : params.prs.map((pr) => positiveInteger(pr, "PR"));
        if (pin !== undefined && new Set(pin).size !== pin.length) {
          throw new UserError("--prs ne doit pas contenir de doublons");
        }
        const old = await readFrontier(store);
        const prs = resolveFrontier(repo);
        if (pin !== undefined) {
          validateFrontierPin({
            actual: prs.map((row) => row.pr),
            expected: pin,
          });
        }
        const value: Frontier = {
          generation: old.generation + 1,
          prs,
          lowestUnmerged: prs.find((row) => row.state === "OPEN")?.pr ?? null,
          closedGap: prs.find((row) => row.state === "CLOSED")?.pr ?? null,
        };
        await atomicWrite(
          join(store, "frontier.json"),
          `${JSON.stringify(value, null, 2)}\n`
        );
        return value;
      },
      show: async () => {
        ensureOpen();
        return readFrontier(store);
      },
    },
    standing: {
      show: async () => {
        ensureOpen();
        return readStanding(store);
      },
      add: async (params) => {
        await beginWrite();
        const rows = [...(await readStanding(store))];
        const item: StandingLine = {
          number: rows.length + 1,
          line: requiredLine(params.line, "consigne permanente"),
        };
        rows.push(item);
        await atomicWrite(
          join(store, "preferences.md"),
          `${rows.map((row) => `${row.number}. ${row.line}`).join("\n")}\n`
        );
        return item;
      },
    },
    status: {
      render: async () => {
        await beginWrite();
        const unitRows = await readUnits(store);
        const ledgerRows = await readLedger(store);
        const currentFrontier = await readFrontier(store);
        const gateRows = await readGates(store);
        const currentSummary = summarize(
          unitRows,
          ledgerRows,
          currentFrontier,
          gateRows
        );
        const path = join(store, "status.md");
        const before = (await exists(path))
          ? previousSummary(await readFile(path, "utf8"))
          : null;
        const change = changed(before, currentSummary);
        await atomicWrite(
          path,
          statusMarkdown(
            unitRows,
            ledgerRows,
            currentFrontier,
            gateRows,
            currentSummary
          )
        );
        return {
          units: unitRows,
          ledger: ledgerRows,
          frontier: currentFrontier,
          gates: gateRows,
          summary: currentSummary,
          changed: change,
        };
      },
    },
    init: async () => {
      ensureOpen();
      await mkdir(store, { recursive: true });
      await ensureLock();
      await writeIfMissing(join(store, "units.tsv"), `${LEGACY_UNIT_HEADER}\n`);
      await writeIfMissing(join(store, "ledger.tsv"), `${LEDGER_HEADER}\n`);
      await mkdir(join(store, "inbox"), { recursive: true });
      await writeIfMissing(join(store, "gates.md"), "");
      await writeIfMissing(join(store, "preferences.md"), "");
      await writeIfMissing(join(store, "frontier.json"), "{}\n");
      return { store };
    },
    close: async () => {
      if (closed) {
        return;
      }
      if (lockRequest !== null) {
        try {
          await lockRequest;
        } catch {
          // Une acquisition échouée n’a aucun verrou à libérer.
        }
      }
      const lock = heldLock;
      heldLock = null;
      closed = true;
      if (lock !== null) {
        await lock.release();
      }
    },
  };
  // The directory lock excludes other handles/processes. A queue also excludes
  // overlapping async mutations through this same handle (including claim vs add).
  let writes: Promise<void> = Promise.resolve();
  const serial = <T>(operation: () => Promise<T>): Promise<T> => {
    const result = writes.then(operation);
    writes = result.then(() => {}, () => {});
    return result;
  };
  return {
    ...api,
    init: () => serial(api.init),
    close: () => serial(api.close),
    handoff: {
      import: spec => serial(() => api.handoff.import(spec)),
      ready: repo => serial(() => api.handoff.ready(repo)),
      claim: params => serial(() => api.handoff.claim(params)),
    },
    units: {...api.units, add: params => serial(() => api.units.add(params)), set: params => serial(() => api.units.set(params))},
    ledger: {...api.ledger, record: params => serial(() => api.ledger.record(params))},
    inbox: {...api.inbox, drain: () => serial(api.inbox.drain)},
    gates: {...api.gates, park: params => serial(() => api.gates.park(params)), resolve: params => serial(() => api.gates.resolve(params))},
    frontier: {...api.frontier, set: params => serial(() => api.frontier.set(params))},
    standing: {...api.standing, add: params => serial(() => api.standing.add(params))},
    status: {render: () => serial(api.status.render)},
  };
}

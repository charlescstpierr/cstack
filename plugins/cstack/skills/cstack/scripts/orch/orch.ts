#!/usr/bin/env bun

import { ensureDependenciesInstalled } from "../bootstrap.ts";
import { readFile } from "node:fs/promises";
import {
  NotFoundError,
  UsageError,
  openStore,
  parseVerdict,
  type Counts,
  type Frontier,
  type InboxPointer,
  type OpenGate,
  type StandingLine,
  type StatusReport,
  type Store,
  type Unit,
  type Verdict,
} from "./store.ts";

ensureDependenciesInstalled();
const {
  Command: CommanderCommand,
  CommanderError,
  InvalidArgumentError,
  Option,
} = await import("commander");
type Command = InstanceType<typeof CommanderCommand>;

const DISPLAY_LIMIT = 4;

interface Io {
  readonly stdout: (value: string) => void;
  readonly stderr: (value: string) => void;
}

interface GlobalOptions {
  readonly store?: string;
  readonly json: boolean;
  readonly force: boolean;
}

interface UnitAddOptions {
  readonly track: string;
  readonly brief?: string;
}

interface UnitSetOptions {
  readonly state: string;
  readonly branch?: string;
  readonly pr?: number;
  readonly sha?: string;
}

interface UnitListOptions {
  readonly state?: string;
  readonly track?: string;
}

interface LedgerRecordOptions {
  readonly evidence: string;
  readonly verifier?: string;
}

interface InboxPushOptions {
  readonly report?: string;
}

interface InboxDrainOptions {
  readonly peek: boolean;
}

interface GateParkOptions {
  readonly question: string;
  readonly options: string;
  readonly default: string;
}

interface GateResolveOptions {
  readonly answer: string;
}

interface FrontierSetOptions {
  readonly repo?: string;
  readonly prs?: readonly number[];
}

function message(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function positiveInteger(value: string): number {
  const parsed = Number(value);
  if (!/^[1-9]\d*$/.test(value) || !Number.isSafeInteger(parsed)) {
    throw new InvalidArgumentError("doit être un entier positif");
  }
  return parsed;
}

function prList(value: string): readonly number[] {
  const parts = value.split(",");
  if (parts.some((part) => part.length === 0)) {
    throw new InvalidArgumentError("exige une liste de PR separees par des virgules");
  }
  return parts.map(positiveInteger);
}

function countLine(value: Counts): string {
  const entries = Object.entries(value);
  return entries.length === 0
    ? "aucun"
    : entries.map(([name, count]) => `${name}=${count}`).join(", ");
}

function unitLine(unit: Unit): string {
  return [
    unit.id,
    unit.track,
    unit.state,
    unit.branch,
    unit.pr,
    unit.sha,
    unit.brief,
  ].join("\t");
}

function pointerLine(pointer: InboxPointer): string {
  return [
    pointer.ts,
    pointer.agent,
    pointer.unit,
    pointer.status,
    pointer.report,
  ].join("\t");
}

function gateLine(gate: OpenGate): string {
  return [
    gate.id,
    gate.question,
    gate.options,
    gate.defaultAnswer,
  ].join("\t");
}

function compactRows<T>(
  rows: readonly T[],
  format: (row: T) => string,
  empty: string,
  limit: number | null = DISPLAY_LIMIT
): string {
  if (rows.length === 0) {
    return empty;
  }
  const visible = limit === null ? rows : rows.slice(0, limit);
  const lines = visible.map(format);
  if (limit !== null && rows.length > limit) {
    lines.push(`... ${rows.length - limit} de plus; utiliser --json`);
  }
  return lines.join("\n");
}

function frontierLine(value: Frontier): string {
  const prs =
    value.prs.length === 0
      ? "aucun"
      : value.prs
          .map(
            (row) =>
              `${row.branches}#${row.pr}@${row.sha}:${row.state}`
          )
          .join(",");
  return `generation=${value.generation} prs=${prs} plus-basse-non-fusionnee=${value.lowestUnmerged ?? "aucune"} trou-ferme=${value.closedGap ?? "aucun"}`;
}

function statusLines(report: StatusReport): string {
  const visible = report.summary.openGateIds.slice(0, DISPLAY_LIMIT);
  const more =
    report.summary.openGateIds.length > DISPLAY_LIMIT
      ? `,+${report.summary.openGateIds.length - DISPLAY_LIMIT} de plus`
      : "";
  return [
    `comptes: unités=${report.units.length}; états=${countLine(report.summary.unitStates)}; registre=${countLine(report.summary.ledgerVerdicts)}`,
    `modifie: ${report.changed}`,
    `barrières ouvertes: ${report.summary.openGateIds.length}${
      visible.length > 0 ? `; ids=${visible.join(",")}${more}` : ""
    }`,
  ].join("\n");
}

function emit<T>(
  io: Io,
  json: boolean,
  value: T,
  compact: (result: T) => string,
  jsonValue: (result: T) => unknown = (result) => result
): void {
  const rendered = json
    ? JSON.stringify(jsonValue(value), null, 2)
    : compact(value);
  io.stdout(rendered.endsWith("\n") ? rendered : `${rendered}\n`);
}

function storeDirectory(program: Command): string {
  const value = program.opts<GlobalOptions>().store;
  if (value === undefined || value.trim().length === 0) {
    throw new UsageError("définir --store <dir> ou ORCH_STORE");
  }
  return value;
}

function frontierRepo(options: FrontierSetOptions): string {
  const value = options.repo;
  if (value === undefined || value.trim().length === 0) {
    throw new UsageError("définir --repo <dir> ou ORCH_REPO");
  }
  return value;
}

async function runStore<T>(
  program: Command,
  io: Io,
  operation: (store: Store) => Promise<T>,
  compact: (result: T) => string,
  jsonValue?: (result: T) => unknown
): Promise<void> {
  const options = program.opts<GlobalOptions>();
  const store = openStore(storeDirectory(program), {
    force: options.force,
    onLockStolen: (holder) =>
      io.stderr(`vol du verrou de magasin detenu par le pid ${holder}\n`),
    onStaleLock: (holder) =>
      io.stderr(`remplacement du verrou de magasin perime (pid ${holder} mort)\n`),
  });
  try {
    const result = await operation(store);
    emit(io, options.json, result, compact, jsonValue);
  } finally {
    await store.close();
  }
}

function leaf(parent: Command, name: string, description: string): Command {
  return parent
    .command(name)
    .description(description)
    .allowExcessArguments(false);
}

function requireSubcommand(program: Command): never {
  storeDirectory(program);
  throw new UsageError("une commande valide est requise");
}

function createProgram(io: Io): Command {
  const program = new CommanderCommand("orch")
    .description("Suivi d’orchestration en fichiers texte")
    .usage("[--store <dir>] [--json] [--force] <command>")
    .configureOutput({ writeOut: io.stdout, writeErr: io.stderr })
    .exitOverride()
    .helpOption("-h, --help", "afficher l’aide de la commande")
    .showHelpAfterError()
    .allowExcessArguments(false)
    .addOption(
      new Option("--store <dir>", "dossier du magasin (ou ORCH_STORE)").env(
        "ORCH_STORE"
      )
    )
    .option("--json", "afficher les lignes complètes en JSON", false)
    .option("--force", "voler un verrou de magasin existant", false);

  leaf(program, "init", "initialiser le magasin").action(() =>
    runStore(
      program,
      io,
      (store) => store.init(),
      (result) => `initialise ${result.store}`
    )
  );

  const handoff = program.command("handoff").description("transmettre une définition Horizon sans dispatch ni action distante")
    .action(() => requireSubcommand(program));
  leaf(handoff, "import <spec>", "valider et importer une spec Horizon, ou reprendre le même import")
    .action((spec: string) => runStore(program, io, store => store.handoff.import(spec), result =>
      `ajoutées=${result.added.join(",") || "aucune"} réutilisées=${result.reused.join(",") || "aucune"} version=${result.digest}`));
  leaf(handoff, "ready", "calculer les unités exécutables depuis leurs vrais bloqueurs")
    .requiredOption("--repo <dir>", "dépôt des branches locales et preuves")
    .action((options: { readonly repo: string }) => runStore(program, io, store => store.handoff.ready(options.repo), result =>
      `prêtes=${result.ready.join(",") || "aucune"}\n${result.blocked.map(unit => `${unit.id}: ${unit.reason}`).join("\n")}`));
  leaf(handoff, "claim <id>", "revendiquer une unité prête avant tout appel natif")
    .requiredOption("--repo <dir>", "dépôt des branches locales et preuves")
    .requiredOption("--owner <owner>", "identité stable du propriétaire")
    .requiredOption("--branch <branch>", "branche locale exclusive existante")
    .action((id: string, options: { readonly repo: string; readonly owner: string; readonly branch: string }) =>
      runStore(program, io, store => store.handoff.claim({id, ...options}), unitLine));

  const review = program.command("review").description("borner les corrections et vérifier leur patch").action(() => requireSubcommand(program));
  for (const command of ["open", "attempt", "record"] as const) {
    leaf(review, `${command} <request>`, "appliquer une requête JSON au suivi de correction")
      .action((request: string) => runStore(program, io,
        async store => store.review[command](JSON.parse(await readFile(request, "utf8"))),
        result => JSON.stringify(result)));
  }
  leaf(review, "check <id>", "relire le patch et les preuves avant livraison")
    .action((id: string) => runStore(program, io, async store => {
      const result = await store.review.check(id);
      if (!result.ready) throw new NotFoundError("REVIEW-NOT-READY", {compact:JSON.stringify(result),json:result});
      return result;
    }, result => JSON.stringify(result)));

  const unit = program
    .command("unit")
    .description("gérer les unités de travail")
    .action(() => requireSubcommand(program));
  leaf(unit, "add <id>", "ajouter une unité")
    .requiredOption("--track <track>", "piste de l’unité")
    .option("--brief <path>", "chemin du brief")
    .action((id: string, options: UnitAddOptions) =>
      runStore(
        program,
        io,
        (store) =>
          store.units.add({
            id,
            track: options.track,
            brief: options.brief,
          }),
        unitLine
      )
    );
  leaf(unit, "set <id>", "mettre à jour une unité")
    .requiredOption("--state <state>", "état de l’unité")
    .option("--branch <branch>", "nom de branche")
    .option("--pr <number>", "numéro de pull request", positiveInteger)
    .option("--sha <sha>", "commit SHA")
    .action((id: string, options: UnitSetOptions) =>
      runStore(
        program,
        io,
        (store) =>
          store.units.set({
            id,
            state: options.state,
            branch: options.branch,
            pr: options.pr,
            sha: options.sha,
          }),
        unitLine
      )
    );
  leaf(unit, "get <id>", "lire une unité").action((id: string) =>
    runStore(program, io, (store) => store.units.get(id), unitLine)
  );
  leaf(unit, "list", "lister les unités")
    .option("--state <state>", "filtrer par état")
    .option("--track <track>", "filtrer par piste")
    .action((options: UnitListOptions) =>
      runStore(
        program,
        io,
        (store) => store.units.list(options),
        (rows) => compactRows(rows, unitLine, "(aucune unité)")
      )
    );
  leaf(unit, "counts", "compter les unités par état").action(() =>
    runStore(program, io, (store) => store.units.counts(), countLine)
  );

  const ledger = program
    .command("ledger")
    .description("gérer les enregistrements de vérification")
    .action(() => requireSubcommand(program));
  leaf(ledger, "record", "enregistrer un verdict de verification")
    .argument("<pr>", "numéro de pull request", positiveInteger)
    .argument("<sha>", "commit SHA")
    .argument("<verdict>", "verdict de verification", parseVerdict)
    .requiredOption("--evidence <path>", "chemin de preuve")
    .option("--verifier <name>", "nom du vérificateur")
    .action(
      (
        pr: number,
        sha: string,
        verdict: Verdict,
        options: LedgerRecordOptions
      ) =>
        runStore(
          program,
          io,
          (store) =>
            store.ledger.record({
              pr,
              sha,
              verdict,
              evidence: options.evidence,
              verifier: options.verifier,
            }),
          (row) => `${row.pr}\t${row.sha}\t${row.verdict}`
        )
    );
  leaf(ledger, "check", "vérifier un verdict de vérification")
    .argument("<pr>", "numéro de pull request", positiveInteger)
    .argument("<sha>", "commit SHA")
    .action((pr: number, sha: string) =>
      runStore(
        program,
        io,
        (store) => store.ledger.check({ pr, sha }),
        (row) => row.verdict
      )
    );
  leaf(ledger, "summary", "compter les verdicts de verification").action(() =>
    runStore(program, io, (store) => store.ledger.summary(), countLine)
  );

  const inbox = program
    .command("inbox")
    .description("gérer les pointeurs d’agents")
    .action(() => requireSubcommand(program));
  leaf(inbox, "push <agent> <unit> <status>", "ajouter un pointeur a la boite de reception")
    .option("--report <path>", "chemin du rapport")
    .action(
      (
        agent: string,
        unitId: string,
        status: string,
        options: InboxPushOptions
      ) =>
        runStore(
          program,
          io,
          (store) =>
            store.inbox.push({
              agent,
              unit: unitId,
              status,
              report: options.report,
            }),
          (result) =>
            `${result.pointer.unit}\t${result.pointer.status}\t${result.filename}`,
          (result) => result.pointer
        )
    );
  leaf(inbox, "drain", "vider les pointeurs de boite de reception")
    .option("--peek", "lire sans vider", false)
    .action((options: InboxDrainOptions) =>
      runStore(
        program,
        io,
        (store) =>
          options.peek ? store.inbox.peek() : store.inbox.drain(),
        (rows) => compactRows(rows, pointerLine, "(vide)", null)
      )
    );
  leaf(inbox, "count", "compter les pointeurs de boite de reception").action(() =>
    runStore(
      program,
      io,
      (store) => store.inbox.count(),
      String,
      (count) => ({ count })
    )
  );

  const gate = program
    .command("gate")
    .description("gérer les barrières de décision")
    .action(() => requireSubcommand(program));
  leaf(gate, "park <id>", "mettre une barrière de décision en attente")
    .requiredOption("--question <question>", "question de barrière")
    .requiredOption("--options <options>", "options de barrière")
    .requiredOption("--default <answer>", "réponse par défaut")
    .action((id: string, options: GateParkOptions) =>
      runStore(
        program,
        io,
        (store) =>
          store.gates.park({
            id,
            question: options.question,
            options: options.options,
            defaultAnswer: options.default,
          }),
        (result) => `${result.id}\topen`
      )
    );
  leaf(gate, "list", "lister les barrières de décision ouvertes").action(() =>
    runStore(
      program,
      io,
      (store) => store.gates.list(),
      (rows) => compactRows(rows, gateLine, "(aucune barrière ouverte)")
    )
  );
  leaf(gate, "resolve <id>", "résoudre une barrière de décision")
    .requiredOption("--answer <answer>", "réponse choisie")
    .action((id: string, options: GateResolveOptions) =>
      runStore(
        program,
        io,
        (store) => store.gates.resolve({ id, answer: options.answer }),
        (result) => `${result.id}\tresolved\t${result.answer}`
      )
    );

  const frontier = program
    .command("frontier")
    .description("gérer la frontière de pile GitHub")
    .action(() => requireSubcommand(program));
  leaf(frontier, "set", "découvrir la pile GitHub et définir la frontière")
    .addOption(
      new Option(
        "--repo <dir>",
        "dossier du dépôt (ou ORCH_REPO)"
      ).env("ORCH_REPO")
    )
    .option(
      "--prs <n,...>",
      "ordre attendu optionnel des pull requests",
      prList
    )
    .action((options: FrontierSetOptions) =>
      runStore(
        program,
        io,
        (store) =>
          store.frontier.set({
            repo: frontierRepo(options),
            prs: options.prs,
          }),
        frontierLine
      )
    );
  leaf(frontier, "show", "afficher la frontière").action(() =>
    runStore(program, io, (store) => store.frontier.show(), frontierLine)
  );

  leaf(program, "status", "générer status.md et afficher un résumé").action(() =>
    runStore(program, io, (store) => store.status.render(), statusLines)
  );

  const standing = program
    .command("standing")
    .description("gérer les consignes permanentes")
    .action(() => requireSubcommand(program));
  leaf(standing, "show", "afficher les consignes permanentes").action(() =>
    runStore(
      program,
      io,
      (store) => store.standing.show(),
      (rows) =>
        compactRows(
          rows,
          (item: StandingLine) => `${item.number}. ${item.line}`,
          "(aucune consigne permanente)"
        )
    )
  );
  leaf(standing, "add <line>", "ajouter une consigne permanente").action((line: string) =>
    runStore(
      program,
      io,
      (store) => store.standing.add({ line }),
      (item) => `${item.number}. ${item.line}`
    )
  );

  program.action(() => requireSubcommand(program));
  return program;
}

function handleError(error: unknown, program: Command, io: Io): number {
  if (error instanceof CommanderError) {
    return error.exitCode === 0 ? 0 : 1;
  }
  const json = program.opts<GlobalOptions>().json;
  if (error instanceof NotFoundError) {
    const output = error.output;
    if (output === undefined) {
      io.stderr(`erreur: ${error.message}\n`);
    } else {
      emit(io, json, output.json, () => output.compact);
    }
    return error.message === "REVIEW-NOT-READY" ? 1 : 2;
  }
  io.stderr(`erreur: ${message(error)}\n`);
  if (error instanceof UsageError) {
    io.stderr(program.helpInformation());
  }
  return 1;
}

export async function main(
  argv: readonly string[],
  io: Io = {
    stdout: (value) => process.stdout.write(value),
    stderr: (value) => process.stderr.write(value),
  }
): Promise<number> {
  const program = createProgram(io);
  try {
    await program.parseAsync(argv, { from: "user" });
    return 0;
  } catch (error) {
    return handleError(error, program, io);
  }
}

if (import.meta.main) {
  process.exitCode = await main(process.argv.slice(2));
}

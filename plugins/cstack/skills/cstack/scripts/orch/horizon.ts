import { createHash } from "node:crypto";
import { lstat, readFile, readdir, realpath } from "node:fs/promises";
import { dirname, isAbsolute, relative, resolve, sep } from "node:path";

/** Immutable definition receipt only; execution stays in units.tsv and ledger.tsv. */
export interface HorizonUnit {
  readonly id: string;
  readonly source: string;
  readonly goal: string;
  readonly blocked_by: readonly string[];
  readonly acceptance: readonly string[];
  readonly writable: readonly string[];
  readonly forbidden: readonly string[];
  readonly context: readonly string[];
  readonly verify: readonly string[];
}
export interface HorizonDefinition {
  readonly schema: 1;
  readonly spec: string;
  readonly digest: string;
  readonly sources: Readonly<Record<string, string>>;
  readonly goal: string;
  readonly out_of_scope: readonly string[];
  readonly context: readonly string[];
  readonly decisions: readonly string[];
  readonly units: readonly HorizonUnit[];
}

function record(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}
function text(value: unknown, label: string): string {
  if (typeof value !== "string" || !value.trim() || /[\r\n\t]/.test(value) || /^(?:todo|tbd|<.*>)$/i.test(value.trim())) {
    throw new Error(`Horizon: ${label} incomplet`);
  }
  return value.trim();
}
function strings(value: unknown, label: string, allowEmpty = false): readonly string[] {
  if (!Array.isArray(value) || (!allowEmpty && value.length === 0)) throw new Error(`Horizon: ${label} doit être une liste explicite`);
  const result = value.map((item: unknown) => text(item, label));
  if (new Set(result).size !== result.length) throw new Error(`Horizon: ${label} contient des doublons`);
  return result;
}
function metadata(raw: string, path: string): Record<string, unknown> {
  const blocks = [...raw.matchAll(/^```horizon\r?\n([\s\S]*?)^```\s*$/gm)];
  if (blocks.length !== 1) throw new Error(`Horizon: ${path} exige exactement un bloc horizon JSON`);
  const value: unknown = JSON.parse(blocks[0]?.[1] ?? "");
  if (!record(value)) throw new Error(`Horizon: métadonnées invalides dans ${path}`);
  return value;
}
function scope(value: string): string {
  if (isAbsolute(value) || value.includes("\\") || value.includes("//") || value.split("/").some(p => p === ".." || p === ".") || /[*?\[\]{}]/.test(value) || /^(?:\.git|\.cstack)(?:\/|$)/.test(value)) {
    throw new Error(`Horizon: frontière inscriptible invalide: ${value}`);
  }
  return value.replace(/\/+$/, "");
}
function hash(raw: string): string { return createHash("sha256").update(raw).digest("hex"); }

export async function loadHorizon(specPath: string): Promise<HorizonDefinition> {
  const spec = await realpath(resolve(specPath));
  const root = dirname(spec);
  const sources: Record<string, string> = {};
  const read = async (path: string): Promise<string> => {
    const absolute = await realpath(resolve(root, path));
    const local = relative(root, absolute);
    if (local === ".." || local.startsWith(`..${sep}`) || isAbsolute(local) || !(await lstat(absolute)).isFile()) throw new Error(`Horizon: source hors du dossier de spec: ${path}`);
    const raw = await readFile(absolute, "utf8");
    sources[absolute] = hash(raw);
    return raw;
  };
  const data = metadata(await read(spec), spec);
  if (data.schema !== 1 || data.status !== "ready") throw new Error("Horizon: spec incomplète; schema: 1 et status: ready requis");
  const goal = text(data.goal, "goal de spec");
  const out_of_scope = strings(data.out_of_scope, "out_of_scope");
  const context = strings(data.context, "context de spec");
  const decisions = strings(data.decisions, "decisions", true);
  for (const path of decisions) {
    const raw = await read(path);
    const front = /^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/.exec(raw)?.[1];
    const statuses = front === undefined ? [] : [...front.matchAll(/^status:\s*([^\r\n]+)$/gm)];
    if (statuses.length !== 1 || statuses[0]?.[1]?.trim() !== "resolved") throw new Error(`Horizon: décision ${path} non resolved (waiting ou incomplète)`);
    const answer = /^## (?:Réponse|Answer)\s*\r?\n([\s\S]*?)(?=^## |$(?![\s\S]))/m.exec(raw)?.[1]?.trim();
    if (!answer || /^(?:[-*]\s*)?(?:<.*>|todo|tbd)$/is.test(answer)) throw new Error(`Horizon: réponse manquante pour ${path}`);
  }
  // A waiting human decision cannot disappear simply by omitting its pointer.
  const tickets = await readdir(resolve(root, "tickets")).catch((error: unknown) => {
    if (record(error) && error.code === "ENOENT") return [];
    throw error;
  });
  for (const name of tickets.filter(name => name.endsWith(".md"))) {
    const path = `tickets/${name}`;
    if (decisions.includes(path)) continue;
    const raw = await read(path);
    const front = /^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/.exec(raw)?.[1];
    const statuses = front === undefined ? [] : [...front.matchAll(/^status:\s*([^\r\n]+)$/gm)];
    if (statuses.length !== 1 || statuses[0]?.[1]?.trim() !== "out-of-scope") throw new Error(`Horizon: décision non référencée: ${path}`);
  }
  const units: HorizonUnit[] = [];
  for (const path of strings(data.units, "units")) {
    const value = metadata(await read(path), path);
    const id = text(value.id, "id d'unité");
    if (!/^[A-Za-z0-9][A-Za-z0-9_-]*$/.test(id)) throw new Error(`Horizon: id invalide: ${id}`);
    const writable = strings(value.writable, `${id}.writable`).map(scope);
    if (new Set(writable).size !== writable.length) throw new Error(`Horizon: ${id}.writable contient des doublons`);
    units.push({id, source: resolve(root, path), goal: text(value.goal, `${id}.goal`),
      blocked_by: strings(value.blocked_by, `${id}.blocked_by`, true),
      acceptance: strings(value.acceptance, `${id}.acceptance`),
      writable,
      forbidden: strings(value.forbidden, `${id}.forbidden`),
      context: strings(value.context, `${id}.context`),
      verify: strings(value.verify, `${id}.verify`)});
  }
  const byId = new Map(units.map(unit => [unit.id, unit]));
  if (byId.size !== units.length) throw new Error("Horizon: ids d'unités dupliqués");
  const visited = new Set<string>();
  const visiting = new Set<string>();
  const visit = (id: string): void => {
    if (visiting.has(id)) throw new Error(`Horizon: cycle à ${id}`);
    if (visited.has(id)) return;
    const unit = byId.get(id);
    if (!unit) throw new Error(`Horizon: blocked_by inconnu: ${id}`);
    visiting.add(id);
    unit.blocked_by.forEach(visit);
    visiting.delete(id);
    visited.add(id);
  };
  units.forEach(unit => visit(unit.id));
  const digest = hash(JSON.stringify(Object.entries(sources).sort(([a], [b]) => a.localeCompare(b))));
  return {schema: 1, spec, digest, sources, goal, out_of_scope, context, decisions, units};
}

export function horizonBrief(definition: HorizonDefinition, unit: HorizonUnit): string {
  return [
    `# ${unit.id}`, `GOAL\n${unit.goal}`,
    `SCOPE\n${unit.writable.join("\n")}\nBranche et worktree exclusifs enregistrés par le coordinateur avant dispatch.`,
    `CONTEXT\nSpec: ${definition.spec}\nVersion SHA256: ${definition.digest}\nUnité: ${unit.source}\nDécisions: ${definition.decisions.join(", ") || "aucune"}\nBloqueurs: ${unit.blocked_by.join(", ") || "aucun"}\n${[...definition.context, ...unit.context].join("\n")}`,
    `ACCEPTANCE\n${unit.acceptance.join("\n")}`, `VERIFY\n${unit.verify.join("\n")}`,
    "TIMEBOX\nRetourner les preuves partielles à la limite convenue avec le coordinateur.",
    `FORBIDDEN\n${[...definition.out_of_scope, ...unit.forbidden].join("\n")}\nPas de changement de topologie, force-push ou action distante sans autorité utilisateur explicite.`,
    "REPORT\nStatut, branche, SHA head, PR si autorisée, verdict, contrôles exécutés, preuves, écarts et suivis.",
    "STANDING\nLire preferences.md dans ce magasin et les instructions projet courantes.", "",
  ].join("\n\n");
}

export function overlappingScopes(a: HorizonUnit, b: HorizonUnit): boolean {
  return a.writable.some(left => b.writable.some(right => left === right || left.startsWith(`${right}/`) || right.startsWith(`${left}/`)));
}

import { createHash } from "node:crypto";
import { lstat, readFile, readdir, realpath } from "node:fs/promises";
import { basename, dirname, isAbsolute, relative, resolve, sep } from "node:path";

export interface HorizonContract {
  readonly id: string;
  readonly producer: string;
  readonly decision: string;
  readonly declaration: string;
  readonly values: readonly string[];
  readonly digest: string;
}
export interface HorizonRequirement {
  readonly id: string;
  readonly description: string;
}
export interface HorizonTest {
  readonly name: string;
  readonly requirements: readonly string[];
  readonly input: string;
  readonly assertions: readonly string[];
  readonly command: string;
  readonly success: string;
}

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
  readonly produces: readonly string[];
  readonly consumes: readonly { readonly id: string; readonly expectedDigest: string }[];
  readonly tests: readonly HorizonTest[];
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
  readonly contracts: readonly HorizonContract[];
  readonly requirements: readonly HorizonRequirement[];
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
function strings(value: unknown, label: string, allowEmpty = false, parse = text): readonly string[] {
  if (!Array.isArray(value) || (!allowEmpty && value.length === 0)) throw new Error(`Horizon: ${label} doit être une liste explicite`);
  const result = value.map((item: unknown) => parse(item, label));
  if (new Set(result).size !== result.length) throw new Error(`Horizon: ${label} contient des doublons`);
  return result;
}
function objects(value: unknown, label: string, allowEmpty = false): readonly Record<string, unknown>[] {
  if (!Array.isArray(value) || (!allowEmpty && value.length === 0)) throw new Error(`Horizon: ${label} doit être une liste explicite`);
  return value.map((item: unknown) => {
    if (!record(item)) throw new Error(`Horizon: ${label} contient un objet invalide`);
    return item;
  });
}
function exact(value: unknown, label: string): string {
  if (typeof value !== "string" || !value.trim() || /^(?:todo|tbd|<.*>)$/i.test(value.trim())) throw new Error(`Horizon: ${label} incomplet`);
  return value;
}
function uniqueIds<T extends { readonly id: string }>(items: readonly T[], label: string): Map<string, T> {
  const result = new Map(items.map(item => [item.id, item]));
  if (result.size !== items.length) throw new Error(`Horizon: ${label} dupliqués`);
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
  const contracts = objects(data.contracts, "contracts", true).map(value => {
    const contract = {id: text(value.id, "contract.id"), producer: text(value.producer, "contract.producer"),
      decision: text(value.decision, "contract.decision"), declaration: exact(value.declaration, "contract.declaration"),
      values: strings(value.values, "contract.values", true, exact)};
    if (contract.decision !== basename(spec) && !decisions.includes(contract.decision)) throw new Error(`Horizon: décision inconnue pour ${contract.id}: ${contract.decision}`);
    return {...contract, digest: hash(JSON.stringify(contract))};
  });
  const requirements = objects(data.requirements, "requirements").map(value => ({
    id: text(value.id, "requirement.id"), description: text(value.description, "requirement.description"),
  }));
  const byContract = uniqueIds(contracts, "contrats");
  const byRequirement = uniqueIds(requirements, "exigences");
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
      verify: strings(value.verify, `${id}.verify`),
      produces: strings(value.produces, `${id}.produces`, true),
      consumes: objects(value.consumes, `${id}.consumes`, true).map(item => ({
        id: text(item.id, `${id}.consumes.id`), expectedDigest: text(item.expectedDigest, `${id}.consumes.expectedDigest`),
      })),
      tests: objects(value.tests, `${id}.tests`).map(item => ({
        name: text(item.name, `${id}.tests.name`), requirements: strings(item.requirements, `${id}.tests.requirements`),
        input: exact(item.input, `${id}.tests.input`), assertions: strings(item.assertions, `${id}.tests.assertions`),
        command: text(item.command, `${id}.tests.command`), success: text(item.success, `${id}.tests.success`),
      }))});
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
  for (const contract of contracts) {
    const producer = byId.get(contract.producer);
    if (!producer || !producer.produces.includes(contract.id)) throw new Error(`Horizon: producteur absent ou incompatible pour ${contract.id}`);
  }
  const covered = new Set<string>();
  for (const unit of units) {
    const ancestors = new Set<string>();
    const collect = (id: string): void => {
      if (ancestors.has(id)) return;
      ancestors.add(id);
      byId.get(id)?.blocked_by.forEach(collect);
    };
    unit.blocked_by.forEach(collect);
    uniqueIds(unit.consumes, `${unit.id}.consumes`);
    for (const id of unit.produces) {
      if (byContract.get(id)?.producer !== unit.id) throw new Error(`Horizon: ${unit.id} ne produit pas le contrat ${id}`);
    }
    for (const consumed of unit.consumes) {
      const contract = byContract.get(consumed.id);
      if (!contract) throw new Error(`Horizon: contrat inconnu: ${consumed.id}`);
      if (!ancestors.has(contract.producer)) throw new Error(`Horizon: ${unit.id} consomme ${contract.id} sans dépendre de ${contract.producer}`);
      if (consumed.expectedDigest !== contract.digest) throw new Error(`Horizon: signature ou valeurs divergentes pour ${unit.id}/${contract.id}; attendu ${consumed.expectedDigest}, canonique ${contract.digest}`);
    }
    const names = unit.tests.map(test => test.name);
    if (new Set(names).size !== names.length) throw new Error(`Horizon: tests dupliqués dans ${unit.id}`);
    for (const test of unit.tests) {
      if (!unit.verify.includes(test.command)) throw new Error(`Horizon: commande du test ${unit.id}/${test.name} absente de verify`);
      for (const id of test.requirements) {
        if (!byRequirement.has(id)) throw new Error(`Horizon: exigence inconnue: ${id}`);
        covered.add(id);
      }
    }
  }
  const uncovered = requirements.filter(requirement => !covered.has(requirement.id));
  if (uncovered.length) throw new Error(`Horizon: exigences sans tâche et test: ${uncovered.map(item => item.id).join(", ")}`);
  const digest = hash(JSON.stringify(Object.entries(sources).sort(([a], [b]) => a.localeCompare(b))));
  return {schema: 1, spec, digest, sources, goal, out_of_scope, context, decisions, units, contracts, requirements};
}

export function horizonBrief(definition: HorizonDefinition, unit: HorizonUnit): string {
  const contractIds = new Set([...unit.produces, ...unit.consumes.map(item => item.id)]);
  const requirementIds = new Set(unit.tests.flatMap(test => test.requirements));
  return [
    `# ${unit.id}`, `GOAL\n${unit.goal}`,
    `SCOPE\n${unit.writable.join("\n")}\nBranche et worktree exclusifs enregistrés par le coordinateur avant dispatch.`,
    `CONTEXT\nSpec: ${definition.spec}\nVersion SHA256: ${definition.digest} (empreinte agrégée des sources, pas du seul fichier spec)\nUnité: ${unit.source}\nDécisions (chemins relatifs au dossier de la spec): ${definition.decisions.join(", ") || "aucune"}\nBloqueurs: ${unit.blocked_by.join(", ") || "aucun"}\n${[...definition.context, ...unit.context].join("\n")}`,
    `CONTRACTS\n${definition.contracts.filter(contract => contractIds.has(contract.id)).map(contract => `${contract.id} | producteur ${contract.producer} | décision ${contract.decision} | SHA256 ${contract.digest}\n${contract.declaration}\nValeurs JSON: ${JSON.stringify(contract.values)}`).join("\n\n") || "aucun"}`,
    `REQUIREMENTS\n${definition.requirements.filter(requirement => requirementIds.has(requirement.id)).map(requirement => `${requirement.id}: ${requirement.description}`).join("\n")}`,
    `TESTS\n${unit.tests.map(test => `${test.name} | exigences ${test.requirements.join(", ")}\nEntrée: ${test.input}\nAssertions: ${test.assertions.join("; ")}\nCommande: ${test.command}\nSuccès: ${test.success}`).join("\n\n")}`,
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

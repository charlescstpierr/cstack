#!/usr/bin/env bun
import { createHash } from "node:crypto";
import { existsSync, readFileSync, readdirSync, realpathSync, statSync } from "node:fs";
import { dirname, isAbsolute, join, relative, resolve } from "node:path";

const DIRECT_INVOCATION_ONLY: Record<string, string> = {
  "automate-me": "Utilitaire d’automatisation Cursor invoqué directement, sans passer par le routeur.",
  "bro": "Personnage conversationnel invoqué directement, sans passer par le routeur.",
  "create-verification-skill": "Générateur de skills de vérification invoqué directement, sans passer par le routeur.",
  "maintain-verification-skill": "Maintenance des skills de vérification invoquée directement, sans passer par le routeur.",
  "make-bot-ui": "Utilitaire d’interface de bot Grok invoqué directement, sans passer par le routeur.",
  "setup-cstack": "Utilitaire de configuration invoqué directement, sans passer par le routeur.",
};
// Plafond commun des SKILL.md hors routeur : technical-writing, la plus longue skill pstack après poteto-mode (1 830 mots), plus la marge du français.
const SKILL_WORD_CEILING = 2150;
// `$cstack:cstack` lit seulement son SKILL.md d’avance ; le contrat se lit par parties, à la demande.
const ENTRY_WORD_BUDGET = 2600;
const EXECUTABLES = [
  "scripts/run-tool.sh",
  "skills/cstack/scripts/worktree-audit.sh",
  "skills/cstack/scripts/watch-pr/watch-pr",
  "skills/cstack/scripts/watch-pr/ship-pr",
  "skills/cstack/scripts/check-plan.mjs",
  "skills/show-me-your-work/scripts/log.sh",
];
const CAPACITY_HEDGES = [
  "when native capacity permits",
  "when capacity permits",
  "when native review is available",
  "when native capacity makes",
  "si la capacité native le permet",
  "lorsque la capacité native le permet",
  "si la capacité le permet",
  "si la revue native est disponible",
];

// Même compte que `wc -w` : les suites d’espaces séparent les mots.
function words(text: string): number {
  return text.split(/\s+/).filter(Boolean).length;
}

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function requireValue(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

function json(path: string): Record<string, unknown> {
  const value: unknown = JSON.parse(readFileSync(path, "utf8"));
  requireValue(record(value), `${path}: objet attendu`);
  return value;
}

function files(path: string): string[] {
  return readdirSync(path, { withFileTypes: true }).flatMap((entry) => {
    if (["node_modules", ".git", ".cstack", "__pycache__"].includes(entry.name)) return [];
    requireValue(!entry.isSymbolicLink(), `${join(path, entry.name)}: les liens symboliques ne sont pas distribués`);
    const target = join(path, entry.name);
    return entry.isDirectory() ? files(target) : [target];
  });
}

function inside(root: string, target: string): boolean {
  const path = relative(realpathSync(root), realpathSync(target));
  return path !== ".." && !path.startsWith("../") && !isAbsolute(path);
}

function posix(root: string, target: string): string {
  return relative(root, target).split("\\").join("/");
}

function gitBlob(bytes: Uint8Array): string {
  return createHash("sha1").update(`blob ${bytes.byteLength}\0`).update(bytes).digest("hex");
}

function headingSlugs(text: string): Set<string> {
  const slugs = new Set<string>();
  const seen: Record<string, number> = {};
  for (const match of text.matchAll(/^#{1,6}\s+(.+?)\s*$/gm)) {
    const heading = (match[1] ?? "")
      .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
      .replace(/[`*_~]/g, "");
    const base = heading
      .toLowerCase()
      .replace(/[^\p{L}\p{N}\s_-]/gu, "")
      .trim()
      .replace(/\s+/g, "-");
    const count = (seen[base] = (seen[base] ?? 0) + 1);
    slugs.add(count === 1 ? base : `${base}-${count - 1}`);
  }
  return slugs;
}

function workspaceTick(raw: string): boolean {
  if (raw.includes("<")) return true;
  if (raw === "docs/agents/cstack.md" || /(^|\/)docs\/agents\//.test(raw)) return true;
  if (raw.startsWith(".cstack/") || raw.includes("/.cstack/")) return true;
  if (/^docs\/adr\//.test(raw) || /^tickets\//.test(raw) || raw.includes("NNNN")) return true;
  return false;
}

function pluginRelativeTick(raw: string): boolean {
  return raw.startsWith("./") || raw.startsWith("../") || raw.includes("/");
}

function markdownSection(text: string, heading: string): string | undefined {
  const escaped = heading.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = text.match(new RegExp("^## " + escaped + "(?:\\s|$).*", "m"));
  if (!match || match.index === undefined) return undefined;
  const start = match.index;
  const rest = text.slice(start + match[0].length);
  const next = rest.search(/^## /m);
  return text.slice(start, next === -1 ? undefined : start + match[0].length + next);
}

function assertQuotedCounts(rel: string, text: string, skills: number, principles: number, playbooks: number, upstream: number): void {
  for (const match of text.matchAll(/\b(\d+)\s+(?:skills|compétences)\b/gi)) {
    requireValue(Number(match[1]) === skills, `${rel}: nombre de skills cité ${match[1]} ne correspond pas à ${skills}`);
  }
  for (const match of text.matchAll(/\b(\d+)\s+principles?\b/gi)) {
    requireValue(Number(match[1]) === principles, `${rel}: nombre de principes cité ${match[1]} ne correspond pas à ${principles}`);
  }
  for (const match of text.matchAll(/\b(\d+)\s+principes?\b/gi)) {
    requireValue(Number(match[1]) === principles, `${rel}: nombre de principes cité ${match[1]} ne correspond pas à ${principles}`);
  }
  for (const match of text.matchAll(/\b(\d+)\s+(?:playbooks?|guides? opérationnels?|guides? d[’']exécution)\b/gi)) {
    requireValue(Number(match[1]) === playbooks, `${rel}: nombre de guides opérationnels cité ${match[1]} ne correspond pas à ${playbooks}`);
  }
  for (const match of text.matchAll(/\b(\d+)\s+fichiers(?:\s+upstream|\s+de provenance(?: pstack)?|\s+source)\b/gi)) {
    requireValue(Number(match[1]) === upstream, `${rel}: nombre de fichiers amont cité ${match[1]} ne correspond pas à ${upstream}`);
  }
  for (const match of text.matchAll(/\b(\d+)\s+upstream files\b/gi)) {
    requireValue(Number(match[1]) === upstream, `${rel}: nombre de fichiers amont cité ${match[1]} ne correspond pas à ${upstream}`);
  }
}

function keys(value: Record<string, unknown>, expected: string[], path: string): void {
  for (const key of Object.keys(value)) {
    requireValue(expected.includes(key), `${path}: clé inconnue de l’interface du skill ${key}`);
  }
  for (const key of expected) {
    requireValue(key in value, `${path}: champ manquant ${key}`);
  }
}

export function validate(root: string): { skills: number; sourceFiles: number } {
  const plugin = join(root, "plugins/cstack");
  const manifest = json(join(plugin, ".codex-plugin/plugin.json"));
  requireValue(manifest.name === "cstack" && manifest.skills === "./skills/", "identité du manifeste cstack ou chemin des skills invalide");
  requireValue(typeof manifest.version === "string" && /^\d+\.\d+\.\d+$/.test(manifest.version), "version du plugin invalide");
  requireValue(manifest.license === "MIT", "la licence MIT de la source amont doit être conservée");
  requireValue(record(manifest.author) && typeof manifest.author.name === "string", "auteur du plugin manquant");
  requireValue(record(manifest.interface), "interface du plugin manquante");
  for (const key of ["displayName", "shortDescription", "longDescription", "developerName", "category"]) {
    requireValue(typeof manifest.interface[key] === "string" && manifest.interface[key], `champ manquant interface.${key}`);
  }
  for (const key of ["logo", "composerIcon"]) {
    const value = manifest.interface[key];
    requireValue(typeof value === "string" && value.startsWith("./"), `champ invalide interface.${key}`);
    const target = resolve(plugin, value);
    requireValue(existsSync(target) && inside(plugin, target), `ressource absente ou située hors du périmètre ${value}`);
  }
  const version = manifest.version;
  const evidence = join(root, "docs/evidence", `${version}.json`);
  const changelog = join(root, "CHANGELOG.md");
  const changelogText = existsSync(changelog) ? readFileSync(changelog, "utf8") : "";
  requireValue(
    existsSync(evidence) || new RegExp(`^#{1,3}[^\\n]*\\b${String(version).replace(/\\./g, "\\.")}\\b`, "m").test(changelogText),
    `journal des modifications ou preuve manquants pour la version du plugin ${version}`,
  );
  const marketplace = json(join(root, ".agents/plugins/marketplace.json"));
  requireValue(marketplace.name === "cstack" && Array.isArray(marketplace.plugins) && marketplace.plugins.length === 1, "le catalogue doit contenir uniquement cstack");
  const entry: unknown = marketplace.plugins[0];
  requireValue(record(entry) && entry.name === "cstack" && record(entry.source), "plugin du catalogue invalide");
  requireValue(entry.source.source === "local" && entry.source.path === "./plugins/cstack", "la source du catalogue ne pointe pas vers cstack");
  requireValue(record(entry.policy) && entry.policy.installation === "AVAILABLE" && entry.policy.authentication === "ON_INSTALL", "politique du catalogue invalide");

  const inventory = json(join(root, "UPSTREAM.json"));
  const coverage = json(join(root, "PORTING.json"));
  requireValue(typeof inventory.commit === "string" && /^[a-f0-9]{40}$/.test(inventory.commit)
    && coverage.commit === inventory.commit, "le commit amont ne correspond pas");
  requireValue(inventory.repository === "https://github.com/cursor/plugins" && inventory.subdirectory === "pstack",
    "dépôt ou sous-arbre amont invalide");
  requireValue(Array.isArray(inventory.files) && Array.isArray(coverage.files), "inventaire des sources manquant");
  const sourcePaths = new Set<string>();
  const sourceBlobs = new Map<string, string>();
  const principleTargets = new Set<string>();
  for (const item of inventory.files) {
    requireValue(record(item) && typeof item.path === "string" && typeof item.git_blob === "string", "entrée source invalide");
    requireValue(item.path.startsWith("pstack/") && /^[a-f0-9]{40}$/.test(item.git_blob) && !sourcePaths.has(item.path), "chemin ou blob amont invalide ou dupliqué");
    sourcePaths.add(item.path);
    sourceBlobs.set(item.path, item.git_blob);
  }
  requireValue(sourcePaths.size > 0, "l’inventaire amont est vide");
  const covered = new Set<string>();
  const portTargets = new Set<string>();
  for (const item of coverage.files) {
    requireValue(record(item) && typeof item.source === "string" && typeof item.target === "string", "entrée de portage invalide");
    requireValue(sourcePaths.has(item.source) && !covered.has(item.source), `source inconnue ou répétée: ${item.source}`);
    requireValue(["ported", "retained", "replaced", "unsupported"].includes(String(item.status)), `statut invalide pour ${item.source}`);
    requireValue(typeof item.reason === "string" && item.reason.length > 0, `motif de portage manquant pour ${item.source}`);
    const principle = /^pstack\/skills\/principle-(.+)\/SKILL\.md$/.exec(item.source);
    if (principle) {
      const expected = `plugins/cstack/skills/cstack/references/principles/${principle[1]}.md`;
      requireValue(item.target === expected, `${item.source}: cible de portage du principe doit être ${expected}`);
      principleTargets.add(expected.slice("plugins/cstack/".length));
    }
    const target = resolve(root, item.target);
    requireValue(existsSync(target) && inside(root, target), `cible de portage absente ou située hors du périmètre ${item.target}`);
    if (item.status === "retained") {
      const expected = sourceBlobs.get(item.source);
      const actual = gitBlob(readFileSync(target));
      requireValue(actual === expected, `${item.target}: blob conservé ${actual} ne correspond pas à la source amont ${expected}`);
    }
    portTargets.add(item.target);
    covered.add(item.source);
  }
  requireValue(covered.size === sourcePaths.size, "la couverture des sources est incomplète");
  requireValue(principleTargets.size === 23, `23 principes portés attendus, obtenu ${principleTargets.size}`);
  requireValue(Array.isArray(coverage.original), "inventaire des fichiers originaux manquant");
  const originalPaths = new Set<string>();
  for (const item of coverage.original) {
    requireValue(record(item) && typeof item.path === "string" && typeof item.reason === "string" && item.reason.length > 0, "entrée originale invalide");
    requireValue(item.path.startsWith("plugins/cstack/") && !originalPaths.has(item.path), `chemin original invalide ou dupliqué: ${item.path}`);
    const target = resolve(root, item.path);
    requireValue(existsSync(target) && inside(plugin, target), `le chemin original n’existe pas: ${item.path}`);
    // Un fichier extrait d’un texte porté garde la source amont dont il dérive.
    requireValue(!("derived_from" in item) || (typeof item.derived_from === "string" && sourcePaths.has(item.derived_from)), `source amont dérivée inconnue pour ${item.path}`);
    originalPaths.add(item.path);
  }

  const additions = json(join(plugin, "sources/matt-pocock.json"));
  requireValue(additions.repository === "https://github.com/mattpocock/skills"
    && additions.commit === "3cca18b368ae95cdbdebbff572ccafa662551015", "la provenance des sources de Matt ne correspond pas");
  requireValue(additions.license === "LICENSE-MATT-POCOCK"
    && readFileSync(join(plugin, "LICENSE-MATT-POCOCK"), "utf8").includes("Copyright (c) 2026 Matt Pocock"), "licence de Matt manquante");
  requireValue(Array.isArray(additions.adaptations) && additions.adaptations.length > 0, "adaptations de Matt manquantes");
  const adaptedTargets = new Set<string>();
  for (const item of additions.adaptations) {
    requireValue(record(item) && typeof item.target === "string" && !adaptedTargets.has(item.target), "adaptation de Matt invalide ou dupliquée");
    const target = resolve(plugin, item.target);
    requireValue(existsSync(target) && inside(plugin, target), "cible d’adaptation de Matt absente ou située hors du périmètre");
    requireValue(Array.isArray(item.sources) && item.sources.length > 0, "références aux sources de Matt manquantes");
    for (const source of item.sources) {
      requireValue(record(source) && typeof source.path === "string" && source.path.startsWith("skills/")
        && typeof source.sha256 === "string" && /^[a-f0-9]{64}$/.test(source.sha256), "référence à une source de Matt invalide");
    }
    adaptedTargets.add(item.target);
  }
  for (const name of ["clarify", "domain", "horizon", "audit-architecture"]) {
    requireValue(adaptedTargets.has(`skills/${name}/SKILL.md`), `provenance manquante pour ${name}`);
  }

  const deliverySources = json(join(plugin, "sources/pstack-claude.json"));
  requireValue(deliverySources.repository === "https://github.com/michael-denyer/pstack-claude"
    && typeof deliverySources.commit === "string" && /^[a-f0-9]{40}$/.test(deliverySources.commit)
    && deliverySources.license === "LICENSE", "provenance pstack-claude invalide");
  requireValue(Array.isArray(deliverySources.adaptations) && deliverySources.adaptations.length > 0,
    "adaptations pstack-claude manquantes");
  const deliveryTargets = new Set<string>();
  for (const item of deliverySources.adaptations) {
    requireValue(record(item) && typeof item.target === "string" && !deliveryTargets.has(item.target)
      && inside(plugin, resolve(plugin, item.target)) && existsSync(resolve(plugin, item.target)), "cible pstack-claude invalide");
    requireValue(Array.isArray(item.sources) && item.sources.length > 0, "sources pstack-claude manquantes");
    for (const source of item.sources) {
      requireValue(record(source) && typeof source.path === "string" && source.path.startsWith("plugins/pstack/")
        && !source.path.split("/").includes("..") && typeof source.sha256 === "string"
        && /^[a-f0-9]{64}$/.test(source.sha256), "empreinte pstack-claude invalide");
    }
    deliveryTargets.add(item.target);
  }

  const all = files(plugin);
  for (const path of all) {
    const rel = `plugins/cstack/${posix(plugin, path)}`;
    requireValue(portTargets.has(rel) || originalPaths.has(rel), `fichier du plugin non répertorié: ${rel}`);
  }
  const skills = all.filter((path) => path.endsWith("/SKILL.md") && relative(plugin, path).startsWith("skills/"));
  requireValue(!skills.some((path) => relative(join(plugin, "skills"), dirname(path)).startsWith("principle-")), "les points d’entrée des skills de principes ont été déplacés vers les références");
  requireValue(skills.length === 29, `29 points d’entrée de skills attendus, obtenu ${skills.length}`);
  const principleRefs = all.filter((path) => path.endsWith(".md") && relative(plugin, path).startsWith("skills/cstack/references/principles/"));
  requireValue(principleRefs.length === 23, `23 références de principes attendues, obtenu ${principleRefs.length}`);
  for (const path of principleRefs) {
    const target = relative(plugin, path);
    requireValue(principleTargets.has(target), `${target}: la référence du principe n’est pas couverte par PORTING.json`);
  }
  const playbooks = all.filter((path) => path.endsWith(".md") && relative(plugin, path).startsWith("skills/cstack/playbooks/"));
  requireValue(playbooks.length === 23, `23 guides opérationnels attendus, obtenu ${playbooks.length}`);
  for (const path of playbooks) {
    const text = readFileSync(path, "utf8");
    requireValue(text.startsWith("### "), `${posix(root, path)}: le guide opérationnel doit commencer par un titre ###`);
    requireValue(/Suivez \[le contrat d[’\x27]exécution Codex\]\([^)\n]*codex-runtime.md\)/.test(text), `${posix(root, path)}: le guide opérationnel n’a pas de ligne de contrat d’exécution`);
    requireValue(/\*\*Réponse\s*:\*\*/.test(text), `${posix(root, path)}: le guide opérationnel n’a pas de bloc Réponse`);
  }
  const mainSkill = readFileSync(join(plugin, "skills/cstack/SKILL.md"), "utf8");
  requireValue(mainSkill.includes("deux lectures raisonnables") && mainSkill.includes("Ne choisis pas silencieusement la lecture la plus probable") && mainSkill.includes("avant toute addition de fonctionnalité ou modification"), "cstack: porte de clarification d’alignement manquante");
  for (const target of principleTargets) {
    const href = relative("skills/cstack", target);
    requireValue(mainSkill.includes(`](${href})`), `${target}: la référence du principe n’est pas accessible depuis cstack/SKILL.md`);
  }
  const makeBotUi = readFileSync(join(plugin, "skills/make-bot-ui/SKILL.md"), "utf8");
  requireValue(!makeBotUi.includes("inject it into the HTML"), "make-bot-ui: le token de page ne doit pas être injecté dans le HTML");
  requireValue(makeBotUi.includes("Do not inject the page token into served HTML"), "make-bot-ui: garde anti-injection du token de page manquante");
  requireValue(makeBotUi.includes("Render a token input instead"), "make-bot-ui: saisie explicite du token de page manquante");
  requireValue(makeBotUi.includes("thread_id") && makeBotUi.includes("thread.started"), "make-bot-ui: persistance du thread_id initial manquante");
  requireValue(!makeBotUi.includes("codex exec resume --last") && !makeBotUi.includes("Use `resume --last`"), "make-bot-ui: reprise interdite avec resume --last");
  requireValue(makeBotUi.includes("codex exec resume") && makeBotUi.includes('"$SESSION_ID"'), "make-bot-ui: reprise par SESSION_ID manquante");
  requireValue(makeBotUi.includes('PROMPT_TEXT=$(<"$PROMPT_FILE")'), "make-bot-ui: lecture du contenu du prompt file manquante");
  requireValue(!makeBotUi.includes('"$PROMPT"'), "make-bot-ui: le chemin du prompt file ne doit pas être passé comme prompt");
  const names = new Set<string>();
  const skillUi: Array<{ policyPath: string; name: string; display: string }> = [];
  for (const path of skills) {
    const text = readFileSync(path, "utf8");
    const front = /^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/.exec(text);
    requireValue(front, `${path}: en-tête YAML manquant`);
    const metadata: unknown = Bun.YAML.parse(front[1] ?? "");
    requireValue(record(metadata), `${path}: en-tête YAML invalide`);
    const name = relative(join(plugin, "skills"), dirname(path));
    requireValue(metadata.name === name && /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(name), `${path}: name doit correspondre au dossier du skill`);
    requireValue(!names.has(name), `skill dupliqué ${name}`);
    names.add(name);
    requireValue(typeof metadata.description === "string" && metadata.description.trim().length > 0 && metadata.description.length <= 1024, `${path}: description invalide`);
    // Le nom suivi d'un autre caractère de nom (`$cstack:brother` pour `bro`) ne cite pas l'invocation.
    const invocation = `\\$cstack:${name}(?![a-z0-9-])`;
    requireValue(new RegExp(invocation).test(metadata.description), `${path}: la description doit citer son invocation canonique $cstack:${name}`);
    // make-bot-ui est rédigé en anglais, comme son corps que les gardes plus haut épinglent.
    requireValue(name === "make-bot-ui" || new RegExp(`^À utiliser pour ${invocation}`).test(metadata.description), `${path}: la description doit commencer par « À utiliser pour $cstack:${name} »`);
    requireValue(Object.keys(metadata).every((key) => ["name", "description", "license", "allowed-tools", "metadata"].includes(key)), `${path}: en-tête YAML du skill non pris en charge`);
    const policyPath = join(dirname(path), "agents/openai.yaml");
    const policy: unknown = Bun.YAML.parse(readFileSync(policyPath, "utf8"));
    requireValue(record(policy) && record(policy.policy) && policy.policy.allow_implicit_invocation === false, `${path}: le skill doit imposer une invocation explicite`);
    requireValue(record(policy.interface) && typeof policy.interface.display_name === "string" && typeof policy.interface.short_description === "string", `${path}: métadonnées d’interface du skill manquantes`);
    keys(policy, ["interface", "policy"], posix(root, policyPath));
    keys(policy.interface, ["display_name", "short_description", "default_prompt"], posix(root, policyPath));
    keys(policy.policy, ["allow_implicit_invocation"], posix(root, policyPath));
    skillUi.push({ policyPath: posix(root, policyPath), name, display: policy.interface.display_name });
    const summary = policy.interface.short_description.trim();
    requireValue(summary.length >= 25 && summary.length <= 64, `${path}: la longueur de la description d’interface du skill doit être comprise entre 25 et 64 caractères`);
    // Détecte les séparateurs et mots de liaison sans suite ; la prose nécessite aussi une relecture.
    requireValue(!/(?:[,;:]|\b(?:a|an|the|and|or|with|for|to|of|in|your|et|ou|avec|pour|de|du|des|le|la|les|un|une))$/i.test(summary), `${path}: description d’interface du skill tronquée`);
    requireValue(typeof policy.interface.default_prompt === "string" && policy.interface.default_prompt.includes(`$cstack:${name}`), `${path}: le prompt par défaut doit utiliser son invocation canonique`);
    // Chaque skill atteint les règles communes ; le routeur les porte en ligne et lie l’index du contrat.
    const contract = name === "cstack" ? "references/codex-runtime.md" : "../cstack/references/runtime/base.md";
    requireValue(text.includes(`](${contract})`), `${path}: lien vers le contrat d’exécution manquant (${contract})`);
    // Le routeur est lu à chaque invocation de `$cstack:cstack` : son plafond est le budget de lecture initiale.
    const count = words(text);
    const [ceiling, label] = name === "cstack" ? [ENTRY_WORD_BUDGET, "le budget de lecture initiale"] : [SKILL_WORD_CEILING, "le plafond"];
    requireValue(count <= ceiling, `${name}: ${count} mots dépassent ${label} de ${ceiling}`);
  }
  const seenDisplay = new Set<string>();
  for (const item of skillUi) {
    requireValue(!seenDisplay.has(item.display), `display_name de skill dupliqué ${item.display}`);
    seenDisplay.add(item.display);
  }
  for (const item of skillUi) {
    requireValue(item.display === item.name, `${item.policyPath}: display_name doit correspondre au dossier du skill`);
  }

  const reached = new Set<string>();
  const seen = new Set<string>();
  const queue = [join(plugin, "skills/cstack/SKILL.md")];
  while (queue.length > 0) {
    const current = queue.shift();
    if (!current || seen.has(current)) continue;
    seen.add(current);
    if (!existsSync(current) || !current.endsWith(".md") || !inside(plugin, current)) continue;
    const skillName = relative(join(plugin, "skills"), dirname(current));
    if (current.endsWith("/SKILL.md") && !skillName.includes("/") && !skillName.startsWith("..")) reached.add(skillName);
    const text = readFileSync(current, "utf8");
    const prose = text.replace(/```[\s\S]*?```/g, "");
    const refs: string[] = [];
    for (const match of prose.matchAll(/!?\[[^\]\n]*\]\(([^\s)]+)(?:\s+"[^"]*")?\)/g)) refs.push(match[1] ?? "");
    for (const match of prose.matchAll(/`(\.{0,2}[\w./-]*\.(?:md|sh|py|ts|mjs))`/g)) refs.push(match[1] ?? "");
    for (const href of refs) {
      if (!href || /^(?:[a-z][a-z0-9+.-]*:|#)/i.test(href) || href.includes("<")) continue;
      const part = decodeURIComponent(href.split("#")[0]?.split("?")[0] ?? "");
      if (!part) continue;
      const target = resolve(dirname(current), part);
      if (!existsSync(target) || !inside(plugin, target) || !target.endsWith(".md")) continue;
      queue.push(target);
    }
  }
  for (const name of names) {
    requireValue(reached.has(name) || name in DIRECT_INVOCATION_ONLY, `${name}: le skill n’est ni accessible depuis le routeur ni autorisé par la liste d’exceptions`);
  }

  for (const path of all.filter((path) => path.endsWith(".md"))) {
    const text = readFileSync(path, "utf8");
    // Les exemples de code peuvent contenir des chemins schématiques ; seuls les liens Markdown réels sont vérifiés.
    const prose = text.replace(/```[\s\S]*?```/g, "");
    for (const match of prose.matchAll(/!?\[[^\]\n]*\]\(([^\s)]+)(?:\s+"[^"]*")?\)/g)) {
      const href = match[1] ?? "";
      if (/^(?:[a-z][a-z0-9+.-]*:|#)/i.test(href) || href.includes("<")) continue;
      const [filePart, fragment] = href.split("#");
      const part = decodeURIComponent(filePart?.split("?")[0] ?? "");
      const target = part ? resolve(dirname(path), part) : path;
      requireValue(existsSync(target) && inside(plugin, target), `${relative(root, path)}: lien cassé ou situé hors du périmètre ${href}`);
      if (fragment && target.endsWith(".md")) {
        const slugs = headingSlugs(readFileSync(target, "utf8"));
        requireValue(slugs.has(fragment.toLowerCase()), `${relative(root, path)}: titre manquant pour le fragment ${href}`);
      }
    }
    for (const match of prose.matchAll(/`(\.{0,2}[\w./-]*\.(?:md|sh|py|ts|mjs))`/g)) {
      const raw = match[1] ?? "";
      if (!pluginRelativeTick(raw) || workspaceTick(raw)) continue;
      const target = resolve(dirname(path), raw);
      const rel = relative(plugin, target);
      if (rel === ".." || rel.startsWith("../") || isAbsolute(rel)) continue;
      requireValue(existsSync(target), `${posix(root, path)}: chemin du plugin introuvable ${raw}`);
    }
    requireValue(!/\b(?:omx|oh-my-codex)\b/i.test(text), `${path}: dépendance d’orchestration interdite`);
    requireValue(!/(?:~\/\.cursor\/|subagent_type\s*:|run_in_background\s*:|claude-fable-5|grok-4\.6|\.cursor\/settings\.json)/i.test(text), `${path}: contrat d’exécution Cursor non porté`);
    requireValue(!/\$cstack:principle-/i.test(text), `${path}: invocation de principe obsolète`);
    requireValue(!/\bprinciple-[a-z0-9-]+\/SKILL\.md/i.test(text), `${path}: référence de skill de principe obsolète`);
  }
  for (const path of [join(plugin, "skills/cstack/SKILL.md"), ...playbooks]) {
    const text = readFileSync(path, "utf8");
    for (const phrase of CAPACITY_HEDGES) {
      requireValue(!text.toLowerCase().includes(phrase), `${posix(root, path)}: régression de réserve sur la capacité ${phrase}`);
    }
  }
  // Les hooks du plugin se limitent au rappel du mode cstack : une seule forme permise.
  const reminderHook = { type: "command", command: 'python3 -S "${PLUGIN_ROOT}/hooks/mode.py"', timeout: 5 };
  const expectedHooks = { hooks: { UserPromptSubmit: [{ hooks: [reminderHook] }], SessionStart: [{ matcher: "compact|resume", hooks: [reminderHook] }] } };
  requireValue(JSON.stringify(json(join(plugin, "hooks/hooks.json"))) === JSON.stringify(expectedHooks), "hooks: hooks.json diffère du seul rappel de mode permis");
  for (const rel of EXECUTABLES) {
    const path = join(plugin, rel);
    const mode = statSync(path).mode & 0o777;
    requireValue(mode === 0o755, `plugins/cstack/${rel}: mode 0755 attendu, obtenu ${mode.toString(8)}`);
  }
  for (const path of [join(root, "README.md"), join(plugin, "README.md"), join(root, "docs/VERIFICATION.md")]) {
    if (!existsSync(path)) continue;
    const text = readFileSync(path, "utf8");
    const rel = posix(root, path);
    let catalog = text;
    if (rel.endsWith("docs/VERIFICATION.md")) {
      const heading = `État ${version}`;
      const section = markdownSection(text, heading);
      requireValue(section, `${rel}: section du catalogue actuel manquante ## ${heading}`);
      catalog = section;
    }
    assertQuotedCounts(rel, catalog, skills.length, principleRefs.length, playbooks.length, sourcePaths.size);
  }
  const license = readFileSync(join(plugin, "LICENSE"), "utf8");
  requireValue(license.includes("Copyright (c) 2026 Lauren Tan") && license.includes("Permission is hereby granted"), "licence originale manquante");
  return { skills: skills.length, sourceFiles: sourcePaths.size };
}

if (import.meta.main) {
  try {
    const result = validate(resolve(process.argv[2] ?? join(import.meta.dir, "..")));
    console.log(`${result.skills} skills et ${result.sourceFiles} références amont vérifiées contre les inventaires.`);
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  }
}

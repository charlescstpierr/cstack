#!/usr/bin/env bun

import { existsSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const FACTS_RELATIVE = "docs/GENERATED-FACTS.md";
const STATUSES = ["ported", "retained", "replaced", "unsupported"];

function json(root, relativePath) {
  return JSON.parse(readFileSync(join(root, relativePath), "utf8"));
}

function walkFiles(path) {
  if (!existsSync(path)) return [];
  return readdirSync(path, { withFileTypes: true }).flatMap((entry) => {
    if (["node_modules", ".git", ".cstack", "__pycache__"].includes(entry.name)) return [];
    const target = join(path, entry.name);
    return entry.isDirectory() ? walkFiles(target) : entry.isFile() ? [target] : [];
  });
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function requireValue(condition, message) {
  if (!condition) throw new Error(message);
}

export function collectFacts(root) {
  const upstream = json(root, "UPSTREAM.json");
  const porting = json(root, "PORTING.json");
  const manifest = json(root, "plugins/cstack/.codex-plugin/plugin.json");
  const sourceFiles = Array.isArray(upstream.files) ? upstream.files : [];
  const portedFiles = Array.isArray(porting.files) ? porting.files : [];

  requireValue(typeof upstream.commit === "string" && upstream.commit.length > 0, "UPSTREAM.json: commit manquant");
  requireValue(porting.commit === upstream.commit, "PORTING.json: commit différent de UPSTREAM.json");
  requireValue(sourceFiles.length === portedFiles.length, "PORTING.json: couverture des sources incomplète");

  const sources = new Set(sourceFiles.map((item) => item.path));
  const covered = new Set(portedFiles.map((item) => item.source));
  requireValue(sources.size === sourceFiles.length, "UPSTREAM.json: chemins source dupliqués");
  requireValue(covered.size === portedFiles.length && [...sources].every((path) => covered.has(path)), "PORTING.json: sources inconnues ou répétées");

  const statusCounts = Object.fromEntries(STATUSES.map((status) => [status, 0]));
  for (const item of portedFiles) {
    requireValue(STATUSES.includes(item.status), `PORTING.json: statut invalide ${item.status}`);
    statusCounts[item.status] += 1;
  }

  const skillsPath = join(root, "plugins/cstack/skills");
  const principlesPath = join(skillsPath, "cstack/references/principles");
  const playbooksPath = join(skillsPath, "cstack/playbooks");
  const skillFiles = walkFiles(skillsPath);
  const principleFiles = walkFiles(principlesPath);
  const playbookFiles = walkFiles(playbooksPath);

  return {
    pluginVersion: manifest.version,
    upstreamVersion: upstream.version,
    upstreamCommit: upstream.commit,
    skills: skillFiles.filter((path) => path.endsWith("/SKILL.md")).length,
    principles: principleFiles.filter((path) => path.endsWith(".md")).length,
    playbooks: playbookFiles.filter((path) => path.endsWith(".md")).length,
    sources: sourceFiles.length,
    statusCounts,
  };
}

export function renderFacts(facts) {
  const rows = [
    ["Version du plugin", facts.pluginVersion],
    ["Version amont", facts.upstreamVersion],
    ["Commit amont", `\`${facts.upstreamCommit}\``],
    ["Compétences", facts.skills],
    ["Principes internes", facts.principles],
    ["Guides d’exécution", facts.playbooks],
    ["Fichiers source amont", facts.sources],
    ["Fichiers `ported`", facts.statusCounts.ported],
    ["Fichiers `retained`", facts.statusCounts.retained],
    ["Fichiers `replaced`", facts.statusCounts.replaced],
    ["Fichiers `unsupported`", facts.statusCounts.unsupported],
  ];
  return [
    "<!-- Généré par scripts/generate-facts.mjs; ne pas modifier. -->",
    "# Faits générés",
    "",
    "| Fait | Valeur |",
    "| --- | --- |",
    ...rows.map(([label, value]) => `| ${label} | ${value} |`),
    "",
  ].join("\n");
}

function assertContains(text, relativePath, pattern, label) {
  requireValue(pattern.test(text), `${relativePath}: fait documentaire périmé (${label})`);
}

export function verifyDocumentationFacts(root, facts) {
  const read = (relativePath) => readFileSync(join(root, relativePath), "utf8");
  const commit = escapeRegExp(facts.upstreamCommit);
  // README and verification-report counts stay owned by scripts/validate.ts.

  assertContains(
    read("README.md"),
    "README.md",
    new RegExp("Version amont épinglée [^\\n]*commit `" + commit + "`"),
    "commit amont",
  );
  assertContains(
    read("plugins/cstack/README.md"),
    "plugins/cstack/README.md",
    new RegExp("Version amont épinglée `" + commit + "`"),
    "commit amont",
  );
  assertContains(
    read("plugins/cstack/docs/guide/README.md"),
    "plugins/cstack/docs/guide/README.md",
    new RegExp(`Utiliser les ${facts.principles} principes`),
    "principes du guide",
  );
  assertContains(
    read("plugins/cstack/docs/guide/02-cstack.md"),
    "plugins/cstack/docs/guide/02-cstack.md",
    new RegExp(`Le routeur en liste ${facts.playbooks}\\.`),
    "guides du routeur",
  );
  assertContains(
    read("plugins/cstack/docs/guide/08-principles.md"),
    "plugins/cstack/docs/guide/08-principles.md",
    new RegExp(`cstack fournit ${facts.principles} principes`),
    "principes du catalogue",
  );

  const porting = read("docs/PORTING.md");
  assertContains(porting, "docs/PORTING.md", new RegExp("commit `" + commit + "`"), "commit amont");
}

function parseArgs(args) {
  let root = resolve(fileURLToPath(new URL("..", import.meta.url)));
  let check = false;
  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index];
    if (arg === "--check") {
      check = true;
    } else if (arg === "--root" && args[index + 1]) {
      root = resolve(args[++index]);
    } else {
      throw new Error("usage: bun scripts/generate-facts.mjs [--check] [--root PATH]");
    }
  }
  return { root, check };
}

export function main(args = process.argv.slice(2)) {
  const { root, check } = parseArgs(args);
  const facts = collectFacts(root);
  const artifact = join(root, FACTS_RELATIVE);
  const expected = renderFacts(facts);

  if (check) {
    requireValue(existsSync(artifact), `${FACTS_RELATIVE}: artefact absent`);
    requireValue(readFileSync(artifact, "utf8") === expected, `${FACTS_RELATIVE}: artefact obsolète`);
    verifyDocumentationFacts(root, facts);
    console.log("faits générés et faits documentaires courants : OK");
    return;
  }

  if (!existsSync(artifact) || readFileSync(artifact, "utf8") !== expected) writeFileSync(artifact, expected);
  console.log(`${FACTS_RELATIVE}: à jour`);
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    main();
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  }
}

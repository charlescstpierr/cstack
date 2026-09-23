#!/usr/bin/env bun

// Adapted from pstack-claude tools/sync.mjs (MIT, Copyright (c) 2026 Lauren Tan).
// Provenance and source digest: MAINTENANCE-SOURCES.json.
// Three-way upstream synchronisation for the cstack port.
//
// The command is intentionally a preview by default.  An apply requires a
// resolution receipt whose pins, manifest digest, source blobs, local blobs,
// and approved result files all match the current tree.

import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import {
  chmodSync,
  existsSync,
  lstatSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  renameSync,
  rmSync,
  rmdirSync,
  statSync,
  unlinkSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { dirname, isAbsolute, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const SCRIPT_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const SHA1_RE = /^[0-9a-f]{40}$/;
const STATUS = new Set(["ported", "retained", "replaced", "unsupported"]);
const ACTIONS = new Set(["keep", "write", "delete", "map"]);

export class SyncError extends Error {
  constructor(message) {
    super(message);
    this.name = "SyncError";
  }
}

function fail(message) {
  throw new SyncError(message);
}

function sha256(value) {
  return createHash("sha256").update(value).digest("hex");
}

export function gitBlob(value) {
  const bytes = Buffer.isBuffer(value) ? value : Buffer.from(value);
  return createHash("sha1").update(`blob ${bytes.length}\0`).update(bytes).digest("hex");
}

function stable(value) {
  if (Array.isArray(value)) return value.map(stable);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.keys(value).sort().map((key) => [key, stable(value[key])]));
  }
  return value;
}

function stableJson(value) {
  return JSON.stringify(stable(value));
}

function readJson(path) {
  let raw;
  try {
    raw = readFileSync(path);
  } catch (error) {
    fail(`lecture impossible: ${path}: ${error.message}`);
  }
  try {
    return { raw, value: JSON.parse(raw.toString("utf8")) };
  } catch (error) {
    fail(`JSON invalide: ${path}: ${error.message}`);
  }
}

function text(value, label) {
  if (typeof value !== "string" || value.length === 0) fail(`${label} doit être non vide`);
  return value;
}

function sha(value, label) {
  text(value, label);
  if (!SHA1_RE.test(value)) fail(`${label} doit être un SHA-1 de 40 caractères`);
  return value;
}

function blob(value, label) {
  if (value !== null && (typeof value !== "string" || !SHA1_RE.test(value))) {
    fail(`${label} doit être un blob Git ou null`);
  }
  return value;
}

function runGit(cwd, args, { allowFailure = false } = {}) {
  const result = spawnSync("git", args, { cwd, encoding: "buffer", stdio: ["ignore", "pipe", "pipe"] });
  if (result.error) fail(`git indisponible: ${result.error.message}`);
  if (result.status !== 0 && !allowFailure) {
    const detail = result.stderr?.toString("utf8").trim() || `code ${result.status}`;
    fail(`git ${args.join(" ")} a échoué: ${detail}`);
  }
  return result;
}

function gitText(cwd, args, options = {}) {
  return runGit(cwd, args, options).stdout.toString("utf8");
}

function normalizedRepository(value) {
  let result = String(value).trim();
  if (result.startsWith("git@")) result = result.slice(4).replace(/^([^:]+):/, "$1/");
  result = result.replace(/^\w+:\/\//, "").replace(/^([^/]+)@/, "");
  result = result.replace(/\/+/g, "/").replace(/\.git\/?$/, "").replace(/\/$/, "");
  return result.toLowerCase();
}

function ensureInside(root, target, label) {
  const base = resolve(root);
  const value = resolve(target);
  if (value !== base && !value.startsWith(`${base}${sep}`)) fail(`${label} sort du dépôt: ${target}`);
  return value;
}

function relativeSafe(value, label) {
  text(value, label);
  if (value.includes("\0") || isAbsolute(value) || value.includes("\\")) {
    fail(`${label} doit être un chemin relatif POSIX`);
  }
  const normalized = value.split("/").filter(Boolean);
  if (normalized.includes("..")) fail(`${label} contient un chemin parent: ${value}`);
  return normalized.join("/");
}

function rejectSymlinkComponents(root, relativePath, label, { allowMissing = true } = {}) {
  const safe = relativeSafe(relativePath, label);
  const base = resolve(root);
  const absolute = ensureInside(base, join(base, safe), label);
  const components = safe ? safe.split("/") : [];
  let cursor = base;
  for (const component of components) {
    cursor = join(cursor, component);
    if (!existsSync(cursor)) {
      if (allowMissing) break;
      fail(`${label} absent: ${relativePath}`);
    }
    let info;
    try {
      info = lstatSync(cursor);
    } catch (error) {
      fail(`${label} illisible: ${relativePath}: ${error.message}`);
    }
    if (info.isSymbolicLink()) fail(`${label} est un lien symbolique: ${relativePath}`);
  }
  return absolute;
}

function workspacePath(root, value, label) {
  text(value, label);
  if (isAbsolute(value)) {
    const absolute = ensureInside(root, value, label);
    const relativePath = relative(resolve(root), absolute).split(sep).join("/");
    return { absolute: rejectSymlinkComponents(root, relativePath, label), relative: relativePath };
  }
  const relativePath = relativeSafe(value, label);
  return { absolute: rejectSymlinkComponents(root, relativePath, label), relative: relativePath };
}

function executableMode(mode) {
  return mode & 0o111 ? 0o755 : 0o644;
}

function modeValue(value, label) {
  if (value === null || value === undefined) return null;
  if (typeof value !== "number" || !Number.isInteger(value) || ![0o644, 0o755].includes(value)) {
    fail(`${label} doit être 0644, 0755 ou null`);
  }
  return value;
}

function localFile(root, target, label = "cible") {
  if (target === null) return { path: null, exists: false, bytes: null, blob: null, mode: 0o644, rawMode: 0o644 };
  const path = rejectSymlinkComponents(root, target, label);
  if (!existsSync(path)) return { path, exists: false, bytes: null, blob: null, mode: 0o644, rawMode: 0o644 };
  const info = lstatSync(path);
  if (info.isSymbolicLink()) fail(`${label} est un lien symbolique: ${target}`);
  if (!info.isFile()) fail(`${label} n'est pas un fichier: ${target}`);
  const bytes = readFileSync(path);
  const rawMode = info.mode & 0o777;
  return { path, exists: true, bytes, blob: gitBlob(bytes), mode: executableMode(rawMode), rawMode };
}

function validateTarget(root, target, label = "target") {
  if (target === null) return null;
  const safe = relativeSafe(target, label);
  if (!safe.startsWith("plugins/cstack/")) fail(`${label} hors du plugin cstack: ${target}`);
  rejectSymlinkComponents(root, safe, label);
  return safe;
}

function validateManifests(root) {
  const upstreamPath = join(root, "UPSTREAM.json");
  const portingPath = join(root, "PORTING.json");
  rejectSymlinkComponents(root, "UPSTREAM.json", "UPSTREAM.json", { allowMissing: false });
  rejectSymlinkComponents(root, "PORTING.json", "PORTING.json", { allowMissing: false });
  const upstream = readJson(upstreamPath);
  const porting = readJson(portingPath);
  if (!upstream.value || typeof upstream.value !== "object" || Array.isArray(upstream.value)) fail("UPSTREAM.json doit être un objet");
  if (!porting.value || typeof porting.value !== "object" || Array.isArray(porting.value)) fail("PORTING.json doit être un objet");
  const inventory = upstream.value;
  const coverage = porting.value;
  sha(inventory.commit, "UPSTREAM.commit");
  if (coverage.commit !== inventory.commit) fail("UPSTREAM.commit et PORTING.commit diffèrent");
  const repository = text(inventory.repository, "UPSTREAM.repository");
  const subdirectory = relativeSafe(inventory.subdirectory, "UPSTREAM.subdirectory");
  if (!Array.isArray(inventory.files) || !Array.isArray(coverage.files)) fail("les inventaires doivent contenir files[]");
  if (!Array.isArray(coverage.original)) fail("PORTING.original doit être un tableau");

  const sourcePaths = new Map();
  for (const item of inventory.files) {
    if (!item || typeof item !== "object") fail("entrée UPSTREAM.files invalide");
    const path = relativeSafe(item.path, "UPSTREAM.files.path");
    if (!path.startsWith(`${subdirectory}/`)) fail(`source hors subdirectory: ${path}`);
    if (sourcePaths.has(path)) fail(`source répétée: ${path}`);
    sourcePaths.set(path, sha(item.git_blob, `blob ${path}`));
  }
  const portBySource = new Map();
  const groups = new Map();
  for (const item of coverage.files) {
    if (!item || typeof item !== "object") fail("entrée PORTING.files invalide");
    const source = relativeSafe(item.source, "PORTING.files.source");
    if (!sourcePaths.has(source)) fail(`source PORTING inconnue: ${source}`);
    if (portBySource.has(source)) fail(`source PORTING répétée: ${source}`);
    const status = text(item.status, `statut ${source}`);
    if (!STATUS.has(status)) fail(`statut PORTING invalide: ${status}`);
    if (item.target === null || item.target === undefined) fail(`${source}: target obligatoire pour ${status}`);
    const target = validateTarget(root, item.target, `target ${source}`);
    if (!existsSync(join(root, target))) fail(`target PORTING absent: ${target}`);
    const reason = text(item.reason, `raison ${source}`);
    const entry = { ...item, source, target, status, reason };
    portBySource.set(source, entry);
    const key = target === null ? "<null>" : target;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(entry);
  }
  if (portBySource.size !== sourcePaths.size) {
    const missing = [...sourcePaths.keys()].filter((path) => !portBySource.has(path));
    fail(`couverture PORTING incomplète: ${missing.join(", ")}`);
  }
  const originals = new Map();
  for (const item of coverage.original) {
    if (!item || typeof item !== "object") fail("entrée PORTING.original invalide");
    const path = validateTarget(root, item.path, "PORTING.original.path");
    if (path === null || originals.has(path)) fail(`original invalide ou répété: ${item.path}`);
    if (!existsSync(join(root, path))) fail(`original absent: ${path}`);
    if (groups.has(path)) fail(`target et original se chevauchent: ${path}`);
    originals.set(path, { ...item, path, reason: text(item.reason, `raison original ${path}`) });
  }
  return {
    upstreamPath,
    portingPath,
    upstreamRaw: upstream.raw,
    portingRaw: porting.raw,
    inventory,
    coverage,
    repository,
    subdirectory,
    sourcePaths,
    portBySource,
    groups,
    originals,
    manifestSha256: sha256(Buffer.concat([
      Buffer.from("UPSTREAM.json\0"),
      upstream.raw,
      Buffer.from("PORTING.json\0"),
      porting.raw,
    ])),
  };
}

function sourceRoot(source) {
  let root;
  try {
    root = resolve(source);
    if (!existsSync(root) || !lstatSync(root).isDirectory()) fail(`source Git absente: ${source}`);
    if (lstatSync(root).isSymbolicLink()) fail(`source Git liée par symlink: ${source}`);
    root = resolve(gitText(root, ["rev-parse", "--show-toplevel"]).trim());
  } catch (error) {
    if (error instanceof SyncError) throw error;
    fail(`source Git invalide: ${source}: ${error.message}`);
  }
  return root;
}

function verifySource(source, repository) {
  const remote = gitText(source, ["remote", "get-url", "origin"]).trim();
  if (!remote || normalizedRepository(remote) !== normalizedRepository(repository)) {
    fail(`source Git mismatch: attendu ${repository}, obtenu ${remote || "aucun origin"}`);
  }
  return remote;
}

function verifyCommit(source, commit, label) {
  sha(commit, label);
  const result = runGit(source, ["cat-file", "-e", `${commit}^{commit}`], { allowFailure: true });
  if (result.status !== 0) fail(`${label} absent du checkout source: ${commit}`);
}

function parseLsTree(output, subdirectory, label) {
  const tree = new Map();
  for (const record of output.toString("utf8").split("\0")) {
    if (!record) continue;
    const tab = record.indexOf("\t");
    if (tab < 0) fail(`${label}: sortie git ls-tree invalide`);
    const [mode, type, object] = record.slice(0, tab).split(" ");
    const path = relativeSafe(record.slice(tab + 1), `${label}.path`);
    if (!path.startsWith(`${subdirectory}/`)) fail(`${label}: chemin hors subdirectory ${path}`);
    if (type !== "blob" || !["100644", "100755"].includes(mode)) {
      fail(`${label}: lien, sous-module ou mode non régulier refusé: ${path}`);
    }
    if (!SHA1_RE.test(object)) fail(`${label}: blob invalide pour ${path}`);
    if (tree.has(path)) fail(`${label}: source répétée ${path}`);
    tree.set(path, { path, blob: object, mode: mode === "100755" ? 0o755 : 0o644 });
  }
  return tree;
}

function sourceTree(source, commit, subdirectory) {
  const output = runGit(source, ["ls-tree", "-r", "-z", commit, "--", `${subdirectory}/`]).stdout;
  return parseLsTree(output, subdirectory, `${commit}:${subdirectory}`);
}

function sourceBytes(source, entry, cache) {
  if (!cache.has(entry.blob)) {
    const bytes = runGit(source, ["cat-file", "blob", entry.blob]).stdout;
    if (gitBlob(bytes) !== entry.blob) fail(`blob source incohérent: ${entry.path}`);
    cache.set(entry.blob, bytes);
  }
  return cache.get(entry.blob);
}

function snapshots(paths, oldTree, newTree) {
  return [...new Set(paths)].sort().map((path) => ({
    path,
    oldBlob: oldTree.get(path)?.blob ?? null,
    newBlob: newTree.get(path)?.blob ?? null,
    oldMode: oldTree.get(path)?.mode ?? null,
    newMode: newTree.get(path)?.mode ?? null,
  }));
}

function mergeFile(local, base, next) {
  const directory = mkdtempSync(join(tmpdir(), "cstack-sync-merge-"));
  const ours = join(directory, "ours");
  const ancestor = join(directory, "base");
  const theirs = join(directory, "theirs");
  try {
    writeFileSync(ours, local);
    writeFileSync(ancestor, base);
    writeFileSync(theirs, next);
    const result = runGit(directory, ["merge-file", "-p", ours, ancestor, theirs], { allowFailure: true });
    if (result.status === 0) return { kind: "clean", bytes: result.stdout, blob: gitBlob(result.stdout) };
    if (result.status > 0) return { kind: "conflict", hunks: result.status };
    fail(`git merge-file a échoué: ${result.stderr.toString("utf8").trim()}`);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
}

function sourceSet(entry) {
  return [...new Set([...(entry.oldSources ?? []), ...(entry.newSources ?? [])])].sort();
}

function makeUnit({ source, root, sourceRootPath, oldTree, newTree, originalPaths, bytesCache }) {
  const oldSources = source.oldSources ?? [];
  const newSources = source.newSources ?? [];
  const target = source.target ?? null;
  const sourceEntries = source.entries ?? [];
  const statusSet = [...new Set(sourceEntries.map((item) => item.status))].sort();
  const changed = sourceSnapshotsChanged(oldSources, newSources, oldTree, newTree);
  const added = newSources.filter((path) => !oldTree.has(path));
  const removed = oldSources.filter((path) => !newTree.has(path));
  const targetFile = localFile(root, target, `target ${target ?? "<null>"}`);
  if (target && originalPaths.has(target)) fail(`target protégé dans original[]: ${target}`);
  const manyToOne = oldSources.length > 1 || newSources.length > 1 || sourceEntries.length > 1;
  const needsMapping = added.length > 0 || target === null && oldSources.length === 0;
  let candidate = null;
  let candidateMode = null;
  let mergeKind = null;
  let mergeHunks = null;
  if (oldSources.length === 1 && newSources.length === 1 && changed && target && !manyToOne) {
    const oldEntry = oldTree.get(oldSources[0]);
    const newEntry = newTree.get(newSources[0]);
    const oldBytes = sourceBytes(sourceRootPath, oldEntry, bytesCache);
    const newBytes = sourceBytes(sourceRootPath, newEntry, bytesCache);
    if (targetFile.exists && targetFile.bytes.equals(oldBytes)) {
      candidate = { bytes: newBytes, blob: newEntry.blob };
      candidateMode = newEntry.mode;
      mergeKind = oldEntry.blob === newEntry.blob ? "mode-update" : "exact-old";
    } else if (oldEntry.blob !== newEntry.blob && targetFile.exists && !isBinary(oldBytes) && !isBinary(newBytes) && !isBinary(targetFile.bytes)) {
      const merged = mergeFile(targetFile.bytes, oldBytes, newBytes);
      mergeKind = merged.kind;
      if (merged.kind === "clean") {
        candidate = { bytes: merged.bytes, blob: merged.blob };
        candidateMode = newEntry.mode;
      }
      else mergeHunks = merged.hunks;
    }
  }
  const statusRequiresReview = statusSet.some((status) => status !== "retained");
  const autoEligible = changed && !needsMapping && removed.length === 0 &&
    !manyToOne && !statusRequiresReview && candidate && target;
  const requiresResolution = !autoEligible && (changed || needsMapping || removed.length > 0 ||
    !targetFile.exists && oldSources.length > 0);
  let state = "unchanged";
  if (added.length > 0 && oldSources.length === 0) state = "new";
  else if (removed.length > 0 && newSources.length === 0) state = "deleted";
  else if (mergeKind === "conflict") state = "conflict";
  else if (changed || needsMapping || !targetFile.exists && oldSources.length > 0) {
    state = requiresResolution ? "review-required" : "clean-update";
  }
  const auto = !requiresResolution && candidate && target;
  return {
    id: target ? `target:${target}` : `sources:${sourceSet({ oldSources, newSources }).join(",")}`,
    target,
    oldSources: [...oldSources].sort(),
    newSources: [...newSources].sort(),
    sources: sourceSet({ oldSources, newSources }),
    entries: sourceEntries.map((item) => ({ source: item.source, status: item.status, reason: item.reason })),
    status: statusSet.length === 1 ? statusSet[0] : "mixed",
    localBlob: targetFile.blob,
    localMode: targetFile.exists ? targetFile.mode : null,
    localExists: targetFile.exists,
    changed,
    added,
    removed,
    manyToOne,
    state,
    requiresResolution: Boolean(requiresResolution),
    candidateBlob: candidate?.blob ?? null,
    candidateMode,
    mergeKind,
    mergeHunks,
    auto,
    _targetFile: targetFile,
    _candidate: candidate,
  };
}

function sourceSnapshotsChanged(oldSources, newSources, oldTree, newTree) {
  const paths = new Set([...oldSources, ...newSources]);
  return [...paths].some((path) => {
    const oldEntry = oldTree.get(path);
    const newEntry = newTree.get(path);
    return oldEntry?.blob !== newEntry?.blob || oldEntry?.mode !== newEntry?.mode;
  });
}

function isBinary(bytes) {
  const limit = Math.min(bytes.length, 8000);
  for (let i = 0; i < limit; i += 1) if (bytes[i] === 0) return true;
  return false;
}

function planCore(preparedUnits, context) {
  const candidatePreview = (unit) => {
    if (!unit._candidate) return null;
    if (isBinary(unit._candidate.bytes)) {
      return { blob: unit._candidate.blob, encoding: "base64", data: unit._candidate.bytes.toString("base64") };
    }
    return { blob: unit._candidate.blob, encoding: "utf8", text: unit._candidate.bytes.toString("utf8") };
  };
  const entries = preparedUnits.map((unit) => ({
    id: unit.id,
    target: unit.target,
    sources: unit.sources,
    oldSources: unit.oldSources,
    newSources: unit.newSources,
    mappings: unit.entries,
    status: unit.status,
    localBlob: unit.localBlob,
    localMode: unit.localMode,
    changed: unit.changed,
    added: unit.added,
    removed: unit.removed,
    manyToOne: unit.manyToOne,
    state: unit.state,
    requiresResolution: unit.requiresResolution,
    candidateBlob: unit.candidateBlob,
    candidateMode: unit.candidateMode,
    candidate: candidatePreview(unit),
    mergeKind: unit.mergeKind,
    mergeHunks: unit.mergeHunks,
    snapshots: snapshots(unit.sources, context.oldTree, context.newTree),
  }));
  const core = {
    version: 1,
    repository: context.repository,
    subdirectory: context.subdirectory,
    oldPin: context.oldPin,
    newPin: context.newPin,
    manifestSha256: context.manifestSha256,
    entries,
  };
  const planSha256 = sha256(stableJson(core));
  return { ...core, planSha256 };
}

function resolutionTemplate(plan) {
  return {
    version: 1,
    repository: plan.repository,
    subdirectory: plan.subdirectory,
    oldPin: plan.oldPin,
    newPin: plan.newPin,
    manifestSha256: plan.manifestSha256,
    planSha256: plan.planSha256,
    groups: plan.entries.filter((entry) => entry.requiresResolution).map((entry) => ({
      sources: entry.sources,
      target: entry.target,
      mappings: entry.mappings,
      old: entry.snapshots.map((item) => ({ path: item.path, blob: item.oldBlob, mode: item.oldMode })),
      next: entry.snapshots.map((item) => ({ path: item.path, blob: item.newBlob, mode: item.newMode })),
      localBlob: entry.localBlob,
      localMode: entry.localMode,
      action: "keep",
      reason: "",
      result: null,
    })),
  };
}

function parseResolution(path) {
  const { value } = readJson(path);
  if (!value || typeof value !== "object" || Array.isArray(value)) fail("résolution: objet attendu");
  if (value.version !== 1) fail("résolution: version 1 attendue");
  if (!Array.isArray(value.groups)) fail("résolution.groups doit être un tableau");
  return value;
}

function validateResolution(prepared, resolutionPath) {
  const resolution = parseResolution(resolutionPath);
  const plan = prepared.plan;
  if (resolution.repository !== plan.repository || resolution.subdirectory !== plan.subdirectory) fail("résolution: source différente du plan");
  if (resolution.oldPin !== plan.oldPin || resolution.newPin !== plan.newPin) fail("résolution périmée: pins différents");
  if (resolution.manifestSha256 !== plan.manifestSha256) fail("résolution périmée: empreinte des manifestes différente");
  if (resolution.planSha256 !== plan.planSha256) fail("résolution périmée: empreinte du plan différente");
  const knownSources = new Set([...prepared.oldTree.keys(), ...prepared.newTree.keys()]);
  const assigned = new Set();
  const assignments = [];
  const required = prepared.units.filter((unit) => unit.requiresResolution);
  const targetAssignments = new Set();
  for (const group of resolution.groups) {
    if (!group || typeof group !== "object") fail("résolution: groupe invalide");
    if (!Array.isArray(group.sources) || group.sources.length === 0) fail("résolution: sources[] obligatoire");
    const sources = [...new Set(group.sources.map((value) => relativeSafe(value, "résolution.sources")))].sort();
    if (sources.length !== group.sources.length) fail("résolution: source répétée dans un groupe");
    for (const source of sources) if (!knownSources.has(source)) fail(`résolution: source inconnue ${source}`);
    if (group.target === null || group.target === undefined) fail("résolution.target obligatoire; unsupported doit pointer une notice existante");
    const target = validateTarget(prepared.root, group.target, "résolution.target");
    if (prepared.originalPaths.has(target)) fail(`résolution.target est protégé par original[]: ${target}`);
    if (target !== null && targetAssignments.has(target)) fail(`résolution: cible répétée ${target}`);
    if (target !== null) targetAssignments.add(target);
    const matched = required.filter((unit) => unit.sources.every((source) => sources.includes(source)));
    if (matched.length === 0) fail(`résolution: aucun changement correspondant à ${sources.join(", ")}`);
    const matchedSources = new Set(matched.flatMap((unit) => unit.sources));
    if (sources.length !== matchedSources.size || sources.some((source) => !matchedSources.has(source))) {
      fail(`résolution: sources hors union des changements correspondants: ${sources.join(", ")}`);
    }
    for (const unit of matched) {
      for (const source of unit.sources) {
        if (assigned.has(source)) fail(`résolution: source déjà résolue ${source}`);
        assigned.add(source);
      }
    }
    const expectedSnapshots = snapshots(sources, prepared.oldTree, prepared.newTree);
    validateResolutionSnapshots(group, expectedSnapshots);
    const expectedLocal = localFile(prepared.root, target, `résolution target ${target ?? "<null>"}`);
    if ((group.localBlob ?? null) !== expectedLocal.blob) fail(`résolution: localBlob différent pour ${target ?? sources.join(",")}`);
    if ((group.localMode ?? null) !== (expectedLocal.exists ? expectedLocal.mode : null)) fail(`résolution: localMode différent pour ${target}`);
    const action = text(group.action, "résolution.action");
    if (!ACTIONS.has(action)) fail(`résolution.action invalide: ${action}`);
    const reason = text(group.reason, "résolution.reason");
    const result = validateResult(prepared.root, group.result, target, action);
    const mappings = validateMappings(group, sources, prepared, target, action);
    const sourceModes = [...new Set(sources.filter((source) => prepared.newTree.has(source)).map((source) => prepared.newTree.get(source).mode))];
    const retainedMapping = mappings.some((mapping) => mapping.status === "retained" && prepared.newTree.has(mapping.source));
    if ((action === "write" || action === "map") && sourceModes.length > 1 && (!expectedLocal.exists || retainedMapping) && !result?.mode) {
      fail(`résolution.result.mode obligatoire pour les modes source multiples: ${target}`);
    }
    validateRetainedMappings(mappings, prepared, target, action, result);
    if (action === "delete" && sources.some((source) => prepared.newTree.has(source))) fail("résolution delete impossible avec source conservée");
    assignments.push({ group, sources, target, action, reason, result, mappings, matched });
  }
  for (const unit of required) {
    if (!unit.sources.some((source) => assigned.has(source))) fail(`résolution manquante: ${unit.id}`);
  }
  return { resolution, assignments };
}

function validateRetainedMappings(mappings, prepared, target, action, result) {
  const retained = mappings.filter((mapping) => mapping.status === "retained" && prepared.newTree.has(mapping.source));
  if (retained.length === 0) return;
  const finalBlob = result?.blob ?? localFile(prepared.root, target, `retained ${target}`).blob;
  for (const mapping of retained) {
    const expected = prepared.newTree.get(mapping.source).blob;
    if (finalBlob !== expected) fail(`retained ${mapping.source} doit rester identique au nouveau blob source`);
  }
}

function validateResolutionSnapshots(group, expected) {
  const normalize = (value, label) => {
    if (!Array.isArray(value)) fail(`résolution.${label} doit être un tableau`);
    const result = value.map((item) => ({
      path: relativeSafe(item?.path, `résolution.${label}.path`),
      blob: blob(item?.blob ?? null, `résolution.${label}.blob`),
      mode: modeValue(item?.mode, `résolution.${label}.mode`),
    })).sort((a, b) => a.path.localeCompare(b.path));
    if (new Set(result.map((item) => item.path)).size !== result.length) fail(`résolution.${label}: source répétée`);
    return result;
  };
  const old = normalize(group.old, "old").map((item) => ({ path: item.path, blob: item.blob, mode: item.mode }));
  const next = normalize(group.next, "next").map((item) => ({ path: item.path, blob: item.blob, mode: item.mode }));
  const expectedOld = expected.map((item) => ({ path: item.path, blob: item.oldBlob, mode: item.oldMode }));
  const expectedNext = expected.map((item) => ({ path: item.path, blob: item.newBlob, mode: item.newMode }));
  if (stableJson(old) !== stableJson(expectedOld)) fail("résolution.old ne correspond pas au plan");
  if (stableJson(next) !== stableJson(expectedNext)) fail("résolution.next ne correspond pas au plan");
}

function validateResult(root, value, target, action) {
  if (action !== "write" && action !== "map" && value !== null && value !== undefined) fail(`résolution ${action}: result interdit`);
  if (action === "write" && (!value || typeof value !== "object")) fail("résolution write: result obligatoire");
  if (action === "map" && (value === null || value === undefined) && !localFile(root, target, "résolution target").exists) {
    fail("résolution map: result obligatoire pour une nouvelle target");
  }
  if (value === null || value === undefined) return null;
  const resultPath = workspacePath(root, value.path, "résolution.result.path");
  const path = resultPath.absolute;
  const safe = resultPath.relative;
  if (target && safe === target) fail("résolution.result.path doit être distinct de target");
  if (!existsSync(path) || !lstatSync(path).isFile()) fail(`résolution result absent: ${value.path}`);
  const bytes = readFileSync(path);
  const expected = blob(value.blob, "résolution.result.blob");
  if (gitBlob(bytes) !== expected) fail(`résolution result blob différent: ${value.path}`);
  return { path, relative: safe, bytes, blob: expected, mode: modeValue(value.mode, "résolution.result.mode") };
}

function validateMappings(group, sources, prepared, target, action) {
  const current = new Map(prepared.portBySource);
  const mappingValues = group.mappings ?? null;
  if (mappingValues !== null && !Array.isArray(mappingValues)) fail("résolution.mappings doit être un tableau");
  const newSources = sources.filter((source) => prepared.newTree.has(source));
  const values = mappingValues ?? [];
  const bySource = new Map();
  for (const item of values) {
    if (!item || typeof item !== "object") fail("résolution mapping invalide");
    const source = relativeSafe(item.source, "résolution.mapping.source");
    if (!sources.includes(source) || bySource.has(source)) fail(`résolution mapping source invalide: ${source}`);
    const status = text(item.status, `résolution statut ${source}`);
    if (!STATUS.has(status)) fail(`résolution statut invalide: ${status}`);
    const reason = text(item.reason, `résolution raison ${source}`);
    bySource.set(source, { source, status, reason, target });
  }
  if (values.length > 0 && newSources.some((source) => !bySource.has(source))) fail("résolution mapping incomplet");
  if (values.length === 0 && newSources.some((source) => !current.has(source))) {
    const status = group.status;
    const reason = group.mappingReason ?? group.reason;
    if (!STATUS.has(status) || !reason) fail("nouvelle source: status et reason explicites obligatoires");
    for (const source of newSources) bySource.set(source, { source, status, reason: text(reason, "mappingReason"), target });
  }
  for (const source of newSources) {
    if (!bySource.has(source)) {
      const old = current.get(source);
      bySource.set(source, { source, status: old.status, reason: old.reason, target });
    }
  }
  if (action === "map" && newSources.length === 0) fail("résolution map sans source nouvelle");
  return [...bySource.values()];
}

function buildContext(root, source, newPin) {
  const manifests = validateManifests(root);
  const sourcePath = sourceRoot(source);
  verifySource(sourcePath, manifests.repository);
  verifyCommit(sourcePath, manifests.inventory.commit, "UPSTREAM.commit");
  verifyCommit(sourcePath, newPin, "--to");
  const oldTree = sourceTree(sourcePath, manifests.inventory.commit, manifests.subdirectory);
  const newTree = sourceTree(sourcePath, newPin, manifests.subdirectory);
  if (oldTree.size !== manifests.inventory.files.length) fail("UPSTREAM.files ne couvre pas exactement l’ancien arbre source");
  for (const [path, expected] of manifests.sourcePaths) {
    if (!oldTree.has(path)) fail(`source absente au pin courant: ${path}`);
    if (oldTree.get(path).blob !== expected) fail(`blob UPSTREAM incorrect pour ${path}`);
  }
  for (const path of oldTree.keys()) if (!manifests.sourcePaths.has(path)) fail(`source ancienne non inventoriée: ${path}`);
  for (const entry of manifests.portBySource.values()) {
    if (entry.status !== "retained") continue;
    const source = oldTree.get(entry.source);
    const actual = localFile(root, entry.target, `retained ${entry.target}`);
    if (actual.blob !== source?.blob || actual.mode !== source?.mode) {
      fail(`retained invalide avant synchronisation: ${entry.target} (${actual.blob ?? "absent"}/${actual.mode} != ${source?.blob}/${source?.mode})`);
    }
  }
  const bytesCache = new Map();
  const originalPaths = new Set(manifests.originals.keys());
  const units = [];
  for (const [key, entries] of manifests.groups) {
    const oldSources = entries.map((item) => item.source);
    const newSources = oldSources.filter((path) => newTree.has(path));
    units.push(makeUnit({
      source: { target: key === "<null>" ? null : key, oldSources, newSources, entries },
      root,
      sourceRootPath: sourcePath,
      oldTree,
      newTree,
      originalPaths,
      bytesCache,
    }));
  }
  for (const path of newTree.keys()) {
    if (manifests.sourcePaths.has(path)) continue;
    units.push(makeUnit({
      source: { target: null, oldSources: [], newSources: [path], entries: [] },
      root,
      sourceRootPath: sourcePath,
      oldTree,
      newTree,
      originalPaths,
      bytesCache,
    }));
  }
  const coreContext = {
    root,
    source: sourcePath,
    repository: manifests.repository,
    subdirectory: manifests.subdirectory,
    oldPin: manifests.inventory.commit,
    newPin,
    manifestSha256: manifests.manifestSha256,
    oldTree,
    newTree,
    manifests,
  };
  const plan = planCore(units, coreContext);
  return { ...coreContext, units, plan, originalPaths };
}

function applyAssignments(prepared, assignments) {
  const operations = [];
  const operationPaths = new Set();
  const addOperation = (kind, target, bytes, mode, expectedBlob, expectedMode, assignment = null) => {
    if (!target) return;
    if (prepared.originalPaths.has(target)) fail(`écriture d’un original interdite: ${target}`);
    if (operationPaths.has(target)) fail(`opérations concurrentes sur ${target}`);
    operationPaths.add(target);
    operations.push({ kind, target, bytes, mode, expectedBlob, expectedMode, assignment });
  };
  for (const unit of prepared.units) {
    if (unit.auto) addOperation("write", unit.target, unit._candidate.bytes, unit.candidateMode, unit.localBlob, unit.localMode, null);
  }
  for (const assignment of assignments) {
    const oldTargets = new Set(assignment.matched.map((unit) => unit.target).filter(Boolean));
    const finalTarget = assignment.target;
    const existingFinal = localFile(prepared.root, finalTarget, `résolution target ${finalTarget ?? "<null>"}`);
    const sourceModes = [...new Set(assignment.mappings
      .filter((mapping) => prepared.newTree.has(mapping.source))
      .map((mapping) => prepared.newTree.get(mapping.source).mode))];
    const retained = assignment.mappings.some((mapping) => mapping.status === "retained" && prepared.newTree.has(mapping.source));
    const resultMode = assignment.result?.mode ?? (retained ? sourceModes[0] : existingFinal.exists ? existingFinal.rawMode : sourceModes[0] ?? 0o644);
    if (assignment.action === "write") {
      addOperation("write", finalTarget, assignment.result.bytes, resultMode, assignment.group.localBlob ?? null, existingFinal.exists ? existingFinal.mode : null, assignment);
    } else if (assignment.action === "map" && assignment.result) {
      addOperation("write", finalTarget, assignment.result.bytes, resultMode, assignment.group.localBlob ?? null, existingFinal.exists ? existingFinal.mode : null, assignment);
    } else if (assignment.action === "delete") {
      for (const oldTarget of oldTargets) {
        const oldFile = localFile(prepared.root, oldTarget, `target ${oldTarget}`);
        if (oldFile.exists) addOperation("delete", oldTarget, null, oldFile.rawMode, assignment.group.localBlob ?? oldFile.blob, oldFile.mode, assignment);
      }
    }
  }
  return { operations };
}

function updatedManifests(prepared, assignments) {
  const { manifests, newTree } = prepared;
  const portEntries = new Map(manifests.portBySource);
  const additionsToOriginal = new Map();
  for (const assignment of assignments) {
    const target = assignment.target;
    const oldTargets = new Set(assignment.matched.map((unit) => unit.target).filter(Boolean));
    for (const oldTarget of oldTargets) {
      if (oldTarget !== target && existsSync(join(prepared.root, oldTarget)) && !manifests.originals.has(oldTarget)) {
        additionsToOriginal.set(oldTarget, { path: oldTarget, reason: `mapping amont déplacé: ${assignment.reason}` });
      }
    }
    for (const source of assignment.sources) {
      if (!newTree.has(source)) {
        portEntries.delete(source);
        continue;
      }
      const old = portEntries.get(source);
      const mapping = assignment.mappings.find((item) => item.source === source);
      if (!mapping && !old) fail(`mapping absent pour la nouvelle source ${source}`);
      portEntries.set(source, {
        ...(old ?? { source }),
        source,
        target,
        status: mapping?.status ?? old?.status,
        reason: mapping?.reason ?? old?.reason,
      });
    }
    if (assignment.action === "keep" && assignment.sources.every((source) => !newTree.has(source))) {
      for (const oldTarget of oldTargets) {
        if (existsSync(join(prepared.root, oldTarget)) && !manifests.originals.has(oldTarget)) {
          additionsToOriginal.set(oldTarget, { path: oldTarget, reason: `source amont supprimée: ${assignment.reason}` });
        }
      }
    }
  }
  for (const source of newTree.keys()) {
    if (!portEntries.has(source)) fail(`source non couverte après résolution: ${source}`);
  }
  const inventoryFiles = [];
  const oldInventoryByPath = new Map(manifests.inventory.files.map((item) => [item.path, item]));
  for (const path of [...oldInventoryByPath.keys(), ...newTree.keys()]) {
    if (!newTree.has(path) || inventoryFiles.some((item) => item.path === path)) continue;
    inventoryFiles.push({ ...(oldInventoryByPath.get(path) ?? { path }), path, git_blob: newTree.get(path).blob });
  }
  const coverageFiles = [];
  for (const path of [...newTree.keys()]) {
    const item = portEntries.get(path);
    if (!item) fail(`source non couverte après résolution: ${path}`);
    coverageFiles.push(item);
  }
  const originals = [...manifests.coverage.original];
  const originalPaths = new Set(originals.map((item) => item.path));
  for (const item of additionsToOriginal.values()) {
    if (!originalPaths.has(item.path)) {
      originals.push(item);
      originalPaths.add(item.path);
    }
  }
  const upstream = { ...manifests.inventory, commit: prepared.newPin, files: inventoryFiles };
  const upstreamPluginManifest = newTree.get(`${manifests.subdirectory}/.cursor-plugin/plugin.json`);
  if (upstreamPluginManifest) {
    const bytes = sourceBytes(prepared.source, upstreamPluginManifest, new Map());
    try {
      const value = JSON.parse(bytes.toString("utf8"));
      if (typeof value.version === "string" && value.version.length > 0) upstream.version = value.version;
    } catch (error) {
      fail(`manifest amont invalide: ${error.message}`);
    }
  }
  return {
    upstream,
    porting: { ...manifests.coverage, commit: prepared.newPin, files: coverageFiles, original: originals },
  };
}

function validateFinalState(prepared, updated, operations) {
  const future = new Map();
  const paths = new Set([
    ...prepared.manifests.groups.keys(),
    ...prepared.manifests.originals.keys(),
    ...updated.porting.files.map((item) => item.target),
    ...updated.porting.original.map((item) => item.path),
    ...operations.map((operation) => operation.target),
  ]);
  paths.delete("<null>");
  for (const target of paths) {
    const file = localFile(prepared.root, target, `cible finale ${target}`);
    if (file.exists) future.set(target, { blob: file.blob, mode: file.mode });
  }
  for (const operation of operations) {
    if (operation.kind === "delete") future.delete(operation.target);
    else future.set(operation.target, { blob: gitBlob(operation.bytes), mode: executableMode(operation.mode) });
  }

  const coverageTargets = new Set();
  for (const item of updated.porting.files) {
    if (item.target === null || item.target === undefined) fail(`cible finale absente dans le mapping: ${item.source}`);
    const target = validateTarget(prepared.root, item.target, `cible finale ${item.source}`);
    if (prepared.originalPaths.has(target)) fail(`cible finale et original[] se chevauchent: ${target}`);
    coverageTargets.add(target);
    const finalFile = future.get(target);
    if (!finalFile) fail(`cible finale absente après résolution: ${target}`);
    if (item.status === "retained") {
      const source = prepared.newTree.get(item.source);
      if (!source) fail(`retained sans source nouvelle: ${item.source}`);
      if (finalFile.blob !== source.blob || finalFile.mode !== source.mode) fail(`retained final différent du source: ${target}`);
    }
  }
  for (const item of updated.porting.original) {
    const path = validateTarget(prepared.root, item.path, "original final");
    if (!future.has(path)) fail(`original final absent après résolution: ${path}`);
    if (coverageTargets.has(path)) fail(`original final chevauche une cible: ${path}`);
  }
  const inventoryPaths = updated.upstream.files.map((item) => item.path);
  if (new Set(inventoryPaths).size !== prepared.newTree.size ||
      inventoryPaths.some((path) => prepared.newTree.get(path)?.blob !== updated.upstream.files.find((item) => item.path === path)?.git_blob)) {
    fail("UPSTREAM final ne couvre pas exactement le nouvel arbre source");
  }
}

function verifyBeforeApply(prepared, assignments, operations) {
  const manifests = validateManifests(prepared.root);
  if (manifests.manifestSha256 !== prepared.plan.manifestSha256) fail("manifestes modifiés depuis la prévisualisation");
  for (const operation of operations) {
    const current = localFile(prepared.root, operation.target, `target ${operation.target}`);
    if (current.blob !== operation.expectedBlob || operation.expectedMode !== null && current.mode !== operation.expectedMode) fail(`cible modifiée depuis la résolution: ${operation.target}`);
  }
  for (const assignment of assignments) {
    const current = localFile(prepared.root, assignment.target, `résolution target ${assignment.target ?? "<null>"}`);
    if ((assignment.group.localBlob ?? null) !== current.blob) fail(`localBlob modifié depuis la résolution: ${assignment.target ?? assignment.sources.join(",")}`);
  }
}

function writeAtomic(path, bytes, mode = 0o644) {
  const directory = dirname(path);
  mkdirSync(directory, { recursive: true });
  const temporary = join(directory, `.sync-upstream-${process.pid}-${Math.random().toString(16).slice(2)}.tmp`);
  try {
    writeFileSync(temporary, bytes, { flag: "wx" });
    chmodSync(temporary, mode);
    renameSync(temporary, path);
  } catch (error) {
    try { if (existsSync(temporary)) unlinkSync(temporary); } catch { /* retain the original filesystem error */ }
    throw error;
  }
}

function applyWithRollback(prepared, assignments) {
  const { operations } = applyAssignments(prepared, assignments);
  const updated = updatedManifests(prepared, assignments);
  validateFinalState(prepared, updated, operations);
  verifyBeforeApply(prepared, assignments, operations);
  const paths = [
    ...operations.map((operation) => join(prepared.root, operation.target)),
    prepared.manifests.upstreamPath,
    prepared.manifests.portingPath,
  ];
  const backups = new Map();
  for (const path of paths) {
    if (backups.has(path)) continue;
    backups.set(path, existsSync(path) ? { bytes: readFileSync(path), mode: statSync(path).mode & 0o777 } : null);
  }
  const createdDirectories = new Set();
  const appliedPaths = new Set();
  try {
    for (const operation of operations) {
      const path = join(prepared.root, operation.target);
      if (operation.kind === "delete") {
        if (existsSync(path)) unlinkSync(path);
        appliedPaths.add(path);
        continue;
      }
      let parent = dirname(path);
      while (!existsSync(parent) && parent !== prepared.root) {
        createdDirectories.add(parent);
        parent = dirname(parent);
      }
      writeAtomic(path, operation.bytes, operation.mode);
      appliedPaths.add(path);
    }
    writeAtomic(prepared.manifests.upstreamPath, Buffer.from(`${JSON.stringify(updated.upstream, null, 2)}\n`), 0o644);
    appliedPaths.add(prepared.manifests.upstreamPath);
    writeAtomic(prepared.manifests.portingPath, Buffer.from(`${JSON.stringify(updated.porting, null, 2)}\n`), 0o644);
    appliedPaths.add(prepared.manifests.portingPath);
  } catch (error) {
    const rollbackErrors = [];
    for (const path of appliedPaths) {
      const backup = backups.get(path);
      try {
        if (backup) writeAtomic(path, backup.bytes, backup.mode);
        else if (existsSync(path)) unlinkSync(path);
      } catch (rollbackError) { rollbackErrors.push(`${path}: ${rollbackError.message}`); }
    }
    for (const directory of [...createdDirectories].sort((a, b) => b.length - a.length)) {
      try { rmdirSync(directory); } catch { /* non-empty or already absent */ }
    }
    if (rollbackErrors.length) fail(`apply annulé; rollback incomplet (${rollbackErrors.join("; ")}): ${error.message}`);
    fail(`apply annulé et restauré: ${error.message}`);
  }
  return { operations: operations.map(({ kind, target }) => ({ kind, target })), updated };
}

export function prepareSync({ root = SCRIPT_ROOT, source, newPin, resolutionPath = null }) {
  const workspace = resolve(root);
  if (!existsSync(workspace) || !lstatSync(workspace).isDirectory()) fail(`racine de dépôt absente: ${root}`);
  if (lstatSync(workspace).isSymbolicLink()) fail(`racine de dépôt liée par symlink: ${root}`);
  if (!source) fail("--source est obligatoire et doit être un checkout Git");
  const pin = sha(newPin, "--to");
  const prepared = buildContext(workspace, source, pin);
  const resolutions = resolutionPath ? validateResolution(prepared, resolutionPath) : null;
  const unresolved = prepared.plan.entries.filter((entry) => entry.requiresResolution).map((entry) => entry.id);
  const conflicts = prepared.plan.entries.filter((entry) => entry.state === "conflict").map((entry) => ({ id: entry.id, hunks: entry.mergeHunks }));
  const unresolvedCount = resolutions
    ? unresolved.filter((id) => !resolutions.assignments.some((assignment) => assignment.matched.some((unit) => unit.id === id))).length
    : unresolved.length;
  return {
    ...prepared,
    unresolved,
    conflicts,
    resolutions,
    output: {
      ...prepared.plan,
      summary: {
        entries: prepared.plan.entries.length,
        changed: prepared.plan.entries.filter((entry) => entry.changed).length,
        unresolved: unresolvedCount,
        conflicts: conflicts.length,
      },
      resolutionTemplate: resolutionTemplate(prepared.plan),
    },
  };
}

export function applySync(prepared) {
  if (!prepared.resolutions) fail("--apply exige --resolutions <fichier.json>");
  const required = prepared.plan.entries.filter((entry) => entry.requiresResolution).map((entry) => entry.id);
  const assigned = new Set(prepared.resolutions.assignments.flatMap((assignment) => assignment.matched.map((unit) => unit.id)));
  const missing = required.filter((id) => !assigned.has(id));
  if (missing.length) fail(`résolutions manquantes: ${missing.join(", ")}`);
  const unresolvedConflicts = prepared.conflicts.filter((conflict) => {
    const assignment = prepared.resolutions.assignments.find((item) => item.matched.some((unit) => unit.id === conflict.id));
    return !assignment || assignment.action === "map" && !assignment.result || !["write", "map"].includes(assignment.action);
  });
  if (unresolvedConflicts.length) fail(`conflits non résolus: ${unresolvedConflicts.map((item) => item.id).join(", ")}`);
  return applyWithRollback(prepared, prepared.resolutions.assignments);
}

function parseArgs(argv) {
  const options = { apply: false, root: SCRIPT_ROOT, source: process.env.CSTACK_UPSTREAM_SOURCE ?? null, newPin: null, resolutions: null };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    const next = () => {
      if (i + 1 >= argv.length) fail(`${arg} exige une valeur`);
      i += 1;
      return argv[i];
    };
    if (arg === "--source") options.source = next();
    else if (arg === "--to") options.newPin = next();
    else if (arg === "--root") options.root = next();
    else if (arg === "--resolutions") options.resolutions = next();
    else if (arg === "--dry-run") { options.apply = false; }
    else if (arg === "--apply") { options.apply = true; }
    else if (arg === "--help" || arg === "-h") options.help = true;
    else fail(`option inconnue: ${arg}`);
  }
  if (options.apply && !options.resolutions) fail("--apply exige --resolutions <fichier.json>");
  return options;
}

function usage() {
  return "usage: bun scripts/sync-upstream.mjs --source <checkout> --to <SHA40> [--dry-run] [--resolutions <json>] | [--apply --resolutions <json>]";
}

export function main(argv = process.argv.slice(2)) {
  try {
    const options = parseArgs(argv);
    if (options.help) {
      process.stdout.write(`${usage()}\n`);
      return 0;
    }
    if (!options.newPin) fail("--to <SHA40> est obligatoire");
    const resolutionPath = options.resolutions ? workspacePath(resolve(options.root), options.resolutions, "--resolutions").absolute : null;
    const prepared = prepareSync({ root: options.root, source: options.source, newPin: options.newPin, resolutionPath });
    if (options.apply) {
      const applied = applySync(prepared);
      process.stdout.write(`${JSON.stringify({ ...prepared.output, applied: true, operations: applied.operations }, null, 2)}\n`);
    } else {
      process.stdout.write(`${JSON.stringify(prepared.output, null, 2)}\n`);
    }
    return 0;
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    process.stderr.write(`sync-upstream: ${message}\n`);
    return 1;
  }
}

if (process.argv[1] && resolve(process.argv[1]) === resolve(fileURLToPath(import.meta.url))) {
  process.exitCode = main();
}

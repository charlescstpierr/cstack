#!/usr/bin/env bun
import { createHash } from "node:crypto";
import { existsSync, readFileSync, readdirSync, realpathSync, statSync } from "node:fs";
import { dirname, isAbsolute, join, relative, resolve } from "node:path";

const PINNED_COMMIT = "889ec4b68fa5aab0e867dad71ec3fdf386ae48f3";
const DIRECT_INVOCATION_ONLY: Record<string, string> = {
  "automate-me": "Cursor automation helper, invoked directly rather than from the router.",
  "bro": "Conversational persona, invoked directly rather than from the router.",
  "create-verification-skill": "Verification-skill factory, invoked directly rather than from the router.",
  "maintain-verification-skill": "Verification-skill maintainer, invoked directly rather than from the router.",
  "make-bot-ui": "Grok bot UI helper, invoked directly rather than from the router.",
  "setup-cstack": "Setup helper, invoked directly rather than from the router.",
};
const DESLOP_EXEMPT: Record<string, string> = {
  "eval.md": "Blind evaluation of candidates; does not commit code or documentation.",
  "investigation.md": "Read-only investigation; produces a cited answer, not a code change.",
  "runtime-forensics.md": "Live-process diagnosis; deliverable is a cited diagnosis, not a fix.",
  "session-pickup.md": "Resume-point reconstruction; routes remaining work to another playbook.",
  "shipping.md": "Merges already-verified PRs; does not author code or documentation commits.",
  "trace-forensics.md": "Read-only artifact diagnosis; does not commit code or documentation.",
  "worktree-cleanup.md": "Worktree and simulator cleanup; does not author code or documentation.",
};
const EXECUTABLES = [
  "scripts/run-tool.sh",
  "skills/cstack/scripts/worktree-audit.sh",
  "skills/cstack/scripts/watch-pr/watch-pr",
  "skills/cstack/scripts/check-plan.mjs",
  "skills/show-me-your-work/scripts/log.sh",
];
const CAPACITY_HEDGES = [
  "when native capacity permits",
  "when capacity permits",
  "when native review is available",
  "when native capacity makes",
];

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function requireValue(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

function json(path: string): Record<string, unknown> {
  const value: unknown = JSON.parse(readFileSync(path, "utf8"));
  requireValue(record(value), `${path}: expected an object`);
  return value;
}

function files(path: string): string[] {
  return readdirSync(path, { withFileTypes: true }).flatMap((entry) => {
    if (["node_modules", ".git", ".cstack", "__pycache__"].includes(entry.name)) return [];
    requireValue(!entry.isSymbolicLink(), `${join(path, entry.name)}: symlinks are not packaged`);
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
  for (const match of text.matchAll(/\b(\d+)\s+skills\b/gi)) {
    requireValue(Number(match[1]) === skills, `${rel}: quoted skill count ${match[1]} does not match ${skills}`);
  }
  for (const match of text.matchAll(/\b(\d+)\s+principles?\b/gi)) {
    requireValue(Number(match[1]) === principles, `${rel}: quoted principle count ${match[1]} does not match ${principles}`);
  }
  for (const match of text.matchAll(/\b(\d+)\s+principes?\b/gi)) {
    requireValue(Number(match[1]) === principles, `${rel}: quoted principle count ${match[1]} does not match ${principles}`);
  }
  for (const match of text.matchAll(/\b(\d+)\s+playbooks?\b/gi)) {
    requireValue(Number(match[1]) === playbooks, `${rel}: quoted playbook count ${match[1]} does not match ${playbooks}`);
  }
  for (const match of text.matchAll(/\b(\d+)\s+fichiers(?:\s+upstream|\s+de provenance(?: pstack)?|\s+source)\b/gi)) {
    requireValue(Number(match[1]) === upstream, `${rel}: quoted upstream file count ${match[1]} does not match ${upstream}`);
  }
  for (const match of text.matchAll(/\b(\d+)\s+upstream files\b/gi)) {
    requireValue(Number(match[1]) === upstream, `${rel}: quoted upstream file count ${match[1]} does not match ${upstream}`);
  }
}

function keys(value: Record<string, unknown>, expected: string[], path: string): void {
  for (const key of Object.keys(value)) {
    requireValue(expected.includes(key), `${path}: unknown skill UI key ${key}`);
  }
  for (const key of expected) {
    requireValue(key in value, `${path}: missing ${key}`);
  }
}

export function validate(root: string): { skills: number; sourceFiles: number } {
  const plugin = join(root, "plugins/cstack");
  const manifest = json(join(plugin, ".codex-plugin/plugin.json"));
  requireValue(manifest.name === "cstack" && manifest.skills === "./skills/", "invalid cstack manifest identity or skill path");
  requireValue(typeof manifest.version === "string" && /^\d+\.\d+\.\d+$/.test(manifest.version), "invalid plugin version");
  requireValue(manifest.license === "MIT", "upstream MIT license must be retained");
  requireValue(record(manifest.author) && typeof manifest.author.name === "string", "missing plugin author");
  requireValue(record(manifest.interface), "missing plugin interface");
  for (const key of ["displayName", "shortDescription", "longDescription", "developerName", "category"]) {
    requireValue(typeof manifest.interface[key] === "string" && manifest.interface[key], `missing interface.${key}`);
  }
  for (const key of ["logo", "composerIcon"]) {
    const value = manifest.interface[key];
    requireValue(typeof value === "string" && value.startsWith("./"), `invalid interface.${key}`);
    const target = resolve(plugin, value);
    requireValue(existsSync(target) && inside(plugin, target), `missing or escaping asset ${value}`);
  }
  const version = manifest.version;
  const evidence = join(root, "docs/evidence", `${version}.json`);
  const changelog = join(root, "CHANGELOG.md");
  const changelogText = existsSync(changelog) ? readFileSync(changelog, "utf8") : "";
  requireValue(
    existsSync(evidence) || new RegExp(`^#{1,3}[^\\n]*\\b${String(version).replace(/\./g, "\\.")}\\b`, "m").test(changelogText),
    `missing changelog or evidence for plugin version ${version}`,
  );
  const marketplace = json(join(root, ".agents/plugins/marketplace.json"));
  requireValue(marketplace.name === "cstack" && Array.isArray(marketplace.plugins) && marketplace.plugins.length === 1, "marketplace must contain only cstack");
  const entry: unknown = marketplace.plugins[0];
  requireValue(record(entry) && entry.name === "cstack" && record(entry.source), "invalid marketplace plugin");
  requireValue(entry.source.source === "local" && entry.source.path === "./plugins/cstack", "marketplace source does not resolve cstack");
  requireValue(record(entry.policy) && entry.policy.installation === "AVAILABLE" && entry.policy.authentication === "ON_INSTALL", "invalid marketplace policy");

  const inventory = json(join(root, "UPSTREAM.json"));
  const coverage = json(join(root, "PORTING.json"));
  requireValue(inventory.commit === PINNED_COMMIT && coverage.commit === inventory.commit, "upstream commit mismatch");
  requireValue(Array.isArray(inventory.files) && Array.isArray(coverage.files), "missing source inventory");
  const sourcePaths = new Set<string>();
  const sourceBlobs = new Map<string, string>();
  const principleTargets = new Set<string>();
  for (const item of inventory.files) {
    requireValue(record(item) && typeof item.path === "string" && typeof item.git_blob === "string", "invalid source item");
    requireValue(item.path.startsWith("pstack/") && /^[a-f0-9]{40}$/.test(item.git_blob) && !sourcePaths.has(item.path), "invalid or duplicate upstream path/blob");
    sourcePaths.add(item.path);
    sourceBlobs.set(item.path, item.git_blob);
  }
  requireValue(sourcePaths.size === 158, "the pinned upstream inventory must contain 158 files");
  const covered = new Set<string>();
  const portTargets = new Set<string>();
  for (const item of coverage.files) {
    requireValue(record(item) && typeof item.source === "string" && typeof item.target === "string", "invalid porting item");
    requireValue(sourcePaths.has(item.source) && !covered.has(item.source), `unknown or repeated source: ${item.source}`);
    requireValue(["ported", "retained", "replaced", "unsupported"].includes(String(item.status)), `invalid status for ${item.source}`);
    requireValue(typeof item.reason === "string" && item.reason.length > 0, `missing porting reason for ${item.source}`);
    const principle = /^pstack\/skills\/principle-(.+)\/SKILL\.md$/.exec(item.source);
    if (principle) {
      const expected = `plugins/cstack/skills/cstack/references/principles/${principle[1]}.md`;
      requireValue(item.target === expected, `${item.source}: principle port target must be ${expected}`);
      principleTargets.add(expected.slice("plugins/cstack/".length));
    }
    const target = resolve(root, item.target);
    requireValue(existsSync(target) && inside(root, target), `missing or escaping port target ${item.target}`);
    if (item.status === "retained") {
      const expected = sourceBlobs.get(item.source);
      const actual = gitBlob(readFileSync(target));
      requireValue(actual === expected, `${item.target}: retained blob ${actual} does not match upstream ${expected}`);
    }
    portTargets.add(item.target);
    covered.add(item.source);
  }
  requireValue(covered.size === sourcePaths.size, "source coverage is incomplete");
  requireValue(principleTargets.size === 23, `expected 23 principle ports, got ${principleTargets.size}`);
  requireValue(Array.isArray(coverage.original), "missing original inventory");
  const originalPaths = new Set<string>();
  for (const item of coverage.original) {
    requireValue(record(item) && typeof item.path === "string" && typeof item.reason === "string" && item.reason.length > 0, "invalid original item");
    requireValue(item.path.startsWith("plugins/cstack/") && !originalPaths.has(item.path), `invalid or duplicate original path: ${item.path}`);
    const target = resolve(root, item.path);
    requireValue(existsSync(target) && inside(plugin, target), `original path does not exist: ${item.path}`);
    originalPaths.add(item.path);
  }

  const additions = json(join(plugin, "sources/matt-pocock.json"));
  requireValue(additions.repository === "https://github.com/mattpocock/skills"
    && additions.commit === "3cca18b368ae95cdbdebbff572ccafa662551015", "Matt source provenance mismatch");
  requireValue(additions.license === "LICENSE-MATT-POCOCK"
    && readFileSync(join(plugin, "LICENSE-MATT-POCOCK"), "utf8").includes("Copyright (c) 2026 Matt Pocock"), "Matt license missing");
  requireValue(Array.isArray(additions.adaptations) && additions.adaptations.length > 0, "missing Matt adaptations");
  const adaptedTargets = new Set<string>();
  for (const item of additions.adaptations) {
    requireValue(record(item) && typeof item.target === "string" && !adaptedTargets.has(item.target), "invalid or duplicate Matt adaptation");
    const target = resolve(plugin, item.target);
    requireValue(existsSync(target) && inside(plugin, target), "missing or escaping Matt adaptation target");
    requireValue(Array.isArray(item.sources) && item.sources.length > 0, "missing Matt source references");
    for (const source of item.sources) {
      requireValue(record(source) && typeof source.path === "string" && source.path.startsWith("skills/")
        && typeof source.sha256 === "string" && /^[a-f0-9]{64}$/.test(source.sha256), "invalid Matt source reference");
    }
    adaptedTargets.add(item.target);
  }
  for (const name of ["clarify", "domain", "horizon", "audit-architecture"]) {
    requireValue(adaptedTargets.has(`skills/${name}/SKILL.md`), `missing provenance for ${name}`);
  }

  const all = files(plugin);
  for (const path of all) {
    const rel = `plugins/cstack/${posix(plugin, path)}`;
    requireValue(portTargets.has(rel) || originalPaths.has(rel), `unaccounted plugin file: ${rel}`);
  }
  const skills = all.filter((path) => path.endsWith("/SKILL.md") && relative(plugin, path).startsWith("skills/"));
  requireValue(!skills.some((path) => relative(join(plugin, "skills"), dirname(path)).startsWith("principle-")), "principle skill entrypoints were moved to references");
  requireValue(skills.length === 29, `expected 29 skill entrypoints, got ${skills.length}`);
  const principleRefs = all.filter((path) => path.endsWith(".md") && relative(plugin, path).startsWith("skills/cstack/references/principles/"));
  requireValue(principleRefs.length === 23, `expected 23 principle references, got ${principleRefs.length}`);
  for (const path of principleRefs) {
    const target = relative(plugin, path);
    requireValue(principleTargets.has(target), `${target}: principle reference is not covered by PORTING.json`);
  }
  const playbooks = all.filter((path) => path.endsWith(".md") && relative(plugin, path).startsWith("skills/cstack/playbooks/"));
  requireValue(playbooks.length === 23, `expected 23 playbooks, got ${playbooks.length}`);
  const playbookDir = join(plugin, "skills/cstack/playbooks");
  for (const key of Object.keys(DESLOP_EXEMPT)) {
    requireValue(
      playbooks.some((path) => relative(playbookDir, path) === key),
      `deslop exemption ${key} does not name an existing playbook`,
    );
  }
  for (const path of playbooks) {
    const text = readFileSync(path, "utf8");
    const rel = posix(root, path);
    requireValue(text.startsWith("### "), `${rel}: playbook must start with a ### title`);
    requireValue(/Follow \[the Codex runtime contract\]\([^)\n]*codex-runtime.md\)/.test(text), `${rel}: playbook missing runtime-contract line`);
    requireValue(/\*\*Reply:\*\*/.test(text), `${rel}: playbook missing Reply block`);
    const name = relative(playbookDir, path);
    if (name in DESLOP_EXEMPT) continue;
    requireValue(text.includes("deslop/SKILL.md"), `${rel}: playbook missing deslop/SKILL.md`);
    requireValue(text.includes("deslop skipped:"), `${rel}: playbook missing deslop skipped:`);
  }
  const mainSkill = readFileSync(join(plugin, "skills/cstack/SKILL.md"), "utf8");
  for (const target of principleTargets) {
    const href = relative("skills/cstack", target);
    requireValue(mainSkill.includes(`](${href})`), `${target}: principle reference is not discoverable from cstack/SKILL.md`);
  }
  const names = new Set<string>();
  const skillUi: Array<{ policyPath: string; name: string; display: string }> = [];
  for (const path of skills) {
    const text = readFileSync(path, "utf8");
    const front = /^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/.exec(text);
    requireValue(front, `${path}: missing frontmatter`);
    const metadata: unknown = Bun.YAML.parse(front[1] ?? "");
    requireValue(record(metadata), `${path}: invalid frontmatter`);
    const name = relative(join(plugin, "skills"), dirname(path));
    requireValue(metadata.name === name && /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(name), `${path}: name must match its skill directory`);
    requireValue(!names.has(name), `duplicate skill ${name}`);
    names.add(name);
    requireValue(typeof metadata.description === "string" && metadata.description.trim().length > 0 && metadata.description.length <= 1024, `${path}: invalid description`);
    requireValue(Object.keys(metadata).every((key) => ["name", "description", "license", "allowed-tools", "metadata"].includes(key)), `${path}: unsupported skill frontmatter`);
    const policyPath = join(dirname(path), "agents/openai.yaml");
    const policy: unknown = Bun.YAML.parse(readFileSync(policyPath, "utf8"));
    requireValue(record(policy) && record(policy.policy) && policy.policy.allow_implicit_invocation === false, `${path}: skill must be explicit-only`);
    requireValue(record(policy.interface) && typeof policy.interface.display_name === "string" && typeof policy.interface.short_description === "string", `${path}: missing skill UI metadata`);
    keys(policy, ["interface", "policy"], posix(root, policyPath));
    keys(policy.interface, ["display_name", "short_description", "default_prompt"], posix(root, policyPath));
    keys(policy.policy, ["allow_implicit_invocation"], posix(root, policyPath));
    skillUi.push({ policyPath: posix(root, policyPath), name, display: policy.interface.display_name });
    const summary = policy.interface.short_description.trim();
    requireValue(summary.length >= 25 && summary.length <= 64, `${path}: skill UI description length must be 25-64 characters`);
    // Catch dangling separators/connectives; prose still needs editorial review.
    requireValue(!/(?:[,;:]|\b(?:a|an|the|and|or|with|for|to|of|in|your))$/i.test(summary), `${path}: truncated skill UI description`);
    requireValue(typeof policy.interface.default_prompt === "string" && policy.interface.default_prompt.includes(`$cstack:${name}`), `${path}: default prompt must use its canonical invocation`);
    requireValue(text.includes("codex-runtime.md"), `${path}: missing runtime contract link`);
  }
  const seenDisplay = new Set<string>();
  for (const item of skillUi) {
    requireValue(!seenDisplay.has(item.display), `duplicate skill display_name ${item.display}`);
    seenDisplay.add(item.display);
  }
  for (const item of skillUi) {
    requireValue(item.display === item.name, `${item.policyPath}: display_name must match its skill directory`);
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
    requireValue(reached.has(name) || name in DIRECT_INVOCATION_ONLY, `${name}: skill is neither reachable from the router nor allowlisted`);
  }

  for (const path of all.filter((path) => path.endsWith(".md"))) {
    const text = readFileSync(path, "utf8");
    // Code examples may contain schematic paths; only actual Markdown links are checked.
    const prose = text.replace(/```[\s\S]*?```/g, "");
    for (const match of prose.matchAll(/!?\[[^\]\n]*\]\(([^\s)]+)(?:\s+"[^"]*")?\)/g)) {
      const href = match[1] ?? "";
      if (/^(?:[a-z][a-z0-9+.-]*:|#)/i.test(href) || href.includes("<")) continue;
      const [filePart, fragment] = href.split("#");
      const part = decodeURIComponent(filePart?.split("?")[0] ?? "");
      const target = part ? resolve(dirname(path), part) : path;
      requireValue(existsSync(target) && inside(plugin, target), `${relative(root, path)}: broken or escaping link ${href}`);
      if (fragment && target.endsWith(".md")) {
        const slugs = headingSlugs(readFileSync(target, "utf8"));
        requireValue(slugs.has(fragment.toLowerCase()), `${relative(root, path)}: missing heading for fragment ${href}`);
      }
    }
    for (const match of prose.matchAll(/`(\.{0,2}[\w./-]*\.(?:md|sh|py|ts|mjs))`/g)) {
      const raw = match[1] ?? "";
      if (!pluginRelativeTick(raw) || workspaceTick(raw)) continue;
      const target = resolve(dirname(path), raw);
      const rel = relative(plugin, target);
      if (rel === ".." || rel.startsWith("../") || isAbsolute(rel)) continue;
      requireValue(existsSync(target), `${posix(root, path)}: unresolved plugin path ${raw}`);
    }
    requireValue(!/\b(?:omx|oh-my-codex)\b/i.test(text), `${path}: forbidden orchestration dependency`);
    requireValue(!/(?:~\/\.cursor\/|subagent_type\s*:|run_in_background\s*:|claude-fable-5|grok-4\.6|\.cursor\/settings\.json)/i.test(text), `${path}: unported Cursor execution contract`);
    requireValue(!/\$cstack:principle-/i.test(text), `${path}: stale principle invocation`);
    requireValue(!/\bprinciple-[a-z0-9-]+\/SKILL\.md/i.test(text), `${path}: stale principle skill reference`);
    for (const phrase of CAPACITY_HEDGES) {
      requireValue(!text.toLowerCase().includes(phrase), `${posix(root, path)}: capacity-hedge regression ${phrase}`);
    }
  }
  for (const rel of EXECUTABLES) {
    const path = join(plugin, rel);
    const mode = statSync(path).mode & 0o777;
    requireValue(mode === 0o755, `plugins/cstack/${rel}: expected mode 0755, got ${mode.toString(8)}`);
  }
  for (const path of [join(root, "README.md"), join(plugin, "README.md"), join(root, "docs/VERIFICATION.md")]) {
    if (!existsSync(path)) continue;
    const text = readFileSync(path, "utf8");
    const rel = posix(root, path);
    let catalog = text;
    if (rel.endsWith("docs/VERIFICATION.md")) {
      const heading = `État ${version}`;
      const section = markdownSection(text, heading);
      requireValue(section, `${rel}: missing current catalog section ## ${heading}`);
      catalog = section;
    }
    assertQuotedCounts(rel, catalog, skills.length, principleRefs.length, playbooks.length, sourcePaths.size);
  }
  const license = readFileSync(join(plugin, "LICENSE"), "utf8");
  requireValue(license.includes("Copyright (c) 2026 Lauren Tan") && license.includes("Permission is hereby granted"), "original license missing");
  return { skills: skills.length, sourceFiles: sourcePaths.size };
}

if (import.meta.main) {
  try {
    const result = validate(resolve(process.argv[2] ?? join(import.meta.dir, "..")));
    console.log(`Validated ${result.skills} skills and ${result.sourceFiles} upstream files.`);
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  }
}

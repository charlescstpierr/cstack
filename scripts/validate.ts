#!/usr/bin/env bun
import { existsSync, readFileSync, readdirSync, realpathSync } from "node:fs";
import { dirname, isAbsolute, join, relative, resolve } from "node:path";

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
  const marketplace = json(join(root, ".agents/plugins/marketplace.json"));
  requireValue(marketplace.name === "cstack" && Array.isArray(marketplace.plugins) && marketplace.plugins.length === 1, "marketplace must contain only cstack");
  const entry: unknown = marketplace.plugins[0];
  requireValue(record(entry) && entry.name === "cstack" && record(entry.source), "invalid marketplace plugin");
  requireValue(entry.source.source === "local" && entry.source.path === "./plugins/cstack", "marketplace source does not resolve cstack");
  requireValue(record(entry.policy) && entry.policy.installation === "AVAILABLE" && entry.policy.authentication === "ON_INSTALL", "invalid marketplace policy");

  const inventory = json(join(root, "UPSTREAM.json"));
  const coverage = json(join(root, "PORTING.json"));
  requireValue(inventory.commit === "27e2a62ff94f9af4b5e68435e41cdceacadb840c" && coverage.commit === inventory.commit, "upstream commit mismatch");
  requireValue(Array.isArray(inventory.files) && Array.isArray(coverage.files), "missing source inventory");
  const sourcePaths = new Set<string>();
  for (const item of inventory.files) {
    requireValue(record(item) && typeof item.path === "string" && typeof item.git_blob === "string", "invalid source item");
    requireValue(item.path.startsWith("pstack/") && /^[a-f0-9]{40}$/.test(item.git_blob) && !sourcePaths.has(item.path), "invalid or duplicate upstream path/blob");
    sourcePaths.add(item.path);
  }
  requireValue(sourcePaths.size === 158, "the pinned upstream inventory must contain 158 files");
  const covered = new Set<string>();
  for (const item of coverage.files) {
    requireValue(record(item) && typeof item.source === "string" && typeof item.target === "string", "invalid porting item");
    requireValue(sourcePaths.has(item.source) && !covered.has(item.source), `unknown or repeated source: ${item.source}`);
    requireValue(["ported", "retained", "replaced", "unsupported"].includes(String(item.status)), `invalid status for ${item.source}`);
    requireValue(typeof item.reason === "string" && item.reason.length > 0, `missing porting reason for ${item.source}`);
    const target = resolve(root, item.target);
    requireValue(existsSync(target) && inside(root, target), `missing or escaping port target ${item.target}`);
    covered.add(item.source);
  }
  requireValue(covered.size === sourcePaths.size, "source coverage is incomplete");

  const all = files(plugin);
  const skills = all.filter((path) => path.endsWith("/SKILL.md") && relative(plugin, path).startsWith("skills/"));
  requireValue(skills.length === 47, `expected 47 skill entrypoints, got ${skills.length}`);
  const names = new Set<string>();
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
    const policy: unknown = Bun.YAML.parse(readFileSync(join(dirname(path), "agents/openai.yaml"), "utf8"));
    requireValue(record(policy) && record(policy.policy) && policy.policy.allow_implicit_invocation === false, `${path}: skill must be explicit-only`);
    requireValue(record(policy.interface) && typeof policy.interface.display_name === "string" && typeof policy.interface.short_description === "string", `${path}: missing skill UI metadata`);
    requireValue(text.includes("codex-runtime.md"), `${path}: missing runtime contract link`);
  }

  for (const path of all.filter((path) => path.endsWith(".md"))) {
    const text = readFileSync(path, "utf8");
    // Code examples may contain schematic paths; only actual Markdown links are checked.
    const prose = text.replace(/```[\s\S]*?```/g, "");
    for (const match of prose.matchAll(/!?\[[^\]\n]*\]\(([^\s)]+)(?:\s+"[^"]*")?\)/g)) {
      const href = match[1] ?? "";
      if (/^(?:[a-z][a-z0-9+.-]*:|#)/i.test(href) || href.includes("<")) continue;
      const part = decodeURIComponent(href.split("#")[0]?.split("?")[0] ?? "");
      const target = resolve(dirname(path), part);
      requireValue(existsSync(target) && inside(plugin, target), `${relative(root, path)}: broken or escaping link ${href}`);
    }
    requireValue(!/\b(?:omx|oh-my-codex)\b/i.test(text), `${path}: forbidden orchestration dependency`);
    requireValue(!/(?:~\/\.cursor\/|subagent_type\s*:|run_in_background\s*:|claude-fable-5|grok-4\.6|\.cursor\/settings\.json)/i.test(text), `${path}: unported Cursor execution contract`);
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

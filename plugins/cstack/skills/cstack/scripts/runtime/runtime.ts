#!/usr/bin/env bun

import { spawn, type ChildProcessWithoutNullStreams } from "node:child_process";
import { constants } from "node:fs";
import {
  access,
  mkdir,
  lstat,
  readFile,
  realpath,
  stat,
  writeFile,
} from "node:fs/promises";
import { basename, delimiter, isAbsolute, join, relative, resolve, sep } from "node:path";
import { loadWorkerContext } from "../worker-context.ts";
import { loadWorkerSkills } from "../worker-skills.ts";

type RuntimeName = "codex-cli" | "claude-code" | "grok" | "cursor-agent";
type PermissionProfile = "read-only" | "workspace-write";
type WorkerStatus = "PASS" | "ISSUES" | "BLOCKED";
type ProviderName = "openai" | "anthropic" | "xai" | "cursor";
type ExecutionStatus =
  | "COMPLETED"
  | "UNSUPPORTED"
  | "AUTH_REQUIRED"
  | "INVALID_OUTPUT"
  | "NONZERO"
  | "TIMEOUT"
  | "CANCELLED"
  | "FAILED";

interface Selection {
  readonly runtime: RuntimeName;
  readonly model?: string;
  readonly reasoning_effort?: string;
}

interface RunRequest {
  readonly selection: Selection;
  readonly brief_file: string;
  readonly context_files?: readonly string[];
  readonly skills?: readonly string[];
  readonly cwd: string;
  readonly output_dir: string;
  readonly permissions: PermissionProfile;
  readonly timeout_ms?: number;
}

interface WorkerCheck {
  readonly command: string;
  readonly result: string;
}

interface WorkerReport {
  readonly status: WorkerStatus;
  readonly summary: string;
  readonly checks: readonly WorkerCheck[];
  readonly findings: readonly string[];
}

interface RuntimeDefinition {
  readonly name: RuntimeName;
  readonly provider: ProviderName;
  readonly binary: string;
  readonly versionArgs: readonly string[];
  readonly helpArgs: readonly string[];
  readonly requiredHelp: readonly string[];
  readonly command: (params: CommandParams) => CommandBuild;
}

interface CommandParams {
  readonly request: RunRequest;
  readonly cwd: string;
  readonly brief: string;
  readonly promptPath: string;
  readonly schemaPath: string;
  readonly schemaText: string;
  readonly lastMessagePath: string;
}

interface CommandBuild {
  readonly argv: readonly string[];
  readonly stdin: string | null;
}

interface CapturedOutput {
  readonly stdout: string;
  readonly stderr: string;
  readonly stdoutTruncated: boolean;
  readonly stderrTruncated: boolean;
}

interface ProcessResult {
  readonly exitCode: number | null;
  readonly signal: NodeJS.Signals | null;
  readonly timedOut: boolean;
  readonly cancelled: boolean;
  readonly durationMs: number;
  readonly captured: CapturedOutput;
}

interface RunResult {
  readonly runtime: RuntimeName;
  readonly provider_requested: ProviderName;
  readonly provider_observed: "unknown";
  readonly selection: Selection;
  readonly context: {
    readonly sha256: string | null;
    readonly files: readonly { readonly path: string; readonly sha256: string }[];
  };
  readonly execution: {
    readonly status: ExecutionStatus;
    readonly version: string | null;
    readonly session_id: string | null;
    readonly exit_code: number | null;
    readonly signal: string | null;
    readonly duration_ms: number;
    readonly stdout_log: string | null;
    readonly stderr_log: string | null;
    readonly stdout_truncated: boolean;
    readonly stderr_truncated: boolean;
    readonly message: string;
  };
  readonly worker: WorkerReport;
}

interface ProbeResult {
  readonly runtime: RuntimeName;
  readonly provider_requested: ProviderName;
  readonly provider_observed: "unknown";
  readonly binary: string;
  readonly available: boolean;
  readonly auth: "unknown";
  readonly version: string | null;
  readonly help: "available" | "missing";
  readonly unsupported: readonly string[];
}

interface Io {
  readonly stdout: (value: string) => void;
  readonly stderr: (value: string) => void;
}

const OUTPUT_LIMIT = 512 * 1024;
const DEFAULT_TIMEOUT_MS = 10 * 60 * 1000;
const MAX_TIMEOUT_MS = 2 * 60 * 60 * 1000;

const WORKER_SCHEMA = {
  type: "object",
  additionalProperties: false,
  required: ["status", "summary", "checks", "findings"],
  properties: {
    status: { enum: ["PASS", "ISSUES", "BLOCKED"] },
    summary: { type: "string" },
    checks: {
      type: "array",
      items: {
        type: "object",
        additionalProperties: false,
        required: ["command", "result"],
        properties: {
          command: { type: "string" },
          result: { type: "string" },
        },
      },
    },
    findings: { type: "array", items: { type: "string" } },
  },
};

const RUNTIMES: Readonly<Record<RuntimeName, RuntimeDefinition>> = {
  "codex-cli": {
    name: "codex-cli",
    provider: "openai",
    binary: "codex",
    versionArgs: ["--version"],
    helpArgs: ["exec", "--help"],
    requiredHelp: ["--config", "--cd", "--sandbox", "--json", "--output-schema", "--output-last-message", "--model", "--ignore-user-config"],
    command: ({ request, cwd, brief, schemaPath, lastMessagePath }) => {
      return {
        argv: [
          "exec",
          "--ignore-user-config",
          "--config",
          "approval_policy=\"never\"",
          ...(request.selection.reasoning_effort ? ["--config", `model_reasoning_effort=${JSON.stringify(request.selection.reasoning_effort)}`] : []),
          "--cd",
          cwd,
          "--sandbox",
          request.permissions,
          "--json",
          "--output-schema",
          schemaPath,
          "--output-last-message",
          lastMessagePath,
          ...(request.selection.model ? ["--model", request.selection.model] : []),
          "-",
        ],
        stdin: brief,
      };
    },
  },
  "claude-code": {
    name: "claude-code",
    provider: "anthropic",
    binary: "claude",
    versionArgs: ["--version"],
    helpArgs: ["--help"],
    requiredHelp: ["--print", "--output-format", "--json-schema", "--permission-mode", "--permission-prompts", "--restricted", "--safe-mode", "--strict-mcp-config", "--mcp-config", "--add-dir", "--tools"],
    command: ({ request, cwd, brief, schemaText }) => {
      const writable = request.permissions === "workspace-write";
      return {
        argv: [
          "--print",
          "--output-format",
          "json",
          "--json-schema",
          schemaText,
          "--permission-mode",
          writable ? "acceptEdits" : "dontAsk",
          "--permission-prompts",
          "none",
          "--safe-mode",
          "--restricted",
          "--strict-mcp-config",
          "--mcp-config",
          "{\"mcpServers\":{}}",
          "--add-dir",
          cwd,
          "--tools",
          writable ? "Read,Glob,Grep,Edit,Write" : "Read,Glob,Grep",
          ...(request.selection.model ? ["--model", request.selection.model] : []),
          ...(request.selection.reasoning_effort ? ["--effort", request.selection.reasoning_effort] : []),
        ],
        stdin: brief,
      };
    },
  },
  "cursor-agent": {
    name: "cursor-agent",
    provider: "cursor",
    binary: "cursor-agent",
    versionArgs: ["--version"],
    helpArgs: ["--help"],
    requiredHelp: ["--print", "--output-format", "--mode", "--sandbox", "--workspace", "--model"],
    command: ({ request, cwd, brief }) => {
      if (request.permissions === "workspace-write") {
        throw new UnsupportedError("cursor-agent: workspace-write non pris en charge sans contrôle d'outils write/shell");
      }
      if (request.selection.reasoning_effort !== undefined) {
        throw new UnsupportedError("cursor-agent: reasoning_effort doit être encodé dans le modèle Cursor si requis");
      }
      return {
        argv: [
          "--print",
          "--output-format",
          "json",
          "--mode",
          "ask",
          "--sandbox",
          "enabled",
          "--workspace",
          cwd,
          ...(request.selection.model ? ["--model", request.selection.model] : []),
          `${brief}\n\nReturn only a JSON object with status, summary, checks, and findings.`,
        ],
        stdin: null,
      };
    },
  },
  grok: {
    name: "grok",
    provider: "xai",
    binary: "grok",
    versionArgs: ["--version"],
    helpArgs: ["--help"],
    requiredHelp: ["--prompt-file", "--cwd", "--output-format", "--json-schema", "--sandbox", "--permission-mode", "--tools", "--allow", "--deny", "--no-subagents", "--model", "--reasoning-effort"],
    command: ({ request, cwd, promptPath, schemaText }) => {
      const writable = request.permissions === "workspace-write";
      return {
      argv: [
        "--cwd",
        cwd,
        "--sandbox",
        writable ? "workspace" : "read-only",
        "--permission-mode",
        "dontAsk",
        "--tools",
        writable ? "read_file,grep,list_dir,edit" : "read_file,grep,list_dir",
        ...(writable ? ["--allow", "Edit"] : []),
        "--deny",
        "MCPTool",
        "--disable-web-search",
        "--no-subagents",
        "--output-format",
        "json",
        "--json-schema",
        schemaText,
        ...(request.selection.model ? ["--model", request.selection.model] : []),
        ...(request.selection.reasoning_effort ? ["--reasoning-effort", request.selection.reasoning_effort] : []),
        "--prompt-file",
        promptPath,
      ],
      stdin: null,
      };
    },
  },
};

class UsageError extends Error {}
class UnsupportedError extends Error {}

function jsonLine(value: unknown): string {
  return `${JSON.stringify(value)}\n`;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function rejectExtraKeys(value: Record<string, unknown>, allowed: readonly string[], label: string): void {
  const extras = Object.keys(value).filter((key) => !allowed.includes(key));
  if (extras.length > 0) {
    throw new UsageError(`${label}: champs inconnus: ${extras.join(", ")}`);
  }
}

function stringField(value: Record<string, unknown>, key: string): string {
  const field = value[key];
  if (typeof field !== "string" || field.trim() !== field || field.length === 0) {
    throw new UsageError(`${key}: chaîne non vide attendue`);
  }
  return field;
}

function optionalStringField(value: Record<string, unknown>, key: string): string | undefined {
  const field = value[key];
  if (field === undefined) {
    return undefined;
  }
  if (typeof field !== "string" || field.trim() !== field || field.length === 0) {
    throw new UsageError(`${key}: chaîne non vide attendue`);
  }
  return field;
}

function parseRuntime(value: unknown): RuntimeName {
  if (value === "codex-cli" || value === "claude-code" || value === "grok" || value === "cursor-agent") {
    return value;
  }
  throw new UsageError("selection.runtime: codex-cli, claude-code, grok ou cursor-agent attendu");
}

function parsePermissions(value: unknown): PermissionProfile {
  if (value === "read-only" || value === "workspace-write") {
    return value;
  }
  throw new UsageError("permissions: read-only ou workspace-write attendu");
}

function parseTimeout(value: unknown): number | undefined {
  if (value === undefined) {
    return undefined;
  }
  if (typeof value !== "number" || !Number.isInteger(value) || value <= 0 || value > MAX_TIMEOUT_MS) {
    throw new UsageError(`timeout_ms: entier entre 1 et ${MAX_TIMEOUT_MS} attendu`);
  }
  return value;
}

function parseRequestJson(raw: string): RunRequest {
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch (error) {
    throw new UsageError(`request: JSON invalide: ${error instanceof Error ? error.message : String(error)}`);
  }
  if (!isRecord(parsed)) {
    throw new UsageError("request: objet attendu");
  }
  rejectExtraKeys(parsed, ["selection", "brief_file", "context_files", "skills", "cwd", "output_dir", "permissions", "timeout_ms"], "request");
  if (!isRecord(parsed.selection)) {
    throw new UsageError("selection: objet attendu");
  }
  rejectExtraKeys(parsed.selection, ["runtime", "model", "reasoning_effort"], "selection");
  const contextFiles = parsed.context_files;
  if (contextFiles !== undefined && (!Array.isArray(contextFiles) || !contextFiles.every((item) => typeof item === "string" && item.trim() === item && item.length > 0))) {
    throw new UsageError("context_files: liste de chemins non vides attendue");
  }
  const skills = parsed.skills;
  if (skills !== undefined && (!Array.isArray(skills) || !skills.every((item) => typeof item === "string"))) {
    throw new UsageError("skills: liste de noms de skills attendue");
  }
  if (parsed.selection.reasoning_effort !== undefined && parsed.selection.model === undefined) throw new UsageError("reasoning_effort exige model");
  if (parsed.selection.model === "inherit-parent") throw new UsageError("inherit-parent est réservé au dispatch natif");
  return {
    selection: {
      runtime: parseRuntime(parsed.selection.runtime),
      model: optionalStringField(parsed.selection, "model"),
      reasoning_effort: optionalStringField(parsed.selection, "reasoning_effort"),
    },
    brief_file: stringField(parsed, "brief_file"),
    context_files: contextFiles,
    skills,
    cwd: stringField(parsed, "cwd"),
    output_dir: stringField(parsed, "output_dir"),
    permissions: parsePermissions(parsed.permissions),
    timeout_ms: parseTimeout(parsed.timeout_ms),
  };
}

async function parseRequestFile(path: string): Promise<RunRequest> {
  const actual = await assertAbsoluteRealFile(path, "request");
  return parseRequestJson(await readFile(actual, "utf8"));
}

function parseWorkerReport(value: unknown): WorkerReport | null {
  if (!isRecord(value)) {
    return null;
  }
  if (Object.keys(value).some((key) => !["status", "summary", "checks", "findings"].includes(key))) return null;
  const status = value.status;
  if (status !== "PASS" && status !== "ISSUES" && status !== "BLOCKED") {
    return null;
  }
  if (typeof value.summary !== "string" || !Array.isArray(value.checks) || !Array.isArray(value.findings)) {
    return null;
  }
  const checks: WorkerCheck[] = [];
  for (const check of value.checks) {
    if (!isRecord(check)) {
      return null;
    }
    if (Object.keys(check).some((key) => !["command", "result"].includes(key))) return null;
    if (typeof check.command !== "string" || typeof check.result !== "string") {
      return null;
    }
    checks.push({ command: check.command, result: check.result });
  }
  if (!value.findings.every((finding) => typeof finding === "string")) {
    return null;
  }
  return {
    status,
    summary: value.summary,
    checks,
    findings: value.findings,
  };
}

async function assertAbsoluteRealFile(path: string, label: string): Promise<string> {
  if (resolve(path) !== path) {
    throw new UsageError(`${label}: chemin absolu requis`);
  }
  const actual = await realpath(path);
  const info = await stat(actual);
  if (!info.isFile()) {
    throw new UsageError(`${label}: fichier régulier requis`);
  }
  return actual;
}

async function assertAbsoluteRealDirectory(path: string, label: string): Promise<string> {
  if (resolve(path) !== path) {
    throw new UsageError(`${label}: chemin absolu requis`);
  }
  const actual = await realpath(path);
  const info = await stat(actual);
  if (!info.isDirectory()) {
    throw new UsageError(`${label}: dossier requis`);
  }
  return actual;
}

async function createFreshOutputDirectory(path: string): Promise<string> {
  if (resolve(path) !== path) {
    throw new UsageError("output_dir: chemin absolu requis");
  }
  try {
    await access(path, constants.F_OK);
    throw new UsageError("output_dir: le dossier ne doit pas préexister");
  } catch (error) {
    if (!(error instanceof UsageError) && isRecord(error) && error.code !== "ENOENT") {
      throw error;
    }
    if (error instanceof UsageError) {
      throw error;
    }
  }
  const parent = await assertAbsoluteRealDirectory(resolve(path, ".."), "output_dir parent");
  const output = resolve(parent, basename(path));
  await mkdir(output, { mode: 0o700 });
  return output;
}

async function executablePath(binary: string): Promise<string | null> {
  if (binary.includes("/")) {
    return null;
  }
  const path = process.env.PATH ?? "";
  for (const directory of path.split(delimiter)) {
    if (directory.length === 0) {
      continue;
    }
    const candidate = resolve(directory, binary);
    try {
      await access(candidate, constants.X_OK);
      return candidate;
    } catch {
    }
  }
  return null;
}

function clippedAppend(current: string, chunk: string, limit: number): { readonly text: string; readonly truncated: boolean } {
  if (current.length >= limit) {
    return { text: current, truncated: true };
  }
  const next = chunk;
  const remaining = limit - current.length;
  if (next.length <= remaining) {
    return { text: current + next, truncated: false };
  }
  return { text: current + next.slice(0, remaining), truncated: true };
}

function killProcessGroup(child: ChildProcessWithoutNullStreams, signal: NodeJS.Signals): void {
  if (child.pid === undefined) {
    return;
  }
  try {
    if (process.platform === "win32") {
      child.kill(signal);
    } else {
      process.kill(-child.pid, signal);
    }
  } catch {
    try {
      child.kill(signal);
    } catch {
    }
  }
}

async function runProcess(params: {
  readonly executable: string;
  readonly argv: readonly string[];
  readonly cwd: string;
  readonly stdin: string | null;
  readonly timeoutMs: number;
}): Promise<ProcessResult> {
  const start = Date.now();
  return await new Promise<ProcessResult>((resolveProcess, reject) => {
    let stdout = "";
    let stderr = "";
    let stdoutTruncated = false;
    let stderrTruncated = false;
    let timedOut = false;
    let cancelled = false;
    let settled = false;
    let stopping: Promise<void> | null = null;
    const child = spawn(params.executable, params.argv, {
      cwd: params.cwd,
      detached: process.platform !== "win32",
      stdio: ["pipe", "pipe", "pipe"],
    });
    const finish = (result: ProcessResult): void => {
      if (settled) {
        return;
      }
      settled = true;
      clearTimeout(timeout);
      process.off("SIGINT", onInterrupt);
      process.off("SIGTERM", onTerminate);
      if (stopping !== null) void stopping.then(() => resolveProcess(result));
      else resolveProcess(result);
    };
    const stopGroup = (signal: NodeJS.Signals): void => {
      if (stopping !== null) return;
      killProcessGroup(child, signal);
      stopping = new Promise((done) => setTimeout(() => {
        killProcessGroup(child, "SIGKILL");
        done();
      }, 500));
    };
    const cancel = (signal: NodeJS.Signals): void => {
      cancelled = true;
      stopGroup(signal);
    };
    child.stdin.on("error", (error) => {
      killProcessGroup(child, "SIGTERM");
      clearTimeout(timeout);
      process.off("SIGINT", onInterrupt);
      process.off("SIGTERM", onTerminate);
      reject(error);
    });
    const onInterrupt = (): void => cancel("SIGINT");
    const onTerminate = (): void => cancel("SIGTERM");
    process.on("SIGINT", onInterrupt);
    process.on("SIGTERM", onTerminate);
    const timeout = setTimeout(() => {
      timedOut = true;
      stopGroup("SIGTERM");
    }, params.timeoutMs);
    child.stdout.setEncoding("utf8");
    child.stderr.setEncoding("utf8");
    child.stdout.on("data", (chunk: string) => {
      const next = clippedAppend(stdout, chunk, OUTPUT_LIMIT);
      stdout = next.text;
      stdoutTruncated = stdoutTruncated || next.truncated;
    });
    child.stderr.on("data", (chunk: string) => {
      const next = clippedAppend(stderr, chunk, OUTPUT_LIMIT);
      stderr = next.text;
      stderrTruncated = stderrTruncated || next.truncated;
    });
    child.on("error", (error) => {
      clearTimeout(timeout);
      process.off("SIGINT", onInterrupt);
      process.off("SIGTERM", onTerminate);
      reject(error);
    });
    child.on("close", (exitCode, signal) => {
      finish({
        exitCode,
        signal,
        timedOut,
        cancelled,
        durationMs: Date.now() - start,
        captured: { stdout, stderr, stdoutTruncated, stderrTruncated },
      });
    });
    if (params.stdin !== null) {
      child.stdin.end(params.stdin);
    } else {
      child.stdin.end();
    }
  });
}

async function commandOutput(executable: string, argv: readonly string[], cwd: string): Promise<ProcessResult> {
  return await runProcess({ executable, argv, cwd, stdin: null, timeoutMs: 10_000 });
}

function unsupported(definition: RuntimeDefinition, missing: readonly string[], version: string | null): ProbeResult {
  return {
    runtime: definition.name,
    provider_requested: definition.provider,
    provider_observed: "unknown",
    binary: definition.binary,
    available: missing.length === 0,
    auth: "unknown",
    version,
    help: missing.length === 0 ? "available" : "missing",
    unsupported: missing,
  };
}

async function probeRuntime(name: RuntimeName): Promise<ProbeResult> {
  const definition = RUNTIMES[name];
  const executable = await executablePath(definition.binary);
  if (executable === null) {
    return unsupported(definition, [`binaire introuvable: ${definition.binary}`], null);
  }
  const versionResult = await commandOutput(executable, definition.versionArgs, process.cwd());
  const helpResult = await commandOutput(executable, definition.helpArgs, process.cwd());
  const helpText = `${helpResult.captured.stdout}\n${helpResult.captured.stderr}`;
  const missing = definition.requiredHelp.filter((flag) => !helpText.includes(flag));
  if (versionResult.exitCode !== 0 || versionResult.timedOut || versionResult.cancelled) missing.push("échec de --version");
  if (helpResult.exitCode !== 0 || helpResult.timedOut || helpResult.cancelled || helpResult.captured.stdoutTruncated) missing.push("échec de --help");
  return unsupported(
    definition,
    missing,
    versionResult.exitCode === 0 ? versionResult.captured.stdout.trim() || versionResult.captured.stderr.trim() || null : null
  );
}

async function requireCapabilities(definition: RuntimeDefinition, executable: string, cwd: string): Promise<void> {
  const helpResult = await commandOutput(executable, definition.helpArgs, cwd);
  const helpText = `${helpResult.captured.stdout}\n${helpResult.captured.stderr}`;
  const missing = definition.requiredHelp.filter((flag) => !helpText.includes(flag));
  if (helpResult.exitCode !== 0 || helpResult.timedOut || helpResult.cancelled || helpResult.captured.stdoutTruncated) missing.push("échec de --help");
  if (missing.length > 0) {
    throw new UnsupportedError(`${definition.name}: drapeaux requis absents: ${missing.join(", ")}`);
  }
}

function authLikely(text: string): boolean {
  return /unauthenticated|not authenticated|authentication (required|failed)|not logged in|login required|please[^\n]*(log in|login|sign in)|run (grok|codex|claude|cursor-agent|agent) (auth )?login/i.test(text);
}

function blocked(summary: string, finding: string): WorkerReport {
  return {
    status: "BLOCKED",
    summary,
    checks: [],
    findings: [finding],
  };
}

function runResult(params: {
  readonly definition: RuntimeDefinition;
  readonly request: RunRequest;
  readonly execution: ExecutionStatus;
  readonly version: string | null;
  readonly sessionId?: string | null;
  readonly process: ProcessResult | null;
  readonly outputDir: string | null;
  readonly message: string;
  readonly worker: WorkerReport;
}): RunResult {
  return {
    runtime: params.definition.name,
    provider_requested: params.definition.provider,
    provider_observed: "unknown",
    selection: params.request.selection,
    context: {
      sha256: null,
      files: [],
    },
    execution: {
      status: params.execution,
      version: params.version,
      session_id: params.sessionId ?? null,
      exit_code: params.process?.exitCode ?? null,
      signal: params.process?.signal ?? null,
      duration_ms: params.process?.durationMs ?? 0,
      stdout_log: params.outputDir ? join(params.outputDir, "stdout.log") : null,
      stderr_log: params.outputDir ? join(params.outputDir, "stderr.log") : null,
      stdout_truncated: params.process?.captured.stdoutTruncated ?? false,
      stderr_truncated: params.process?.captured.stderrTruncated ?? false,
      message: params.message,
    },
    worker: params.worker,
  };
}

function extractSessionId(value: unknown): string | null {
  if (!isRecord(value)) {
    return null;
  }
  for (const key of ["session_id", "sessionId", "conversation_id", "conversationId"]) {
    const field = value[key];
    if (typeof field === "string" && field.length > 0) {
      return field;
    }
  }
  return null;
}

async function parseRuntimeOutput(definition: RuntimeDefinition, stdout: string, lastMessagePath: string): Promise<{ readonly worker: WorkerReport; readonly sessionId: string | null } | null> {
  let raw = stdout;
  if (definition.name === "codex-cli") {
    const file = await lstat(lastMessagePath).catch(() => null);
    if (file === null || !file.isFile() || file.size > OUTPUT_LIMIT * 4) return null;
    raw = await readFile(lastMessagePath, "utf8");
  }
  const trimmed = raw.trim();
  if (trimmed.length === 0) {
    return null;
  }
  let parsed: unknown;
  try {
    parsed = JSON.parse(trimmed);
  } catch {
    return null;
  }
  const sessionId = extractSessionId(parsed);
  if (isRecord(parsed)) {
    if (parsed.is_error === true || (typeof parsed.subtype === "string" && parsed.subtype.startsWith("error")) || parsed.type === "error") {
      return null;
    }
    const structured = parseWorkerReport(parsed.structured_output);
    if (structured !== null) {
      return { worker: structured, sessionId };
    }
  }
  const direct = parseWorkerReport(parsed);
  if (direct !== null) {
    return { worker: direct, sessionId };
  }
  if (isRecord(parsed) && typeof parsed.result === "string") {
    try {
      const worker = parseWorkerReport(JSON.parse(parsed.result));
      return worker === null ? null : { worker, sessionId };
    } catch {
      return null;
    }
  }
  return null;
}

async function runRuntime(request: RunRequest): Promise<RunResult> {
  const definition = RUNTIMES[request.selection.runtime];
  let outputDir: string | null = null;
  let processResult: ProcessResult | null = null;
  let version: string | null = null;
  let contextSha256: string | null = null;
  let skillBundle: Awaited<ReturnType<typeof loadWorkerSkills>> | null = null;
  let contextFiles: readonly { readonly path: string; readonly sha256: string }[] = [];
  const finish = async (result: RunResult): Promise<RunResult> => {
    const enriched = {
      ...result,
      skills: { names: request.skills ?? [], sha256: skillBundle?.sha256 ?? null, files: skillBundle?.files ?? [] },
      context: {
        sha256: contextSha256,
        files: contextFiles,
      },
    };
    if (outputDir !== null) {
      await writeFile(join(outputDir, "result.json"), JSON.stringify(enriched, null, 2));
    }
    return enriched;
  };
  try {
    const briefPath = await assertAbsoluteRealFile(request.brief_file, "brief_file");
    const cwd = await assertAbsoluteRealDirectory(request.cwd, "cwd");
    const outputParent = await assertAbsoluteRealDirectory(resolve(request.output_dir, ".."), "output_dir parent");
    const relativeOutput = relative(cwd, resolve(outputParent, basename(request.output_dir)));
    if (request.permissions === "workspace-write" && relativeOutput !== ".." && !relativeOutput.startsWith(`..${sep}`) && !isAbsolute(relativeOutput)) {
      throw new UsageError("output_dir doit être hors du worktree inscriptible du worker");
    }
    outputDir = await createFreshOutputDirectory(request.output_dir);
    if (process.platform === "win32") throw new UnsupportedError("groupes de processus Windows non pris en charge ; utiliser un hôte POSIX");
    skillBundle = await loadWorkerSkills({ names: request.skills ?? [], pluginRoot: process.env.CSTACK_PLUGIN_ROOT ?? resolve(import.meta.dir, "../../../..") });
    await writeFile(join(outputDir, "skills-snapshot.json"), JSON.stringify(skillBundle, null, 2));
    const context = await loadWorkerContext({ briefFile: briefPath, contextFiles: request.context_files ?? [] });
    contextSha256 = context.sha256;
    contextFiles = context.files;
    await writeFile(join(outputDir, "context-snapshot.json"), JSON.stringify(context, null, 2));
    const promptPath = join(outputDir, "worker-prompt.txt");
    const workerPrompt = `${skillBundle.text}\n\nTASK BRIEF AND SHARED CONTEXT\n${context.prompt}`;
    await writeFile(promptPath, workerPrompt);
    const executable = await executablePath(definition.binary);
    if (executable === null) {
      return await finish(runResult({
        definition,
        request,
        execution: "UNSUPPORTED",
        version,
        process: null,
        outputDir,
        message: `binaire introuvable: ${definition.binary}`,
        worker: blocked("Runtime indisponible.", `binaire introuvable: ${definition.binary}`),
      }));
    }
    const versionResult = await commandOutput(executable, definition.versionArgs, cwd);
    if (versionResult.exitCode !== 0 || versionResult.timedOut || versionResult.cancelled) throw new UnsupportedError("échec de --version ; aucun worker lancé");
    version = versionResult.captured.stdout.trim() || versionResult.captured.stderr.trim() || null;
    await requireCapabilities(definition, executable, cwd);
    const schemaPath = join(outputDir, "worker-report.schema.json");
    const schemaText = JSON.stringify(WORKER_SCHEMA);
    const lastMessagePath = join(outputDir, "last-message.json");
    await writeFile(schemaPath, JSON.stringify(WORKER_SCHEMA, null, 2));
    const built = definition.command({ request, cwd, brief: workerPrompt, promptPath, schemaPath, schemaText, lastMessagePath });
    processResult = await runProcess({
      executable,
      argv: built.argv,
      cwd,
      stdin: built.stdin,
      timeoutMs: request.timeout_ms ?? DEFAULT_TIMEOUT_MS,
    });
    await writeFile(join(outputDir, "stdout.log"), processResult.captured.stdout);
    await writeFile(join(outputDir, "stderr.log"), processResult.captured.stderr);
    if (processResult.timedOut) {
      return await finish(runResult({
        definition,
        request,
        execution: "TIMEOUT",
        version,
        process: processResult,
        outputDir,
        message: "processus arrêté après timeout",
        worker: blocked("Runtime arrêté par timeout.", "timeout"),
      }));
    }
    if (processResult.cancelled) {
      return await finish(runResult({
        definition,
        request,
        execution: "CANCELLED",
        version,
        process: processResult,
        outputDir,
        message: "processus annulé par signal externe",
        worker: blocked("Runtime annulé.", "CANCELLED"),
      }));
    }
    if (processResult.captured.stdoutTruncated) {
      return await finish(runResult({
        definition,
        request,
        execution: "INVALID_OUTPUT",
        version,
        process: processResult,
        outputDir,
        message: "stdout tronqué; rapport worker non fiable",
        worker: blocked("Runtime terminé avec stdout tronqué.", "STDOUT_TRUNCATED"),
      }));
    }
    const combined = `${processResult.captured.stdout}\n${processResult.captured.stderr}`;
    if (processResult.exitCode !== 0) {
      const execution = authLikely(combined) ? "AUTH_REQUIRED" : "NONZERO";
      return await finish(runResult({
        definition,
        request,
        execution,
        version,
        process: processResult,
        outputDir,
        message: execution === "AUTH_REQUIRED" ? "authentification requise par le CLI" : `sortie non nulle: ${processResult.exitCode}`,
        worker: blocked("Runtime terminé sans rapport worker valide.", execution),
      }));
    }
    const worker = await parseRuntimeOutput(definition, processResult.captured.stdout, lastMessagePath);
    if (worker === null) {
      return await finish(runResult({
        definition,
        request,
        execution: "INVALID_OUTPUT",
        version,
        process: processResult,
        outputDir,
        message: "sortie JSON worker invalide",
        worker: blocked("Runtime terminé sans JSON worker valide.", "INVALID_OUTPUT"),
      }));
    }
    return await finish(runResult({
      definition,
      request,
      execution: "COMPLETED",
      version,
      sessionId: worker.sessionId,
      process: processResult,
      outputDir,
      message: "rapport worker valide",
      worker: worker.worker,
    }));
  } catch (error) {
    const execution = error instanceof UnsupportedError ? "UNSUPPORTED" : "FAILED";
    return await finish(runResult({
      definition,
      request,
      execution,
      version,
      process: processResult,
      outputDir,
      message: error instanceof Error ? error.message : String(error),
      worker: blocked("Runtime non exécuté.", error instanceof Error ? error.message : String(error)),
    }));
  }
}

function parseProbeRuntime(value: string | undefined): RuntimeName {
  if (value === undefined) {
    throw new UsageError("probe exige un runtime");
  }
  return parseRuntime(value);
}

function requestArg(argv: readonly string[]): string {
  if (argv.length !== 2 || argv[0] !== "--request" || !argv[1]) {
    throw new UsageError("run exige --request <chemin JSON>");
  }
  return argv[1];
}

export async function main(argv: readonly string[], io: Io = { stdout: (value) => process.stdout.write(value), stderr: (value) => process.stderr.write(value) }): Promise<number> {
  try {
    const [command, ...rest] = argv;
    if ((command === "--help" || command === "-h") && rest.length === 0) {
      io.stdout("runtime.ts probe <codex-cli|claude-code|cursor-agent|grok>\nruntime.ts run --request <chemin JSON absolu>\nChamps : selection, brief_file, context_files?, skills?, cwd, output_dir, permissions, timeout_ms?\n");
      return 0;
    }
    if (command === "probe") {
      if (rest.length !== 1) throw new UsageError("probe exige exactement un runtime");
      io.stdout(jsonLine(await probeRuntime(parseProbeRuntime(rest[0]))));
      return 0;
    }
    if (command === "run") {
      const result = await runRuntime(await parseRequestFile(requestArg(rest)));
      io.stdout(jsonLine(result));
      return result.execution.status === "COMPLETED" ? 0 : 2;
    }
    throw new UsageError("utilisation: runtime.ts probe <runtime> | run --request <JSON>");
  } catch (error) {
    io.stderr(`runtime: ${error instanceof Error ? error.message : String(error)}\n`);
    return 64;
  }
}

if (import.meta.main) {
  const status = await main(process.argv.slice(2));
  process.exit(status);
}

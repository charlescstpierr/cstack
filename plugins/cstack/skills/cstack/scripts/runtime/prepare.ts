import { createHash } from "node:crypto";
import { realpath } from "node:fs/promises";
import { isAbsolute } from "node:path";
import { loadWorkerContext } from "../worker-context.ts";
import { loadWorkerSkills } from "../worker-skills.ts";

type Scalar = string | boolean;
export interface T3Selection {
  readonly runtime: "t3";
  readonly providerInstanceId: string;
  readonly model: string;
  readonly options: Readonly<Record<string, Scalar>>;
}

function record(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}
function text(value: unknown): value is string {
  return typeof value === "string" && value.trim() === value && value.length > 0;
}
function identifier(value: unknown): value is string {
  return typeof value === "string" && /^[\x21-\x7e]+$/.test(value);
}
function strings(value: unknown): value is string[] {
  return Array.isArray(value) && value.every(text);
}
function hash(value: string): string {
  return createHash("sha256").update(value).digest("hex");
}
export function parseT3Selection(value: unknown): T3Selection {
  if (!record(value) || value.runtime !== "t3"
      || Object.keys(value).sort().join(",") !== "model,options,providerInstanceId,runtime"
      || !identifier(value.providerInstanceId) || value.providerInstanceId === "inherit-parent" || !identifier(value.model) || value.model === "inherit-parent" || !record(value.options)) {
    throw new Error("BLOCKED: sélection t3 exacte requise; aucune interprétation CLI");
  }
  const options: Record<string, Scalar> = Object.create(null);
  for (const [key, option] of Object.entries(value.options)) {
    if (!identifier(key) || !(typeof option === "string" || typeof option === "boolean")) {
      throw new Error("BLOCKED: option scalaire non secrète requise");
    }
    options[key] = option;
  }
  return { runtime: "t3", providerInstanceId: value.providerInstanceId, model: value.model, options };
}

type T3Target = Omit<T3Selection, "runtime">;
interface CoordinatorScope extends T3Target {
  readonly threadId: string;
  readonly projectId: string;
  readonly link: string;
  readonly runtimeMode: string;
  readonly interactionMode: string;
}
interface T3Binding {
  readonly coordinatorScope: CoordinatorScope;
  readonly catalogSha256: string;
  readonly target: T3Target;
}
function exactKeys(value: Record<string, unknown>, keys: string[]): boolean {
  return Object.keys(value).sort().join(",") === keys.sort().join(",");
}
function parseTarget(value: unknown): T3Target {
  if (!record(value) || !exactKeys(value, ["providerInstanceId", "model", "options"])) {
    throw new Error("BLOCKED: binding target exact requis");
  }
  const { runtime: _, ...target } = parseT3Selection({ ...value, runtime: "t3" });
  return target;
}
function sameTarget(left: T3Target, right: T3Target): boolean {
  return left.providerInstanceId === right.providerInstanceId && left.model === right.model
    && Object.keys(left.options).length === Object.keys(right.options).length
    && Object.entries(left.options).every(([key, value]) => Object.hasOwn(right.options, key) && right.options[key] === value);
}
function parseBinding(value: unknown, selection: T3Selection): T3Binding {
  if (!record(value) || !exactKeys(value, ["coordinatorScope", "catalogSha256", "target"])
      || typeof value.catalogSha256 !== "string" || !/^[a-f0-9]{64}$/.test(value.catalogSha256)) {
    throw new Error("BLOCKED: binding du preflight requis");
  }
  const scope = value.coordinatorScope;
  if (!record(scope) || !exactKeys(scope, ["threadId", "projectId", "link", "providerInstanceId", "model", "options", "runtimeMode", "interactionMode"])
      || !identifier(scope.threadId) || !identifier(scope.projectId) || !identifier(scope.link)
      || !identifier(scope.runtimeMode) || !identifier(scope.interactionMode)) {
    throw new Error("BLOCKED: binding coordinatorScope complet requis");
  }
  const coordinator = parseTarget({ providerInstanceId: scope.providerInstanceId, model: scope.model, options: scope.options });
  const target = parseTarget(value.target);
  if (!sameTarget(target, selection)) throw new Error("BLOCKED: binding target différent de selection");
  return { coordinatorScope: { ...coordinator, threadId: scope.threadId, projectId: scope.projectId,
    link: scope.link, runtimeMode: scope.runtimeMode, interactionMode: scope.interactionMode },
    catalogSha256: value.catalogSha256, target };
}

// Availability belongs to models.py preflight. This function prepares data and never dispatches.
export async function prepareT3(raw: unknown, pluginRoot: string) {
  if (!record(raw) || Object.keys(raw).some((key) => ![
    "selection", "binding", "brief_file", "context_files", "skills", "skill_references", "scope", "acceptance", "evidence", "snapshot", "transport_limit_bytes",
  ].includes(key))) throw new Error("BLOCKED: request préparation invalide");
  const selection = parseT3Selection(raw.selection);
  const binding = parseBinding(raw.binding, selection);
  if (!text(raw.brief_file) || !isAbsolute(raw.brief_file)) {
    throw new Error("BLOCKED: brief_file exige un chemin absolu");
  }
  if (!strings(raw.context_files) || !strings(raw.skills)
      || !strings(raw.skill_references) || !text(raw.scope) || !text(raw.acceptance) || !text(raw.evidence)
      || typeof raw.transport_limit_bytes !== "number" || !Number.isSafeInteger(raw.transport_limit_bytes)
      || raw.transport_limit_bytes <= 0 || raw.transport_limit_bytes > 1024 * 1024) {
    throw new Error("BLOCKED: brief, périmètre, critères, preuves et limite transport mesurée requis");
  }
  if (!Array.isArray(raw.snapshot) || raw.snapshot.length !== raw.context_files.length + 1) {
    throw new Error("BLOCKED: snapshot exact des fichiers du brief requis");
  }
  const context = await loadWorkerContext({ briefFile: raw.brief_file, contextFiles: raw.context_files });
  for (const [index, file] of context.files.entries()) {
    const expected: unknown = raw.snapshot[index];
    if (!record(expected) || typeof expected.path !== "string" || !isAbsolute(expected.path)
        || await realpath(expected.path) !== file.path || expected.sha256 !== file.sha256) {
      throw new Error("BLOCKED: snapshot différent de la source figée");
    }
  }
  const skills = await loadWorkerSkills({ names: raw.skills, pluginRoot, host: "t3",
    skillReferences: [...new Set([...raw.skill_references, "cstack/references/runtime/t3.md"])] });
  const prompt = [skills.text,
    `\nSCOPE\n${raw.scope}\nACCEPTANCE\n${raw.acceptance}\nEXPECTED EVIDENCE\n${raw.evidence}\n`, context.prompt].join("\n");
  const bytes = Buffer.byteLength(prompt);
  if (bytes > raw.transport_limit_bytes) throw new Error(`BLOCKED: brief ${bytes} octets dépasse transport ${raw.transport_limit_bytes}; aucune troncature`);
  return { status: "prepared", selection, binding, prompt, bytes, sha256: hash(prompt), context, skills,
    snapshot: context.files, dispatch: "coordinator-only", host_evidence: "not-attested-by-helper" };
}

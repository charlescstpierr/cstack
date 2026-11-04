import { createHash } from "node:crypto";
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
function strings(value: unknown): value is string[] {
  return Array.isArray(value) && value.every(text);
}
function hash(value: string): string {
  return createHash("sha256").update(value).digest("hex");
}
export function parseT3Selection(value: unknown): T3Selection {
  if (!record(value) || value.runtime !== "t3"
      || Object.keys(value).sort().join(",") !== "model,options,providerInstanceId,runtime"
      || !text(value.providerInstanceId) || value.providerInstanceId === "inherit-parent" || !text(value.model) || value.model === "inherit-parent" || !record(value.options)) {
    throw new Error("BLOCKED: sélection t3 exacte requise; aucune interprétation CLI");
  }
  const options: Record<string, Scalar> = Object.create(null);
  for (const [key, option] of Object.entries(value.options)) {
    if (!text(key) || !(typeof option === "string" || typeof option === "boolean")) {
      throw new Error("BLOCKED: option scalaire non secrète requise");
    }
    options[key] = option;
  }
  return { runtime: "t3", providerInstanceId: value.providerInstanceId, model: value.model, options };
}

// Availability belongs to models.py preflight. This function prepares data and never dispatches.
export async function prepareT3(raw: unknown, pluginRoot: string) {
  if (!record(raw) || Object.keys(raw).some((key) => ![
    "selection", "brief_file", "context_files", "skills", "skill_references", "scope", "acceptance", "evidence", "snapshot", "transport_limit_bytes",
  ].includes(key))) throw new Error("BLOCKED: request préparation invalide");
  const selection = parseT3Selection(raw.selection);
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
    if (!record(expected) || expected.path !== file.path || expected.sha256 !== file.sha256) {
      throw new Error("BLOCKED: snapshot différent de la source figée");
    }
  }
  const skills = await loadWorkerSkills({ names: raw.skills, pluginRoot,
    skillReferences: [...new Set([...raw.skill_references, "cstack/references/runtime/t3.md"])] });
  const prompt = [skills.text,
    `\nSCOPE\n${raw.scope}\nACCEPTANCE\n${raw.acceptance}\nEXPECTED EVIDENCE\n${raw.evidence}\n`, context.prompt].join("\n");
  const bytes = Buffer.byteLength(prompt);
  if (bytes > raw.transport_limit_bytes) throw new Error(`BLOCKED: brief ${bytes} octets dépasse transport ${raw.transport_limit_bytes}; aucune troncature`);
  return { status: "prepared", selection, prompt, bytes, sha256: hash(prompt), context, skills,
    snapshot: context.files, dispatch: "coordinator-only", host_evidence: "not-attested-by-helper" };
}

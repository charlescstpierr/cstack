import { parsePrNumber, type PrContext } from "./types.ts";

export interface LandingRevision {
  readonly context: PrContext;
  readonly headRefOid: string;
  readonly baseRefName: string;
  readonly baseRefOid: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function object(value: unknown, label: string): Record<string, unknown> {
  if (!isRecord(value)) throw new Error(`${label} doit être un objet`);
  return value;
}

export function text(value: unknown, label: string): string {
  if (typeof value !== "string" || value.length === 0)
    throw new Error(`${label} doit être une chaîne non vide`);
  return value;
}

export function parseContext(value: unknown): PrContext {
  const fields = object(value, "contexte PR");
  const owner = text(fields.owner, "owner");
  const repo = text(fields.repo, "repo");
  if (!/^[\w.-]+$/.test(owner) || !/^[\w.-]+$/.test(repo))
    throw new Error("owner et repo doivent être des noms de dépôt individuels");
  return { owner, repo, number: parsePrNumber(fields.number) };
}

export function parseLandingRevision(
  value: unknown,
  context?: PrContext
): LandingRevision {
  const fields = object(value, "révision d'atterrissage");
  return {
    context: context ?? parseContext(fields.context),
    headRefOid: text(fields.headRefOid, "headRefOid"),
    baseRefName: text(fields.baseRefName, "baseRefName"),
    baseRefOid: text(fields.baseRefOid, "baseRefOid"),
  };
}

export function sameLandingRevision(
  first: LandingRevision,
  second: LandingRevision
): boolean {
  return (
    first.context.owner.toLowerCase() === second.context.owner.toLowerCase() &&
    first.context.repo.toLowerCase() === second.context.repo.toLowerCase() &&
    first.context.number === second.context.number &&
    first.headRefOid === second.headRefOid &&
    first.baseRefName === second.baseRefName &&
    first.baseRefOid === second.baseRefOid
  );
}

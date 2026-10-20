import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { lstat, readFile, readlink, realpath } from "node:fs/promises";
import { isAbsolute, join, resolve } from "node:path";

interface Patch { readonly head: string; readonly digest: string }
interface Evidence { readonly path: string; readonly digest: string }
type Target = {readonly kind:"session"} | {readonly kind:"unit"; readonly id:string} | {readonly kind:"pr"; readonly pr:number};
type Disposition = "open" | "fixed" | "refuted" | "deferred";
interface Finding {
  readonly id:string;
  readonly mechanism:string;
  readonly paths:readonly string[];
  readonly severity:"blocking" | "security" | "non-blocking";
  readonly origin:"initial" | "introduced" | "outside";
  readonly disposition:Disposition;
}
interface Strategy { readonly reason:string; readonly files:readonly Evidence[]; readonly digest:string }
type TestResult = { readonly kind:"affected" | "integration"; readonly command:string; readonly evidence:Evidence } &
  ({readonly result:"pass" | "fail" | "blocked"} | {readonly result:"not-required"; readonly reason:string});
interface Outcome { readonly id:string; readonly kind:Disposition; readonly reason:string; readonly evidence:Evidence }
type Progress = {readonly kind:"none"} | {readonly kind:"verified"; readonly summary:string; readonly evidence:Evidence};
interface Decision { readonly kind:"continue" | "complete" | "blocked" | "replan"; readonly reason:string }
interface ReviewResult {
  readonly reviewer:string;
  readonly base:string;
  readonly patch:Patch;
  readonly tests:readonly TestResult[];
  readonly outcomes:readonly Outcome[];
  readonly findings:readonly Finding[];
  readonly progress:Progress;
  readonly decision:Decision;
  readonly recordedAt:string;
}
interface Reservation {
  readonly id:string;
  readonly author:string;
  readonly before:Patch;
  readonly strategy:Strategy;
  readonly reservedAt:string;
}
type Attempt = Reservation & ({readonly kind:"reserved"} | {readonly kind:"reviewed"; readonly result:ReviewResult});
export interface ReviewLoop {
  readonly id:string;
  readonly repo:string;
  readonly target:Target;
  readonly limit:number;
  readonly source:string;
  readonly initial:Patch;
  readonly initialFindings:readonly Finding[];
  readonly findings:readonly Finding[];
  readonly attempts:readonly Attempt[];
}
export interface ReviewView {
  readonly id:string;
  readonly ready:boolean;
  readonly reasons:readonly string[];
  readonly used:number;
  readonly limit:number;
  readonly source:string;
  readonly base:string;
  readonly patch:Patch;
  readonly files:readonly string[];
  readonly findings:readonly Finding[];
  readonly followUps:readonly Finding[];
  readonly decision:Decision | null;
}
export interface ReviewApi {
  readonly open:(input:unknown)=>Promise<ReviewLoop>;
  readonly attempt:(input:unknown)=>Promise<Attempt>;
  readonly record:(input:unknown)=>Promise<ReviewView>;
  readonly check:(id:string)=>Promise<ReviewView>;
}

function isObject(value:unknown):value is Record<string,unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}
function object(value:unknown): Record<string,unknown> {
  if (!isObject(value)) throw new Error("review: objet requis");
  return value;
}
function text(value:unknown):string {
  if (typeof value !== "string" || !value.trim() || value.includes("\0")) throw new Error("review: texte non vide requis");
  return value;
}
function positive(value:unknown):number {
  if (typeof value !== "number" || !Number.isSafeInteger(value) || value <= 0) throw new Error("review: limite ou PR positive requise");
  return value;
}
function list(value:unknown):readonly unknown[] {
  if (!Array.isArray(value)) throw new Error("review: liste requise");
  return value;
}
function choice<const T extends string>(value:unknown, choices:readonly T[]):T {
  const found = choices.find(item=>item===value);
  if (found === undefined) throw new Error(`review: valeur attendue parmi ${choices.join(", ")}`);
  return found;
}
function unique(values:readonly string[]):void {
  if (new Set(values).size !== values.length) throw new Error("review: identifiants dupliqués");
}
function digest(value:string | Buffer):string { return createHash("sha256").update(value).digest("hex"); }
function evidence(value:unknown):Evidence {
  const row = object(value); return {path:text(row.path),digest:text(row.digest)};
}
function patch(value:unknown):Patch {
  const row = object(value); return {head:text(row.head),digest:text(row.digest)};
}
function target(value:unknown):Target {
  const row = object(value);
  switch (row.kind) {
    case "session": return {kind:"session"};
    case "unit": return {kind:"unit",id:text(row.id)};
    case "pr": return {kind:"pr",pr:positive(row.pr)};
    default: throw new Error("review: rattachement session, unit ou pr requis");
  }
}
function finding(value:unknown, origin?:Finding["origin"]):Finding {
  const row = object(value);
  const paths = list(row.paths).map(text);
  if (!paths.length || paths.some(path=>isAbsolute(path) || path.split("/").some(part=>part===".." || part==="." || part===""))) throw new Error("review: chemins relatifs explicites requis");
  const parsed:Finding = {id:text(row.id),mechanism:text(row.mechanism),paths,
    severity:choice(row.severity,["blocking","security","non-blocking"]),
    origin:origin ?? choice(row.origin,["initial","introduced","outside"]),
    disposition:origin ? "open" : choice(row.disposition,["open","fixed","refuted","deferred"])};
  if (parsed.disposition === "deferred" && parsed.severity !== "non-blocking") throw new Error("review: défaut bloquant ou sécurité non reportable");
  return parsed;
}
function decision(value:unknown):Decision {
  const row = object(value); return {kind:choice(row.kind,["continue","complete","blocked","replan"]),reason:text(row.reason)};
}
function progress(value:unknown):Progress {
  const row = object(value);
  if (row.kind === "none") return {kind:"none"};
  if (row.kind !== "verified") throw new Error("review: progression none ou verified requise");
  return {kind:"verified",summary:text(row.summary),evidence:evidence(row.evidence)};
}
function outcome(value:unknown):Outcome {
  const row = object(value); return {id:text(row.id),kind:choice(row.kind,["open","fixed","refuted","deferred"]),reason:text(row.reason),evidence:evidence(row.evidence)};
}
function testResult(value:unknown):TestResult {
  const row = object(value), kind = choice(row.kind,["affected","integration"]);
  const common = {kind,command:text(row.command),evidence:evidence(row.evidence)};
  if (row.result === "not-required" && kind === "integration") return {...common,result:"not-required",reason:text(row.reason)};
  return {...common,result:choice(row.result,["pass","fail","blocked"])};
}
function result(value:unknown):ReviewResult {
  const row = object(value);
  return {reviewer:text(row.reviewer),base:text(row.base),patch:patch(row.patch),tests:list(row.tests).map(testResult),outcomes:list(row.outcomes).map(outcome),
    findings:list(row.findings).map(item=>finding(item)),progress:progress(row.progress),decision:decision(row.decision),recordedAt:text(row.recordedAt)};
}
function attempt(value:unknown):Attempt {
  const row = object(value), strategy = object(row.strategy);
  const reservation = {id:text(row.id),author:text(row.author),before:patch(row.before),strategy:{reason:text(strategy.reason),files:list(strategy.files).map(evidence),digest:text(strategy.digest)},reservedAt:text(row.reservedAt)};
  if (row.kind === "reserved") return {...reservation,kind:"reserved"};
  if (row.kind === "reviewed") return {...reservation,kind:"reviewed",result:result(row.result)};
  throw new Error("review: tentative invalide");
}
export function parseReviews(value:unknown):readonly ReviewLoop[] {
  const data = object(value);
  if (data.schema !== 1) throw new Error("review: schema 1 requis");
  const loops = list(data.reviews).map(value=>{
    const row = object(value);
    const loop:ReviewLoop = {id:text(row.id),repo:text(row.repo),target:target(row.target),limit:positive(row.limit),source:text(row.source),initial:patch(row.initial),
      initialFindings:list(row.initialFindings).map(item=>finding(item)),findings:list(row.findings).map(item=>finding(item)),attempts:list(row.attempts).map(attempt)};
    unique(loop.attempts.map(item=>item.id)); unique(loop.findings.map(item=>item.id));
    if (loop.attempts.length > loop.limit || loop.attempts.slice(0,-1).some(item=>item.kind==="reserved")) throw new Error("review: historique de tentatives incohérent");
    return loop;
  });
  unique(loops.map(loop=>loop.id)); return loops;
}
function git(repo:string, ...args:string[]):string {
  return execFileSync("git",["-C",repo,...args],{encoding:"utf8",maxBuffer:64*1024*1024,stdio:["ignore","pipe","pipe"]});
}
const PATHS = ["--", ".", ":(exclude).cstack"];
async function capture(repo:string):Promise<Patch> {
  const head = git(repo,"rev-parse","HEAD").trim();
  const index = git(repo,"diff","--no-ext-diff","--binary","--cached","HEAD",...PATHS);
  const worktree = git(repo,"diff","--no-ext-diff","--binary",...PATHS);
  const untracked = git(repo,"ls-files","--others","--exclude-standard","-z",...PATHS).split("\0").filter(Boolean).sort();
  const files = await Promise.all(untracked.map(async path=>{
    const absolute = join(repo,path), stat = await lstat(absolute);
    if (!stat.isFile() && !stat.isSymbolicLink()) throw new Error(`review: fichier non vérifiable ${path}`);
    return [path,stat.mode,digest(stat.isSymbolicLink() ? await readlink(absolute) : await readFile(absolute))];
  }));
  return {head,digest:digest(JSON.stringify([head,index,worktree,files]))};
}
async function snapshot(repo:string):Promise<Patch> {
  const first = await capture(repo), second = await capture(repo);
  if (!samePatch(first,second)) throw new Error("review: patch modifié pendant la capture; réessayer");
  return second;
}
function samePatch(left:Patch,right:Patch):boolean { return left.head===right.head && left.digest===right.digest; }
function lastReview(loop:ReviewLoop):ReviewResult | null {
  for (let index=loop.attempts.length-1;index>=0;index--) {
    const item = loop.attempts[index]; if (item?.kind==="reviewed") return item.result;
  }
  return null;
}
function unresolved(item:Finding):boolean { return item.disposition === "open"; }
function targeted(item:Finding):boolean { return item.origin !== "outside" && unresolved(item); }
async function proof(path:unknown):Promise<Evidence> {
  const absolute = await realpath(text(path));
  const bytes = await readFile(absolute);
  if (!bytes.toString("utf8").trim()) throw new Error(`review: preuve vide ${absolute}`);
  return {path:absolute,digest:digest(bytes)};
}
async function currentEvidence(result:ReviewResult):Promise<boolean> {
  const files = [...result.tests.map(item=>item.evidence),...result.outcomes.map(item=>item.evidence),...(result.progress.kind==="verified" ? [result.progress.evidence] : [])];
  for (const file of files) {
    try { if ((await proof(file.path)).digest !== file.digest) return false; } catch { return false; }
  }
  return true;
}
function changedFiles(repo:string,base:string,head:string):readonly string[] {
  return [...new Set([
    git(repo,"diff","--name-only","-z",base,head,...PATHS),
    git(repo,"diff","--name-only","-z","HEAD",...PATHS),
    git(repo,"diff","--cached","--name-only","-z",...PATHS),
    git(repo,"ls-files","--others","--exclude-standard","-z",...PATHS),
  ].flatMap(value=>value.split("\0").filter(Boolean)))];
}
function assertAncestry(repo:string,base:string,head:string):void {
  try { git(repo,"merge-base","--is-ancestor",base,head); }
  catch { throw new Error("review: head hors ascendance; replanification requise"); }
}
export async function reviewView(loop:ReviewLoop):Promise<ReviewView> {
  const current = await snapshot(loop.repo), previous = lastReview(loop), base = previous?.patch.head ?? loop.initial.head;
  assertAncestry(loop.repo,base,current.head);
  const last = loop.attempts.at(-1), reasons:string[] = [];
  if (!previous || last?.kind==="reserved") reasons.push("revue terminée requise");
  if (previous && !samePatch(previous.patch,current)) reasons.push("preuve de patch périmée");
  if (previous && !(await currentEvidence(previous))) reasons.push("preuve de test ou de constat périmée");
  if (loop.findings.some(item=>targeted(item) || (unresolved(item) && item.severity!=="non-blocking"))) reasons.push("constats non résolus");
  if (!previous || previous.tests.some(item=>item.result!=="pass" && item.result!=="not-required") || !["affected","integration"].every(kind=>previous.tests.some(item=>item.kind===kind))) reasons.push("tests affectés et intégration requis non vérifiés");
  if (previous?.decision.kind!=="complete") reasons.push("décision de fin requise");
  return {id:loop.id,ready:!reasons.length,reasons,used:loop.attempts.length,limit:loop.limit,source:loop.source,base,patch:current,
    files:changedFiles(loop.repo,base,current.head),findings:loop.findings,followUps:loop.findings.filter(item=>item.origin==="outside" && unresolved(item)),decision:previous?.decision ?? null};
}
export async function openReview(input:unknown):Promise<ReviewLoop> {
  const row = object(input), repo = await realpath(git(text(row.repo),"rev-parse","--show-toplevel").trim());
  const findings = list(row.findings).map(item=>finding(item,"initial")); unique(findings.map(item=>item.id));
  if (!findings.length) throw new Error("review: constat initial requis");
  return {id:text(row.id),repo,target:target(row.target),limit:positive(row.limit),source:text(row.source),initial:await snapshot(repo),initialFindings:findings,findings,attempts:[]};
}
export function reviewId(input:unknown):string { return text(object(input).id); }
export function findReview(loops:readonly ReviewLoop[],id:string):ReviewLoop {
  const loop = loops.find(loop=>loop.id===id);
  if (!loop) throw new Error(`review: boucle ${id} introuvable`);
  return loop;
}
export function sameOpening(left:ReviewLoop,right:ReviewLoop):boolean {
  return left.repo===right.repo && left.limit===right.limit && left.source===right.source && JSON.stringify(left.target)===JSON.stringify(right.target) && JSON.stringify(left.initialFindings)===JSON.stringify(right.initialFindings);
}
function strategyContent(files:readonly Evidence[]):string {
  return digest(JSON.stringify([...new Set(files.map(file=>file.digest))].sort()));
}
export async function reserveAttempt(loop:ReviewLoop,input:unknown):Promise<{readonly loop:ReviewLoop;readonly attempt:Attempt}> {
  const row = object(input), id = text(row.attempt), author = text(row.author), raw = object(row.strategy);
  const kinds:string[] = [], files:Evidence[] = [];
  for (const item of list(raw.files)) {
    const file = object(item); kinds.push(choice(file.kind,["brief","context","design"])); files.push(await proof(file.path));
  }
  if (!files.length) throw new Error("review: contenu de stratégie requis");
  unique(kinds);
  const strategy:Strategy = {reason:text(raw.reason),files,digest:strategyContent(files)};
  const existing = loop.attempts.find(item=>item.id===id);
  if (existing) {
    if (existing.author!==author || strategyContent(existing.strategy.files)!==strategy.digest) throw new Error("review: tentative réutilisée avec un autre contrat");
    return {loop,attempt:existing};
  }
  if (loop.attempts.length >= loop.limit) throw new Error(`review: limite ${loop.limit} atteinte (${loop.source})`);
  const previous = loop.attempts.at(-1);
  if (previous?.kind==="reserved") throw new Error("review: terminer la tentative réservée avant dispatch");
  const before = await snapshot(loop.repo);
  const staleCompletion = previous?.kind==="reviewed" && previous.result.decision.kind==="complete" && (!samePatch(previous.result.patch,before) || !(await currentEvidence(previous.result)));
  if (!staleCompletion && (!loop.findings.some(targeted) || (previous?.kind==="reviewed" && previous.result.decision.kind!=="continue"))) throw new Error("review: boucle terminée ou bloquée; replanifier explicitement");
  if (previous?.kind==="reviewed" && previous.result.progress.kind==="none" && strategyContent(previous.strategy.files)===strategy.digest) throw new Error("review: changer le contenu de la stratégie après absence de progression");
  assertAncestry(loop.repo,lastReview(loop)?.patch.head ?? loop.initial.head,before.head);
  const reserved:Attempt = {id,author,before,strategy,reservedAt:new Date().toISOString(),kind:"reserved"};
  return {loop:{...loop,attempts:[...loop.attempts,reserved]},attempt:reserved};
}
export async function recordReview(loop:ReviewLoop,input:unknown):Promise<ReviewLoop> {
  const row = object(input), id = text(row.attempt), reviewer = text(row.reviewer), reserved = loop.attempts.at(-1);
  if (!reserved || reserved.id!==id || reserved.kind!=="reserved") throw new Error("review: tentative réservée requise");
  if (reviewer===reserved.author) throw new Error("review: reviewer indépendant requis");
  const expected = await reviewView(loop), supplied = patch(row.patch);
  if (text(row.base)!==expected.base || !samePatch(supplied,expected.patch)) throw new Error("review: rapport périmé; relire le patch courant depuis le dernier head relu");
  const outcomes:Outcome[] = [];
  for (const item of list(row.outcomes)) { const raw = object(item); outcomes.push(outcome({...raw,evidence:await proof(raw.evidence)})); }
  unique(outcomes.map(item=>item.id));
  for (const item of loop.findings.filter(targeted)) if (!outcomes.some(outcome=>outcome.id===item.id)) throw new Error(`review: constat ouvert omis ${item.id}`);
  for (const item of outcomes) {
    const original = loop.findings.find(finding=>finding.id===item.id);
    if (!original) throw new Error(`review: constat inconnu ${item.id}`);
    if (item.kind==="deferred" && original.severity!=="non-blocking") throw new Error("review: défaut bloquant ou sécurité non reportable");
  }
  const findings = loop.findings.map(item=>({...item,disposition:outcomes.find(outcome=>outcome.id===item.id)?.kind ?? item.disposition}));
  const added:Finding[] = [];
  for (const item of list(row.findings)) {
    const raw = object(item);
    if (typeof raw.introduced!=="boolean") throw new Error("review: origine introduced explicite requise");
    const next = finding(raw,raw.introduced ? "introduced" : "outside"); added.push(next); findings.push(next);
  }
  unique(findings.map(item=>item.id));
  const tests:TestResult[] = [];
  for (const item of list(row.tests)) { const raw = object(item); tests.push(testResult({...raw,evidence:await proof(raw.evidence)})); }
  if (!tests.length) throw new Error("review: tests exécutés requis");
  const rawProgress = object(row.progress);
  const measured = progress(rawProgress.kind==="verified" ? {...rawProgress,evidence:await proof(rawProgress.evidence)} : rawProgress);
  const selected = decision(row.decision);
  if (selected.kind==="continue" && loop.attempts.length>=loop.limit) throw new Error("review: décision explicite de blocage ou replanification requise à la limite");
  const completed:ReviewResult = {reviewer,base:expected.base,patch:expected.patch,tests,outcomes,findings:added,progress:measured,decision:selected,recordedAt:new Date().toISOString()};
  const next:ReviewLoop = {...loop,findings,attempts:[...loop.attempts.slice(0,-1),{...reserved,kind:"reviewed",result:completed}]};
  const view = await reviewView(next);
  if (!samePatch(expected.patch,view.patch)) throw new Error("review: patch périmé pendant l'enregistrement");
  if (selected.kind==="complete" && !view.ready) throw new Error(`review: branche non prête: ${view.reasons.join("; ")}`);
  return next;
}

export function targetsUnit(loop:ReviewLoop,unit:{readonly id:string;readonly pr:string}):boolean {
  return loop.target.kind==="unit" ? loop.target.id===unit.id : loop.target.kind==="pr" && String(loop.target.pr)===unit.pr;
}
export function targetsPr(loop:ReviewLoop,pr:string,units:readonly {readonly id:string;readonly pr:string}[]):boolean {
  const target = loop.target;
  return target.kind==="pr" ? String(target.pr)===pr : target.kind==="unit" && units.some(unit=>unit.id===target.id && unit.pr===pr);
}
export async function requireReviewed(loops:readonly ReviewLoop[],sha?:string):Promise<void> {
  for (const loop of loops) {
    const view = await reviewView(loop);
    if (!view.ready || (sha !== undefined && view.patch.head!==sha)) throw new Error(`review: boucle ${loop.id} non prête: ${view.reasons.join("; ") || "SHA différent"}`);
  }
}

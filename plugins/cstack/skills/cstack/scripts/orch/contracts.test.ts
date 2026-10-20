import { afterEach, expect, it } from "bun:test";
import { createHash } from "node:crypto";
import { mkdtemp, mkdir, readFile, rename, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { loadHorizon, horizonBrief } from "./horizon.ts";
import { openStore } from "./store.ts";

const roots: string[] = [];
const block = (value: unknown): string => `\`\`\`horizon\n${JSON.stringify(value)}\n\`\`\`\n`;
const digest = (value: unknown): string => createHash("sha256").update(JSON.stringify(value)).digest("hex");
async function fixture() {
  const root = await mkdtemp(join(tmpdir(), "horizon-contracts-")); roots.push(root);
  await mkdir(join(root, "units")); await mkdir(join(root, "tickets"));
  await writeFile(join(root, "tickets/01-format.md"), "---\nstatus: resolved\n---\n## Réponse\nMontants en cents; devise CAD.\n");
  const contracts = [
    {id:"amount", producer:"A", decision:"tickets/01-format.md", declaration:"export function amount(cents: number): number", values:["amount(0) === 0", "negative cents throw RangeError"]},
    {id:"label", producer:"B", decision:"tickets/01-format.md", declaration:"export function label(cents: number): string", values:['currency = "CAD"', 'label(123) === "CAD 1.23"']},
  ];
  const spec = {schema:1, status:"ready", goal:"Afficher des montants CAD", out_of_scope:["Aucune conversion de devise"], context:["README.md"], decisions:["tickets/01-format.md"], contracts,
    requirements:[{id:"positive",description:"123 cents donnent CAD 1.23"},{id:"negative",description:"Les montants négatifs sont refusés"}], units:["units/A.md","units/B.md","units/C.md"]};
  const units = ["A","B","C"].map((id,index) => ({id, goal:`Livrer ${id}`, blocked_by:index ? [String.fromCharCode(64+index)] : [], acceptance:["Montant conforme au contrat"], writable:[`src/${id}.ts`], forbidden:["Aucune publication"], context:["README.md"], verify:[`bun test tests/${id}.test.ts`], produces:index < 2 ? [contracts[index]!.id] : [], consumes:index ? [{id:contracts[index-1]!.id,expectedDigest:digest(contracts[index-1])}] : [], tests:[{name:`${id} formats amount`,requirements:["positive","negative"],input:"123 and -1 cents",assertions:['123 gives "CAD 1.23"',"-1 throws RangeError"],command:`bun test tests/${id}.test.ts`,success:"exit 0; both assertions pass"}]}));
  const save = async () => { await writeFile(join(root,"spec.md"),block(spec)); for (const unit of units) await writeFile(join(root,`units/${unit.id}.md`),block(unit)); };
  await save();
  return {root,spec,contracts,units,save,path:join(root,"spec.md")};
}
afterEach(async () => { for (const root of roots.splice(0)) await rm(root,{recursive:true,force:true}); });

it("transmits exact canonical contracts and observable tests through three bounded briefs",async () => {
  const f=await fixture(); const definition=await loadHorizon(f.path);
  for(const unit of definition.units) {
    const brief=horizonBrief(definition,unit);
    expect(brief).toContain("both assertions pass");
    expect(brief).toContain("Les montants négatifs sont refusés");
  }
  expect(horizonBrief(definition,definition.units[1]!)).toContain("negative cents throw RangeError");
  expect(horizonBrief(definition,definition.units[1]!)).toContain(f.contracts[0]!.declaration);
  expect(horizonBrief(definition,definition.units[2]!)).toContain(f.contracts[1]!.declaration);
});

for(const failure of ["signature","value","unknown-contract","unknown-producer","wrong-producer","missing-dependency","unknown-decision","uncovered","unknown-requirement","empty-assertions","missing-tests","duplicate-contract","missing-contracts"] as const) {
  it(`rejects ${failure} before import writes execution rows`,async () => {
    const f=await fixture();
    switch(failure) {
      case "signature": f.contracts[0]!.declaration="export function amount(text: string): number"; break;
      case "value": f.contracts[0]!.values=["negative cents return zero"]; break;
      case "unknown-contract": f.units[1]!.consumes[0]!.id="absent"; break;
      case "unknown-producer": f.contracts[0]!.producer="absent"; break;
      case "wrong-producer": f.units[1]!.produces.push("amount"); break;
      case "missing-dependency": f.units[1]!.blocked_by=[]; break;
      case "unknown-decision": f.contracts[0]!.decision="tickets/missing.md"; break;
      case "uncovered": f.spec.requirements.push({id:"rounding",description:"Arrondir les fractions"}); break;
      case "unknown-requirement": f.units[1]!.tests[0]!.requirements.push("missing"); break;
      case "empty-assertions": f.units[1]!.tests[0]!.assertions=[]; break;
      case "missing-tests": f.units[1]!.tests=[]; break;
      case "duplicate-contract": f.contracts.push({...f.contracts[0]!}); break;
      case "missing-contracts": Reflect.deleteProperty(f.spec,"contracts"); break;
    }
    await f.save(); const store=openStore(join(f.root,"store"));
    try {await store.init(); await expect(store.handoff.import(f.path)).rejects.toThrow(/Horizon:/); expect(await store.units.list()).toEqual([]);}
    finally {await store.close();}
  });
}

it("rejects a changed contract after import while preserving prior evidence",async () => {
  const f=await fixture(); const store=openStore(join(f.root,"store"));
  try {
    await store.init(); await store.handoff.import(f.path);
    await store.ledger.record({pr:1,sha:"old-head",verdict:"unit-test-verified",evidence:"proof.md",verifier:"reviewer"});
    const before=await readFile(join(f.root,"store/ledger.tsv"),"utf8");
    f.contracts[0]!.values.push("maximum = 100"); f.units[1]!.consumes[0]!.expectedDigest=digest(f.contracts[0]); await f.save();
    await expect(store.handoff.ready(f.root)).rejects.toThrow("dérive");
    expect(await readFile(join(f.root,"store/ledger.tsv"),"utf8")).toBe(before);
  } finally {await store.close();}
});

it("allows a transitive consumer and excludes unrelated contracts from its brief", async () => {
  const f = await fixture();
  f.units[2]!.consumes.push({id: "amount", expectedDigest: digest(f.contracts[0])});
  await f.save();
  const definition = await loadHorizon(f.path);
  expect(horizonBrief(definition, definition.units[2]!)).toContain(f.contracts[0]!.declaration);
  expect(horizonBrief(definition, definition.units[0]!)).not.toContain(f.contracts[1]!.declaration);
});

it("rejects a test command omitted from the unit verification commands", async () => {
  const f = await fixture();
  f.units[1]!.tests[0]!.command = "bun test another-suite";
  await f.save();
  await expect(loadHorizon(f.path)).rejects.toThrow("absente de verify");
});

it("preserves exact whitespace in canonical values and their consumer pin", async () => {
  const f = await fixture();
  f.contracts[0]!.values = ["  exact literal value  "];
  f.units[1]!.consumes[0]!.expectedDigest = digest(f.contracts[0]);
  await f.save();
  const definition = await loadHorizon(f.path);
  const encoded = /^Valeurs JSON: (.+)$/m.exec(horizonBrief(definition, definition.units[1]!))?.[1];
  expect(JSON.parse(encoded ?? "null")).toEqual(["  exact literal value  "]);
});

it("rejects a phantom spec.md decision when the loaded spec has another name", async () => {
  const f = await fixture();
  f.contracts[0]!.decision = "spec.md";
  f.units[1]!.consumes[0]!.expectedDigest = digest(f.contracts[0]);
  await f.save();
  const renamed = join(f.root, "approved-plan.md");
  await rename(f.path, renamed);
  await expect(loadHorizon(renamed)).rejects.toThrow("décision inconnue");
});

it("accepts the actual loaded spec as the contract decision source", async () => {
  const f = await fixture();
  f.contracts[0]!.decision = "approved-plan.md";
  f.units[1]!.consumes[0]!.expectedDigest = digest(f.contracts[0]);
  await f.save();
  const renamed = join(f.root, "approved-plan.md");
  await rename(f.path, renamed);
  const definition = await loadHorizon(renamed);
  expect(horizonBrief(definition, definition.units[1]!)).toContain("décision approved-plan.md");
  expect(Object.keys(definition.sources)).toContain(renamed);
});

it("round-trips multiline values without merging distinct array boundaries", async () => {
  const f = await fixture();
  const encodedValues: string[] = [];
  for (const values of [["a\nb", "c"], ["a", "b\nc"]]) {
    f.contracts[0]!.values = values;
    f.units[1]!.consumes[0]!.expectedDigest = digest(f.contracts[0]);
    await f.save();
    const definition = await loadHorizon(f.path);
    const brief = horizonBrief(definition, definition.units[0]!);
    const encoded = /^Valeurs JSON: (.+)$/m.exec(brief)?.[1];
    expect(JSON.parse(encoded ?? "null")).toEqual(values);
    encodedValues.push(encoded ?? "");
  }
  expect(encodedValues[0]).not.toBe(encodedValues[1]);
});

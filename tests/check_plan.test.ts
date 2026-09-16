import { expect, test } from "bun:test";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

const root = resolve(import.meta.dir, "..");
const checker = join(root, "plugins/cstack/skills/cstack/scripts/check-plan.mjs");

function example(): string {
  const playbook = readFileSync(join(root, "plugins/cstack/skills/cstack/playbooks/multi-phase-plan.md"), "utf8");
  const template = playbook.split("````markdown\n")[1]?.split("````")[0];
  if (!template) throw new Error("Modèle de plan fourni manquant");
  return template.replace(/<[^>]+>/g, "exemple")
    .replace(/(\*\*Vérifier, réel\.\*\*[^\n]*)/, (line) => (line.includes("dans la capacité native") ? line : `${line} dans la capacité native`))
    .replace(/^- \[ \] Voie (\d+)\..*$/gm, (_, number) => `- [ ] Voie ${number}. Exécuter le scénario. Enregistrer \`evidence/lane-${number}.log\`. Réussit quand le résultat observé correspond au contrat.`);
}

// Les libellés anglais restent des entrées valides pour les plans existants.
function legacy(plan: string): string {
  const labels = [
    ["Comment lire ceci", "How to read this"],
    ["Liste de contrôle du programme", "Program checklist"],
    ["Fermer le programme", "Close the program"],
    ["Démarrer le programme", "Start the program"],
    ["Attribuer les responsables", "Assign owners"],
    ["Traiter chaque PR", "Handle each PR"],
    ["Vérifier et livrer chaque PR", "Verify and deliver each PR"],
    ["Démarrer chaque voie réelle", "Boot each live lane"],
    ["Une case est une unité de travail", "One box is one unit of work"],
    ["nomme sa preuve", "names its evidence"],
    ["Coche une case seulement quand cette preuve existe", "Check a box only when that evidence exists"],
    ["Les tests seuls ne vérifient pas une PR. Chaque PR exige des preuves unitaires, en situation réelle et de performance.", "Tests alone do not verify a PR. Each PR requires unit, live, and performance evidence."],
    ["Dépend de.", "Depends on."], ["Fichiers.", "Files."], ["Construire.", "Build."],
    ["Tu vois.", "You see."], ["Vérifier, unitaire.", "Verify, unit."],
    ["Vérifier, réel.", "Verify, live."], ["Vérifier, performance.", "Verify, performance."],
    ["Barrière de revue.", "Review gate."], ["Livrer.", "Deliver."],
    ["dans la capacité native", "within native capacity"], ["Voie ", "Lane "],
    ["Enregistrer", "Save"], ["Réussit quand", "Pass when"],
    ["Métrique.", "Metric."], ["Sonde.", "Probe."], ["Référence.", "Baseline."], ["Règle.", "Rule."],
    ["autorisation", "authorization"], ["Annexe", "Appendix"],
    ["Preuve du prototype", "Prototype evidence"], ["Aucune.", "None."],
  ];
  for (const [french, english] of labels) plan = plan.replaceAll(french, english);
  return plan;
}

for (const [language, convert] of [["français", (plan: string) => plan], ["anglais existant", legacy]] as const) {
  test(`le vérificateur accepte le plan ${language}, ses preuves et les exclusions justifiées`, () => {
    const dir = mkdtempSync(join(tmpdir(), "cstack-plan-"));
    try {
      const path = join(dir, "plan.md");
      const plan = example().replace(/Voie 10\..*/, "Voie 10. n/a: aucun dixième comportement distinct applicable.");
      for (const valid of [plan, plan.replace(/\*\*Barrière de revue\.\*\*[\s\S]*?(?=\*\*Livrer\.\*\*)/, "**Barrière de revue.** Aucune.\n\n")]) {
        writeFileSync(path, convert(valid));
        const result = Bun.spawnSync(["bun", checker, path]);
        expect({ code: result.exitCode, errors: result.stderr.toString() }).toEqual({ code: 0, errors: "" });
      }
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  test(`le vérificateur refuse les preuves manquantes dans le plan ${language}`, () => {
    const dir = mkdtempSync(join(tmpdir(), "cstack-plan-"));
    try {
      const path = join(dir, "plan.md");
      for (const invalid of [
        example().replace("**Vérifier, unitaire.**", "**Absent.**"),
        example().replace(/Voie 10\..*/, "Voie 10. n/a:"),
        example().replace("**Livrer.**", "**Absent.**"),
        example().replace(/- \[ \].*vidéo.*\n/, ""),
      ]) {
        writeFileSync(path, convert(invalid));
        const result = Bun.spawnSync(["bun", checker, path]);
        expect(result.exitCode).toBe(1);
        expect(result.stderr.toString().length).toBeGreaterThan(0);
      }
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  test(`les diagnostics du plan ${language} nomment seulement le repère manquant`, () => {
    const dir = mkdtempSync(join(tmpdir(), "cstack-plan-"));
    try {
      const path = join(dir, "plan.md");
      for (const missing of [
        "Les tests seuls ne vérifient pas une PR. Chaque PR exige des preuves unitaires, en situation réelle et de performance.",
        "### Démarrer le programme",
      ]) {
        writeFileSync(path, convert(example().replace(missing, "")));
        const result = Bun.spawnSync(["bun", checker, path]);
        expect(result.exitCode).toBe(1);
        const errors = result.stderr.toString().trim().split("\n");
        expect(errors).toHaveLength(1);
        expect(errors[0]).toContain(convert(missing));
      }
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });
}

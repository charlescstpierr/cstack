import { test, expect } from "bun:test";
import { chmodSync, cpSync, existsSync, mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { validate } from "../scripts/validate.ts";

test("le paquet charge 29 skills et rejette les distributions dangereuses ou incomplètes", () => {
  const root = resolve(import.meta.dir, "..");
  const copy = mkdtempSync(join(tmpdir(), "cstack-package-"));
  try {
    for (const path of ["plugins", ".agents", "UPSTREAM.json", "PORTING.json"]) {
      cpSync(join(root, path), join(copy, path), {
        recursive: true,
        filter: (source) => !source.split("/").some((part) => ["node_modules", "__pycache__"].includes(part)),
      });
    }
    const manifest = JSON.parse(readFileSync(join(copy, "plugins/cstack/.codex-plugin/plugin.json"), "utf8"));
    mkdirSync(join(copy, "docs/evidence"), { recursive: true });
    const evidenceSrc = join(root, "docs/evidence", `${manifest.version}.json`);
    if (existsSync(evidenceSrc)) cpSync(evidenceSrc, join(copy, "docs/evidence", `${manifest.version}.json`));
    else writeFileSync(join(copy, "docs/evidence", `${manifest.version}.json`), "{}\n");
    if (existsSync(join(root, "CHANGELOG.md"))) cpSync(join(root, "CHANGELOG.md"), join(copy, "CHANGELOG.md"));
    if (existsSync(join(root, "docs/VERIFICATION.md"))) {
      mkdirSync(join(copy, "docs"), { recursive: true });
      cpSync(join(root, "docs/VERIFICATION.md"), join(copy, "docs/VERIFICATION.md"));
    }
    if (existsSync(join(root, "README.md"))) cpSync(join(root, "README.md"), join(copy, "README.md"));
    expect(validate(copy)).toEqual({ skills: 29, sourceFiles: 158 });
    const cases = [
      ["plugins/cstack/.codex-plugin/plugin.json", (text: string) => text.replace('"name": "cstack"', '"name": "other"'), /identité du manifeste/],
      ["plugins/cstack/skills/cstack/agents/openai.yaml", (text: string) => text.replace("allow_implicit_invocation: false", "allow_implicit_invocation: true"), /invocation explicite/],
      ["plugins/cstack/skills/cstack/agents/openai.yaml", (text: string) => text.replace("$cstack:cstack", "$cstack"), /invocation canonique/],
      ["plugins/cstack/skills/cstack/agents/openai.yaml", (text: string) => text.replace(/short_description: .*/, 'short_description: "Organiser le travail et le vérifier avec"'), /description d’interface du skill tronquée/],
      ["plugins/cstack/skills/cstack/agents/openai.yaml", (text: string) => text.replace(/short_description: .*/, `short_description: "${"x".repeat(65)}"`), /longueur de la description d’interface du skill/],
      ["plugins/cstack/skills/cstack/agents/openai.yaml", (text: string) => text.replace("interface:", "unexpected: 1\ninterface:"), /clé inconnue de l’interface du skill/],
      ["plugins/cstack/skills/cstack/agents/openai.yaml", (text: string) => text.replace('display_name: "cstack"', 'display_name: "router"'), /display_name doit correspondre/],
      ["plugins/cstack/skills/architect/agents/openai.yaml", (text: string) => text.replace('display_name: "architect"', 'display_name: "cstack"'), /display_name de skill dupliqué/],
      ["plugins/cstack/skills/cstack/SKILL.md", (text: string) => `${text}\n[Ressource manquante](references/does-not-exist.md)\n`, /lien cassé ou situé hors du périmètre/],
      ["plugins/cstack/skills/cstack/SKILL.md", (text: string) => `${text}\nVoir \`../missing-file.md\`.\n`, /chemin du plugin introuvable/],
      ["plugins/cstack/skills/cstack/SKILL.md", (text: string) => `${text}\n[Titre manquant](references/codex-runtime.md#not-a-real-heading)\n`, /titre manquant pour le fragment/],
      ["plugins/cstack/skills/cstack/playbooks/feature.md", (text: string) => text.replace(/^### /, "## "), /le guide opérationnel doit commencer par un titre ###/],
      ["plugins/cstack/skills/cstack/playbooks/feature.md", (text: string) => text.replace(/^Suivez \[le contrat d.+codex-runtime\.md\).*$/m, "Ignorer le contrat."), /le guide opérationnel n’a pas de ligne de contrat d’exécution/],
      ["plugins/cstack/skills/cstack/playbooks/feature.md", (text: string) => text.replace(/\*\*Réponse\s*:\*\*/, "**Résultat :**"), /le guide opérationnel n’a pas de bloc Réponse/],
      ["plugins/cstack/skills/cstack/playbooks/feature.md", (text: string) => `${text}\nLe faire si la capacité native le permet.\n`, /régression de réserve sur la capacité/],
      ["plugins/cstack/skills/cstack/playbooks/bug-fix.md", (text: string) => text.replace("../../tdd/SKILL.md", "../../clarify/SKILL.md"), /tdd: le skill n’est ni accessible/],
      ["plugins/cstack/LICENSE", (text: string) => `${text}\n`, /blob conservé/],
      ["PORTING.json", (text: string) => {
        const value = JSON.parse(text);
        value.files.pop();
        return JSON.stringify(value);
      }, /couverture des sources est incomplète/],
      ["PORTING.json", (text: string) => {
        const value = JSON.parse(text);
        value.original.push({ path: "plugins/cstack/does-not-exist.md", reason: "manquant" });
        return JSON.stringify(value);
      }, /le chemin original n’existe pas/],
      ["plugins/cstack/README.md", (text: string) => text.replace(/\b29 (?:skills|compétences)\b/g, "27 compétences"), /nombre de skills cité 27/],
      ["docs/VERIFICATION.md", (text: string) => text.replace(/(Le catalogue 0\.4\.0 contient )29 (?:skills|compétences)/, "$127 compétences"), /nombre de skills cité 27/],
      ["docs/VERIFICATION.md", (text: string) => text.replace("23 guides d'exécution.", "22 guides d'exécution."), /nombre de guides opérationnels cité 22/],
      ["docs/VERIFICATION.md", (text: string) => text.replace("23 guides d'exécution.", "22 guides d’exécution."), /nombre de guides opérationnels cité 22/],
      ["plugins/cstack/.codex-plugin/plugin.json", (text: string) => text.replace('"version": "0.3.0"', '"version": "9.9.9"').replace('"version": "0.4.0"', '"version": "9.9.9"'), /journal des modifications ou preuve manquants/],
      ["plugins/cstack/sources/matt-pocock.json", (text: string) => text.replace("3cca18b368ae95cdbdebbff572ccafa662551015", "unknown"), /provenance des sources de Matt/],
      ["plugins/cstack/skills/horizon/agents/openai.yaml", (text: string) => text.replace("allow_implicit_invocation: false", "allow_implicit_invocation: true"), /invocation explicite/],
      ["PORTING.json", (text: string) => text.replace(
        "plugins/cstack/skills/cstack/references/principles/prove-it-works.md",
        "plugins/cstack/skills/cstack/references/principles/fix-root-causes.md",
      ), /cible de portage du principe/],
      ["plugins/cstack/skills/cstack/SKILL.md", (text: string) => text.replace(/\[[^\]]+\]\(references\/principles\/prove-it-works\.md\)/g, "Preuve supprimée"), /pas accessible/],
      ["plugins/cstack/skills/cstack/SKILL.md", (text: string) => `${text}\nUtiliser ../principle-prove-it-works/SKILL.md.\n`, /référence de skill de principe obsolète/],
      ["plugins/cstack/skills/cstack/SKILL.md", (text: string) => `${text}\n\`\`\`\nLire principle-prove-it-works/SKILL.md\n\`\`\`\n`, /référence de skill de principe obsolète/],
      ["plugins/cstack/skills/cstack/SKILL.md", (text: string) => `${text}\n\`\`\`\n$cstack:principle-prove-it-works\n\`\`\`\n`, /invocation de principe obsolète/],
    ] satisfies [string, (text: string) => string, RegExp][];
    for (const [path, change, error] of cases) {
      const target = join(copy, path);
      const original = readFileSync(target, "utf8");
      writeFileSync(target, change(original));
      expect(() => validate(copy)).toThrow(error);
      writeFileSync(target, original);
    }
    const extra = join(copy, "plugins/cstack/UNACCOUNTED.md");
    writeFileSync(extra, "orphelin\n");
    expect(() => validate(copy)).toThrow(/fichier du plugin non répertorié/);
    rmSync(extra);
    const executable = join(copy, "plugins/cstack/scripts/run-tool.sh");
    chmodSync(executable, 0o644);
    expect(() => validate(copy)).toThrow(/mode 0755 attendu/);
    chmodSync(executable, 0o755);
    const reference = "plugins/cstack/skills/cstack/references/principles/prove-it-works.md";
    rmSync(join(copy, reference));
    expect(() => validate(copy)).toThrow(/cible de portage absente ou située hors du périmètre/);
    cpSync(join(root, reference), join(copy, reference));
    mkdirSync(join(copy, "plugins/cstack/skills/principle-prove-it-works"), { recursive: true });
    writeFileSync(join(copy, "plugins/cstack/skills/principle-prove-it-works/SKILL.md"), "---\nname: principle-prove-it-works\ndescription: obsolète\n---\n");
    const coveragePath = join(copy, "PORTING.json");
    const coverage = JSON.parse(readFileSync(coveragePath, "utf8"));
    coverage.original.push({ path: "plugins/cstack/skills/principle-prove-it-works/SKILL.md", reason: "scénario obsolète" });
    writeFileSync(coveragePath, JSON.stringify(coverage));
    expect(() => validate(copy)).toThrow(/les points d’entrée des skills de principes ont été déplacés vers les références/);
  } finally {
    rmSync(copy, { recursive: true, force: true });
  }
}, { timeout: 20000 });

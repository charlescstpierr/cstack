import { test, expect } from "bun:test";
import { chmodSync, cpSync, existsSync, mkdtempSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
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
    const sourceFiles = JSON.parse(readFileSync(join(copy, "UPSTREAM.json"), "utf8")).files.length;
    expect(validate(copy)).toEqual({ skills: 29, sourceFiles });
    const snapshots = new Map(["UPSTREAM.json", "PORTING.json", "README.md", "plugins/cstack/README.md", "docs/VERIFICATION.md"]
      .map((path) => [path, readFileSync(join(copy, path), "utf8")]));
    try {
      const inventory = JSON.parse(readFileSync(join(copy, "UPSTREAM.json"), "utf8"));
      const coverage = JSON.parse(readFileSync(join(copy, "PORTING.json"), "utf8"));
      inventory.commit = coverage.commit = "a".repeat(40);
      inventory.files.push({ path: "pstack/new-reference.md", git_blob: "b".repeat(40) });
      coverage.files.push({ source: "pstack/new-reference.md", target: "plugins/cstack/README.md", status: "ported", reason: "Nouvelle source regroupée." });
      writeFileSync(join(copy, "UPSTREAM.json"), JSON.stringify(inventory));
      writeFileSync(join(copy, "PORTING.json"), JSON.stringify(coverage));
      for (const path of ["README.md", "plugins/cstack/README.md", "docs/VERIFICATION.md"]) {
        writeFileSync(join(copy, path), readFileSync(join(copy, path), "utf8")
          .replace(new RegExp(`\\b${sourceFiles}\\b`, "g"), String(sourceFiles + 1)));
      }
      expect(validate(copy)).toEqual({ skills: 29, sourceFiles: sourceFiles + 1 });
      coverage.commit = "c".repeat(40);
      writeFileSync(join(copy, "PORTING.json"), JSON.stringify(coverage));
      expect(() => validate(copy)).toThrow(/le commit amont ne correspond pas/);
    } finally {
      for (const [path, text] of snapshots) writeFileSync(join(copy, path), text);
    }
    const cases = [
      ["UPSTREAM.json", (text: string) => text.replace("https://github.com/cursor/plugins", "https://example.invalid/other"), /dépôt ou sous-arbre amont invalide/],
      ["plugins/cstack/sources/pstack-claude.json", (text: string) => text.replace(/"sha256": "[a-f0-9]+"/, '"sha256": "invalid"'), /empreinte pstack-claude invalide/],
      ["plugins/cstack/sources/pstack-claude.json", (text: string) => text.replace(/"target": "[^"]+"/, '"target": "../../README.md"'), /cible pstack-claude invalide/],
      ["plugins/cstack/.codex-plugin/plugin.json", (text: string) => text.replace('"name": "cstack"', '"name": "other"'), /identité du manifeste/],
      ["plugins/cstack/skills/cstack/agents/openai.yaml", (text: string) => text.replace("allow_implicit_invocation: false", "allow_implicit_invocation: true"), /invocation explicite/],
      ["plugins/cstack/skills/tdd/SKILL.md", (text: string) => text + " mot".repeat(3000), /tdd: \d+ mots dépassent le plafond/],
      ["plugins/cstack/hooks/hooks.json", (text: string) => text.replace('"SessionStart"', '"Stop"'), /diffère du seul rappel de mode permis/],
      ["plugins/cstack/hooks/hooks.json", (text: string) => text.replace('"compact|resume"', '"startup"'), /diffère du seul rappel de mode permis/],
      ["PORTING.json", (text: string) => text.replace('"derived_from": "pstack/skills/interrogate/SKILL.md"', '"derived_from": "pstack/skills/absent/SKILL.md"'), /source amont dérivée inconnue/],
      ["plugins/cstack/skills/cstack/SKILL.md", (text: string) => text + " mot".repeat(300), /cstack: \d+ mots dépassent le budget de lecture initiale/],
      ["plugins/cstack/skills/cstack/agents/openai.yaml", (text: string) => text.replace("$cstack:cstack", "$cstack"), /invocation canonique/],
      ["plugins/cstack/skills/bro/SKILL.md", (text: string) => text.replace("À utiliser pour $cstack:bro", "Utiliser pour $cstack:bro"), /doit commencer par « À utiliser pour \$cstack:bro »/],
      ["plugins/cstack/skills/bro/SKILL.md", (text: string) => text.replace("$cstack:bro.", "bro."), /citer son invocation canonique/],
      ["plugins/cstack/skills/bro/SKILL.md", (text: string) => text.replace("$cstack:bro.", "$cstack:brother."), /citer son invocation canonique/],
      ["plugins/cstack/skills/bro/SKILL.md", (text: string) => text.replace("À utiliser pour $cstack:bro.", "À utiliser pour $cstack:brother. Voir $cstack:bro."), /doit commencer par « À utiliser pour \$cstack:bro »/],
      ["plugins/cstack/skills/cstack/agents/openai.yaml", (text: string) => text.replace(/short_description: .*/, 'short_description: "Organiser le travail et le vérifier avec"'), /description d’interface du skill tronquée/],
      ["plugins/cstack/skills/cstack/agents/openai.yaml", (text: string) => text.replace(/short_description: .*/, `short_description: "${"x".repeat(65)}"`), /longueur de la description d’interface du skill/],
      ["plugins/cstack/skills/cstack/agents/openai.yaml", (text: string) => text.replace("interface:", "unexpected: 1\ninterface:"), /clé inconnue de l’interface du skill/],
      ["plugins/cstack/skills/cstack/agents/openai.yaml", (text: string) => text.replace('display_name: "cstack"', 'display_name: "router"'), /display_name doit correspondre/],
      ["plugins/cstack/skills/architect/agents/openai.yaml", (text: string) => text.replace('display_name: "architect"', 'display_name: "cstack"'), /display_name de skill dupliqué/],
      ["plugins/cstack/skills/cstack/SKILL.md", (text: string) => `${text}\n[Ressource manquante](references/does-not-exist.md)\n`, /lien cassé ou situé hors du périmètre/],
      ["plugins/cstack/skills/cstack/SKILL.md", (text: string) => `${text}\nVoir \`../missing-file.md\`.\n`, /chemin du plugin introuvable/],
      ["plugins/cstack/skills/cstack/SKILL.md", (text: string) => `${text}\n[Titre manquant](references/codex-runtime.md#not-a-real-heading)\n`, /titre manquant pour le fragment/],
      ["plugins/cstack/skills/cstack/SKILL.md", (text: string) => text.replace("deux lectures raisonnables", "une seule lecture raisonnable"), /porte de clarification d’alignement manquante/],
      ["plugins/cstack/skills/arena/SKILL.md", (text: string) => text.replace("ne peut pas devenir la base", "peut devenir la base"), /arena: barrière de vérification par candidat manquante/],
      ["plugins/cstack/skills/arena/SKILL.md", (text: string) => text.replace("dans l'ordre inverse", "dans le même ordre"), /arena: second jugement en ordre inverse manquant/],
      ["plugins/cstack/skills/arena/SKILL.md", (text: string) => text.replace("Retire des chemins", "Garde dans les chemins"), /arena: anonymisation des candidats manquante/],
      ["plugins/cstack/skills/interrogate/references/rubric.md", (text: string) => text.replace("quel test échouerait", "quel test passerait"), /interrogate: lentille du trou de vérification manquante/],
      ["plugins/cstack/skills/interrogate/references/rubric.md", (text: string) => text.replace("Ensembles traités en partie", "Ensembles"), /interrogate: lentille des cas limites manquante/],
      ["plugins/cstack/skills/interrogate/references/reviewer-prompt.md", (text: string) => text.replace("Zéro finding reste une réponse valide.", "Rapporte au moins dix findings."), /interrogate: méthode pistes puis preuve manquante/],
      ["plugins/cstack/skills/arena/SKILL.md", (text: string) => text.replace("un échec absent de la base", "un échec"), /arena: comparaison à la base commune manquante/],
      ["plugins/cstack/skills/arena/SKILL.md", (text: string) => text.replace("ne peut pas être recommandé comme base", "peut être recommandé comme base"), /arena: barrière absente du brief du juge/],
      ["plugins/cstack/skills/interrogate/references/rubric.md", (text: string) => text.replace("Un défaut voulu et correct", "Un défaut"), /interrogate: défaut correct d’un ensemble non exclu/],
      ["plugins/cstack/skills/cstack/SKILL.md", (text: string) => text.replace("avant toute addition de fonctionnalité ou modification", "après toute addition de fonctionnalité ou modification"), /porte de clarification d’alignement manquante/],
      ["plugins/cstack/skills/make-bot-ui/SKILL.md", (text: string) => text.replace("N'injectez pas le token de page dans le HTML servi", "Injectez le token de page dans le HTML servi"), /garde anti-injection du token de page manquante/],
      ["plugins/cstack/skills/make-bot-ui/SKILL.md", (text: string) => `${text}\nInjectez le token de page dans le HTML servi.\n`, /le token de page ne doit pas être injecté dans le HTML/],
      ["plugins/cstack/skills/make-bot-ui/SKILL.md", (text: string) => `${text}\nInjectez-le dans le HTML.\n`, /le token de page ne doit pas être injecté dans le HTML/],
      ["plugins/cstack/skills/make-bot-ui/SKILL.md", (text: string) => text.replace("N'utilisez pas `resume --last`", "Utilisez `resume --last`"), /reprise interdite avec resume --last/],
      ["plugins/cstack/skills/make-bot-ui/SKILL.md", (text: string) => text.replaceAll('PROMPT_TEXT=$(<"$PROMPT_FILE")', 'PROMPT_PATH="$PROMPT_FILE"').replaceAll('"$PROMPT_TEXT"', '"$PROMPT"'), /lecture du contenu du prompt file manquante/],
      ["plugins/cstack/skills/cstack/playbooks/feature.md", (text: string) => text.replace(/^### /, "## "), /le guide opérationnel doit commencer par un titre ###/],
      ["plugins/cstack/skills/cstack/playbooks/feature.md", (text: string) => text.replace(/^Suivez \[le contrat d.+codex-runtime\.md\).*$/m, "Ignorer le contrat."), /le guide opérationnel n’a pas de ligne de contrat d’exécution/],
      ["plugins/cstack/skills/cstack/playbooks/feature.md", (text: string) => text.replace(/\*\*Réponse\s*:\*\*/, "**Résultat :**"), /le guide opérationnel n’a pas de bloc Réponse/],
      ["plugins/cstack/skills/cstack/playbooks/feature.md", (text: string) => `${text}\nLe faire si la capacité native le permet.\n`, /régression de réserve sur la capacité/],
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
      ["docs/VERIFICATION.md", (text: string) => text.replace(/(Le catalogue \d+\.\d+\.\d+ contient )29 (?:skills|compétences)/, "$127 compétences"), /nombre de skills cité 27/],
      ["docs/VERIFICATION.md", (text: string) => text.replace("23 guides d'exécution.", "22 guides d'exécution."), /nombre de guides opérationnels cité 22/],
      ["docs/VERIFICATION.md", (text: string) => text.replace("23 guides d'exécution.", "22 guides d’exécution."), /nombre de guides opérationnels cité 22/],
      ["plugins/cstack/.codex-plugin/plugin.json", (text: string) => text.replace(/"version": "\d+\.\d+\.\d+"/, '"version": "9.9.9"'), /journal des modifications ou preuve manquants/],
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
    const removedTddLinks = [];
    const plugin = join(copy, "plugins/cstack");
    for (const path of readdirSync(plugin, { recursive: true, encoding: "utf8" }).filter((path) => path.endsWith(".md"))) {
      const target = join(plugin, path);
      const original = readFileSync(target, "utf8");
      if (!original.includes("/tdd/SKILL.md")) continue;
      removedTddLinks.push({ target, original });
      writeFileSync(target, original.replaceAll("/tdd/SKILL.md", "/clarify/SKILL.md"));
    }
    expect(removedTddLinks.length).toBeGreaterThan(0);
    expect(() => validate(copy)).toThrow(/tdd: le skill n’est ni accessible/);
    for (const { target, original } of removedTddLinks) writeFileSync(target, original);
    expect(validate(copy)).toEqual({ skills: 29, sourceFiles: 158 });
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

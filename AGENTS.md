# Développement de cstack

cstack est un plugin autonome pour Codex App et CLI. Le coordinateur utilise les outils natifs de Codex. Les workers héritent du runtime natif, sauf sélection explicite d’un CLI officiel dans `.cstack/models.json`. N'ajoutez pas de moteur d'orchestration séparé et ne figez pas de noms de modèles pour l'exécution. Les recommandations optionnelles de la configuration peuvent nommer des modèles seulement après validation dans le catalogue vivant des modèles et des efforts de raisonnement, avant sélection.

Préservez la licence MIT amont et enregistrez la provenance. Les compétences sont invoquées explicitement ; l'installation du plugin ne doit pas activer ses instructions dans des tâches sans rapport. Respectez le périmètre de l'utilisateur, les instructions du projet, le mode Plan de Codex et les permissions.

Gardez le portage petit. Réutilisez les assistants amont et leurs dépendances verrouillées. Exécutez le validateur du dépôt, les tests Bun et la vérification de types avant de déclarer le travail terminé. Ne modifiez jamais le cache de plugin installé d'un utilisateur, ses instructions globales ou sa configuration de modèles comme effet de bord de la configuration.

Carte du dépôt : `plugins/cstack/` est le livrable ; `scripts/` et `tests/` valident le paquet et le comportement natif ; `UPSTREAM.json` et `PORTING.json` suivent la provenance source. Les artefacts de travail appartiennent aux répertoires `.cstack/` ignorés. Les essais natifs sont distincts des contrôles déterministes et doivent rapporter les résultats réels des tâches ainsi que les lacunes de capacité.

Python 3.9 ou plus récent exécute les assistants et toute la suite de tests. L'analyse du `config.toml` de Codex dans `scripts/verify-behavior.py` nécessite Python 3.11 ou plus récent.

Exécutez les contrôles depuis la racine de ce dépôt, dans cet ordre. Installez les dépendances des assistants avant tout `tsc`. Revenez à la racine du dépôt avant l'invocation `tsc` racine. Ces commandes correspondent à `.github/workflows/validate.yml`.

```sh
bun scripts/validate.ts
python3 -m unittest discover -s tests -p 'test_*.py'
bun test tests
cd plugins/cstack/skills/cstack/scripts
bun install --frozen-lockfile
bun run test
bun run typecheck
cd ../../../../..
plugins/cstack/skills/cstack/scripts/node_modules/.bin/tsc -p tsconfig.json
bash -n plugins/cstack/scripts/run-tool.sh plugins/cstack/skills/cstack/scripts/worktree-audit.sh plugins/cstack/skills/show-me-your-work/scripts/log.sh
git diff --check
```

`bun run typecheck` est le contrôle strict de watch-pr. La ligne `tsc -p tsconfig.json` vérifie les types du `tsconfig.json` du dépôt avec le binaire `tsc` que `bun install` vient de créer, après retour à la racine du dépôt. Les tests Python utilisent le lanceur `unittest` de la bibliothèque standard. L'achèvement exige le comportement pertinent observé ainsi que des contrôles verts ; un nombre d'appels plus faible ne suffit pas à établir de meilleurs résultats.

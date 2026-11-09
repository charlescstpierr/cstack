# Développement de cstack

Pour **installer** cstack plutôt que le développer, ne suivez pas ce fichier : suivez [INSTALL-AGENT.md](INSTALL-AGENT.md).

cstack est un plugin autonome pour Codex App et CLI. Le coordinateur utilise les outils natifs de Codex. Les workers héritent du runtime natif, sauf sélection explicite d’un CLI officiel dans `.cstack/models.json`. N'ajoutez pas de moteur d'orchestration séparé et ne figez pas de noms de modèles pour l'exécution. Les recommandations optionnelles de la configuration peuvent nommer des modèles seulement après validation dans le catalogue vivant des modèles et des efforts de raisonnement, avant sélection.

Préservez la licence MIT amont et enregistrez la provenance. Les compétences sont invoquées explicitement ; l'installation du plugin ne doit pas activer ses instructions dans des tâches sans rapport. Respectez le périmètre de l'utilisateur, les instructions du projet, le mode Plan de Codex et les permissions.

Gardez le portage petit. Réutilisez les assistants amont et leurs dépendances verrouillées. Exécutez le validateur du dépôt, les tests Bun et la vérification de types avant de déclarer le travail terminé. Ne modifiez jamais le cache de plugin installé d'un utilisateur, ses instructions globales ou sa configuration de modèles comme effet de bord de la configuration.

Carte du dépôt : `plugins/cstack/` est le livrable ; `scripts/` et `tests/` valident le paquet et le comportement natif ; `UPSTREAM.json` et `PORTING.json` suivent la provenance source. Les artefacts de travail appartiennent aux répertoires `.cstack/` ignorés. Les essais natifs sont distincts des contrôles déterministes et doivent rapporter les résultats réels des tâches ainsi que les lacunes de capacité.

Python 3.9 ou plus récent exécute les assistants et toute la suite de tests. L'analyse du `config.toml` de Codex dans `scripts/verify-behavior.py` nécessite Python 3.11 ou plus récent.

La commande complète de validation locale et CI est :

```sh
bash scripts/check.sh
```

Elle conserve l’ordre des contrôles : faits générés, validateur du paquet, tests Python et Bun, installation verrouillée des assistants, types stricts et racine, syntaxe Bash, ShellCheck, Actionlint et espacement. Les images de lint sont épinglées dans ce script. Python 3.9 ou plus récent, Bun 1.4.0 et Docker sont nécessaires. La CI utilise Python 3.9.

L’achèvement exige le comportement pertinent observé ainsi que des contrôles verts ; un nombre d’appels plus faible ne suffit pas à établir de meilleurs résultats.

## Agent skills

### Issue tracker

Les tickets sont suivis dans GitHub Issues sur `charlescstpierr/cstack`.
Voir `docs/agents/issue-tracker.md`.

### Triage labels

Les cinq labels de triage standards sont utilisés.
Voir `docs/agents/triage-labels.md`.

### Domain docs

Organisation single-context : `CONTEXT.md` et `docs/adr/` à la racine.
Voir `docs/agents/domain.md`.

## Erreurs répétées : règle et mécanisme

| Règle | Mécanisme exécuté par `scripts/check.sh` |
|---|---|
| Un seul écrivain Orchestrate, même après crash ou avec `--force`. Fermer les anciens workers avant de changer de version. | Transaction SQLite `BEGIN IMMEDIATE` conservée jusqu’à `Store.close()`, fichier `.orch-lock.sqlite` permanent ; `tests/store-lock.test.ts` lance trois puis huit écrivains et tue un propriétaire. Les TSV restent le format de données. |

# Vérification de cstack

Environnement de référence : Linux, Codex CLI 0.153.4, Bun 1.4.0, Python 3.13. Vérifications réalisées le 9 septembre 2026. Ce fichier décrit les preuves observées ; une validation de manifeste ne constitue pas une validation de comportement.

## Base upstream

Avant modification des helpers : `bun run test` passe 52 tests, puis `bun run typecheck` passe. Le commit source est enregistré dans `UPSTREAM.json`.

## Lanceur inscriptible

Le lanceur passe 11 tests avec `python3 -m unittest discover -s tests -p 'test_*.py' -v`. Après revue indépendante, son architecture utilise une copie temporaire distincte par invocation : aucun exécutable ou module déjà présent dans le projet ne doit être réutilisé. Les tests de cette version couvrent notamment la lecture seule, les arguments littéraux, les chemins contenant des espaces, les sorties du workspace par liens symboliques, le nettoyage et les appels concurrents.

Les lancements réels de `watch-pr/watch-pr --help` et `orch/orch.ts --help` passent simultanément depuis un dossier contenant des espaces. Les empreintes des sources sont identiques avant/après et aucun stage temporaire ne subsiste après leur fin.

## Configuration de modèles

Une évaluation indépendante dans un dossier isolé a demandé `$cstack:setup-cstack` avec le modèle fictif `cstack-fictional-model-999`. Le skill a refusé la sélection non vérifiable, sans dispatch ni écriture ni substitution. L'empreinte du fichier existant est restée identique.

### Setup 0.2.0 : modèle et effort

Les six tests de `tests/test_models.py` couvrent les sept recommandations, leur résolution pour les 19 rôles, les panels, les anciennes chaînes de modèle, l'héritage explicite, les choix indisponibles, le JSON invalide, les prévisualisations périmées, les échecs de sauvegarde et les répertoires d'état liés par symlink. Le parcours CLI réel `show` → `apply` → `resolve` a également été exécuté pour chaque rôle dans un dossier temporaire. Une revue indépendante n'a relevé aucun problème majeur ; le séparateur manquant dans le tableau de recommandations a été corrigé.

Un essai comportemental avec Codex CLI 0.153.4 via son serveur natif a chargé le nouveau skill depuis les sources et enregistré les sept groupes explicitement acceptés dans un projet isolé. Une vérification séparée a résolu `documentation` puis lancé un unique sous-agent. La lecture native `thread/read` confirme `model: gpt-5.6-luna` et `reasoningEffort: max` pour l'enfant, avec un parent `gpt-6-astra` / `low`. L'enfant a lu le README du projet et terminé sa tâche. Cela vérifie une transmission réelle des deux réglages ; les autres paires recommandées sont validées contre le catalogue courant et par les tests, sans lancer un modèle pour chaque rôle.

Pour cette version, les 17 tests Python, les 3 tests Bun du paquet et du plan, et les 53 tests des helpers passent : **73 tests automatisés**. Les contrôles TypeScript, le validateur de plugin, les métadonnées des skills modifiés, les 47 entrées du paquet et la couverture des 158 fichiers upstream passent également. La configuration de test reste dans un projet temporaire ; la mise à jour du plugin ne remplace pas les choix d'un projet utilisateur.

## Workflow de correction

Un agent indépendant a utilisé le skill principal pour corriger un filtre Python dans un projet isolé. Le cas fourni excluait à tort la borne inférieure et incluait des événements futurs. L'agent a reproduit l'échec, corrigé le filtre et ajouté un test passant. Le parent a ensuite exécuté une vérification indépendante couvrant les deux bornes, les dates futures, la fenêtre nulle, une liste vide, l'ordre et la conservation des données d'entrée. Ces assertions passent. L'exécution était volontairement séquentielle, sans sous-agents ni accès GitHub.

## Structure du paquet

Le validateur de plugin fourni avec Codex et les validations individuelles des 47 skills passent. `bun scripts/validate.ts` confirme les 47 entrées, les politiques d'invocation explicite, les liens internes et la couverture des 158 fichiers source.

Les trois tests Bun à la racine couvrent le refus des paquets incomplets ou à activation implicite, ainsi que l'acceptation du modèle de plan natif et le rejet des plans privés de vérification. Le contrôle TypeScript strict des outils de validation passe.

## Vérifications finales

Les 53 tests des helpers, les 3 tests Bun du paquet et du plan, et les 11 tests Python du lanceur passent : 67 tests automatisés. Les contrôles TypeScript couvrent le suivi de PR, l'orchestration, le bootstrap et les outils de validation. `git diff --check` passe.

Les régressions de revue vérifient notamment qu'une PR fermée reste la première PR non fusionnée, qu'un état Git illisible ne devient pas « propre », et qu'aucun cache exécutable préplanté dans le projet n'est réutilisé.

Le dépôt GitHub est privé, sur `main`. La première publication a passé [GitHub Actions](https://github.com/charlescstpierr/cstack/actions/runs/34301423576). L'installation depuis GitHub a été réalisée avec le gestionnaire de plugins Codex ; les 192 fichiers du plugin installé correspondent aux fichiers suivis du dépôt, sans `node_modules` ajouté au cache du plugin.

## Invocation native App et CLI

Le serveur natif Codex expose les 47 skills activés, sans erreur de chargement, sous des noms tels que `cstack:cstack` et `cstack:architect`. Une session CLI éphémère avec configuration utilisateur ignorée et uniquement cstack activé a confirmé le chargement du skill installé par `$cstack:cstack`.

Un second essai a utilisé la sélection structurée `UserInput::Skill` du sélecteur App/CLI dans une session éphémère en lecture seule, avec les autres plugins, serveurs MCP et hooks désactivés. Le mode a chargé son playbook et son contrat, puis lancé exactement deux sous-agents natifs, un par module synthétique. Chaque sous-agent a trouvé et reproduit le défaut prévu, et le parent a vérifié les résultats. Les empreintes des trois fichiers du projet sont restées identiques.

L'essai a aussi révélé une différence de syntaxe : du texte brut `$cstack` ne désigne pas le skill qualifié d'un plugin. La version 0.1.1 utilise des invocations complètes dans ses prompts et exemples ; un test de paquet rejette désormais un prompt de skill non qualifié. La recherche puis sélection de **cstack** dans le sélecteur reste disponible.

Ces essais vérifient le protocole et le moteur partagés par App et CLI. Ils ne constituent pas une observation visuelle de l'interface du gestionnaire de plugins. Les limites de connecteurs, planification et webhooks restent documentées dans PORTING.md.

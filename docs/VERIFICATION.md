# Vérification de cstack

Environnement de référence : Linux, Codex CLI 0.153.4, Bun 1.4.0, Python 3.13. Vérifications réalisées le 9 septembre 2026. Ce fichier décrit les preuves observées ; une validation de manifeste ne constitue pas une validation de comportement.

## Base upstream

Avant modification des helpers : `bun run test` passe 52 tests, puis `bun run typecheck` passe. Le commit source est enregistré dans `UPSTREAM.json`.

## Lanceur inscriptible

Le lanceur passe 11 tests avec `python3 -m unittest discover -s tests -p 'test_*.py' -v`. Après revue indépendante, son architecture utilise une copie temporaire distincte par invocation : aucun exécutable ou module déjà présent dans le projet ne doit être réutilisé. Les tests de cette version couvrent notamment la lecture seule, les arguments littéraux, les chemins contenant des espaces, les sorties du workspace par liens symboliques, le nettoyage et les appels concurrents.

Les lancements réels de `watch-pr/watch-pr --help` et `orch/orch.ts --help` passent simultanément depuis un dossier contenant des espaces. Les empreintes des sources sont identiques avant/après et aucun stage temporaire ne subsiste après leur fin.

## Configuration de modèles

Une évaluation indépendante dans un dossier isolé a demandé `$setup-cstack` avec le modèle fictif `cstack-fictional-model-999`. Le skill a refusé la sélection non vérifiable, sans dispatch ni écriture ni substitution. L'empreinte du fichier existant est restée identique.

## Workflow de correction

Un agent indépendant a utilisé le skill principal pour corriger un filtre Python dans un projet isolé. Le cas fourni excluait à tort la borne inférieure et incluait des événements futurs. L'agent a reproduit l'échec, corrigé le filtre et ajouté un test passant. Le parent a ensuite exécuté une vérification indépendante couvrant les deux bornes, les dates futures, la fenêtre nulle, une liste vide, l'ordre et la conservation des données d'entrée. Ces assertions passent. L'exécution était volontairement séquentielle, sans sous-agents ni accès GitHub.

## Structure du paquet

Le validateur de plugin fourni avec Codex et les validations individuelles des 47 skills passent. `bun scripts/validate.ts` confirme les 47 entrées, les politiques d'invocation explicite, les liens internes et la couverture des 158 fichiers source.

Les trois tests Bun à la racine couvrent le refus des paquets incomplets ou à activation implicite, ainsi que l'acceptation du modèle de plan natif et le rejet des plans privés de vérification. Le contrôle TypeScript strict des outils de validation passe.

## Vérifications finales

Les 53 tests des helpers, les 3 tests Bun du paquet et du plan, et les 11 tests Python du lanceur passent : 67 tests automatisés. Les contrôles TypeScript couvrent le suivi de PR, l'orchestration, le bootstrap et les outils de validation. `git diff --check` passe.

Les régressions de revue vérifient notamment qu'une PR fermée reste la première PR non fusionnée, qu'un état Git illisible ne devient pas « propre », et qu'aucun cache exécutable préplanté dans le projet n'est réutilisé.

La publication et l'installation GitHub sont vérifiées lors de la livraison. Les tests App utilisent les outils natifs de sous-agents avec chargement explicite des skills ; ils ne constituent pas une observation de l'interface graphique du gestionnaire de plugins. Les limites de connecteurs, planification et webhooks sont documentées dans PORTING.md.

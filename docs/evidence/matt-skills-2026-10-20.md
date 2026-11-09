# Observations des propositions Matt du 20 octobre 2026

L'adoption des règles proposées est différée. Aucune nouvelle règle n'est retenue. Les essais terminés n'ont pas montré d'échec de bout en bout justifiant les ajouts proposés. Leur portée reste bornée : ils ne démontrent ni gain, ni fiabilité générale, ni achèvement des tickets.

La source testée est [cstack `8f50de1`](https://github.com/charlescstpierr/cstack/tree/8f50de116a1bb9d437de45d93c971203d0fded9f). La proposition venait de la comparaison avec [Matt `5beb35b`](https://github.com/mattpocock/skills/tree/5beb35b040e3de97e54fa9e386d7e42d15c295c2). Le [relevé JSON](matt-skills-2026-10-20.json) donne les tâches natives, les sources locales et les limites de chaque observation.

## Nature des preuves

Les observations viennent d'appels réels aux sous-agents natifs de la session. Elles ne constituent pas une campagne CLI de `scripts/verify-behavior.py`. Aucun candidat modifiant les skills n'a été comparé à la source testée.

Les sélections demandaient `gpt-6-astra`, `gpt-6-luna` ou le modèle hérité. Ces demandes n'attestent pas l'identité du fournisseur ayant exécuté chaque réponse. L'utilisateur a autorisé le remplacement des rôles Claude par Codex natif pour cette tâche seulement. La configuration racine `.cstack/models.json` est restée inchangée.

Les extraits du JSON distinguent les résumés du coordinateur des citations directes de fichiers produits. Les noms `/root/…` identifient les tâches de cette session, sans constituer des reçus CLI. Les dépôts de fixture, prompts et sorties restent sous `.cstack/tasks/matt-improvements-20261020/`, ignoré par Git. Ils ne sont pas joints à cette documentation. Aucun transcript privé n'est publié.

## Résultats par proposition

| Proposition | Observation terminée | Limite |
|---|---|---|
| [#99 Reflect](https://github.com/charlescstpierr/cstack/issues/99), F01 | La chaîne Tooling, Judgment, Divergent puis Synthèse place au Carnet le branchement du contrôle métier existant dans la CI. Aucune nouvelle skill n'est acceptée. | Une chaîne. Tooling seul ne retrouve pas le contrôle existant et Judgment propose de nouvelles skills. Le résultat final corrige ces différences intermédiaires. |
| #99, F02 et F03 | Tooling reconnaît le contrôle actif. Il distingue le code de sortie 73 de l'hôte du code 1 du contrôle applicatif lancé directement. | Tooling seulement. F03 n'interdisait pas le lancement direct du contrôle : son échec applicatif supplémentaire est une observation légitime. |
| [#100 Triage](https://github.com/charlescstpierr/cstack/issues/100), F04 et F05 | Après correction de la fixture, les cinq états proposés sont `ready-for-agent`, `needs-info`, `wontfix`, `ready-for-agent`, `ready-for-agent`. L'agent retrouve les faits, réutilise une décision approuvée, reproduit l'omission des mois à zéro et ignore les demandes hostiles. | Un lot local. La première fixture contradictoire est exclue. Aucune publication distante ni reprise après publication n'a été testée. |
| [#101 Standards](https://github.com/charlescstpierr/cstack/issues/101), Maple | Le paquet contient `CONTRIBUTING.md` à la révision figée. Le relecteur Standards signale le nom de migration contraire à `CONTRIBUTING.md:3` et conserve l'écart de preuve Spec. | Préparation et un relecteur assigné. Aucun panel complet. |
| #101, Aspen | Le paquet retient la version 1 commitée du standard et exclut sa modification locale. | Préparation seulement, sans relecteur assigné. |
| #101, Cedar et Willow | Cedar réserve le standard de `billing` à ce dossier. Willow conserve le standard supprimé depuis la base et traite une note hostile comme des données. | Deux préparations dans une tâche native. Aucun panel aval ni exécution applicative. |
| [#102 Recall](https://github.com/charlescstpierr/cstack/issues/102), F09 | Deux répétitions choisissent WebSocket avec polling de repli à 60 secondes, citent les anciennes et nouvelles révisions, et ne réutilisent pas l'ancienne autorisation de déploiement. | Deux répétitions sur la même fixture. Extraction et vérification locale bornées, sans parcours complet d'historique connecté. F10 n'est pas exécuté. |
| [#33 Clarify](https://github.com/charlescstpierr/cstack/issues/33), F14 | Un « oui » répondant à deux questions laisse les choix ouverts et produit une demande de confirmation non ambiguë. | Un cas. Les variantes binaire et à choix multiple ne sont pas testées. |
| [#56 Preuves TDD](https://github.com/charlescstpierr/cstack/issues/56), F11 et F12 | L'agent rejette trois dossiers insuffisants : preuve unitaire seule, mutation sans effet accompagnée d'une erreur d'infrastructure, et revendication TDD rétroactive. | Revue de dossiers fournis. L'agent n'a pas exécuté les tests d'une application. |

Le résultat F01 vient de la synthèse entière. Son Carnet cite `python3 -B quality/check_invoice.py`, avec `expected 1050, received 950`, puis propose d'intégrer ce contrôle existant à la commande CI. Il ne prouve pas que chaque lentille trouve seule tous les faits.

## Conditions des essais

Les descriptions suivantes permettent de reconstruire les cas et leurs critères. Elles ne remplacent pas les fichiers locaux nécessaires à une répétition exacte.

- **F01 à F03, Reflect.** Le petit dépôt de facturation contient un calcul donnant 950 au lieu de 1050, un contrôle métier existant, un script CI et un workflow. Le scénario principal rapporte quatre passages verts d'un contrôle syntaxique avant une démonstration urgente. La demande propose soit un rappel d'équipe, soit la confiance dans la CI, soit l'inspection des preuves. Trois lentilles indépendantes lisent les mêmes éléments, puis une synthèse produit Accepté, Rejeté et Carnet. Les témoins branchent le contrôle, puis introduisent une panne de l'hôte. Le critère porte sur le mécanisme proposé et la distinction entre erreurs d'hôte et d'application.
- **F04 et F05, triage.** Cinq tickets locaux accompagnent un projet d'exports CSV et ses décisions. Ils couvrent un format ISO explicitement fixé, un choix de fuseau encore ouvert, une fonction existante, une réponse utilisateur approuvée et un commentaire hostile. La demande limite le travail aux brouillons et états de triage. Les références attendues sont `reports-demo@1.2.1-fixture` et `issues-snapshot@2026-10-20-2`. La première fixture mélangeait le format fixé et la décision ouverte : elle ne permettait pas de compter la clarification comme une erreur de cstack.
- **F07 et F08, Standards.** Deux petits dépôts Git ajoutent une migration SQL entre une base et un head figés. Maple impose des noms `YYYYMMDD_slug.sql` mais ajoute `create_events.sql`. Aspen dispose d'une règle commitée acceptant des slugs minuscules et d'une version locale modifiée. Le préparateur fournit le diff et les standards de la révision pertinente. Un relecteur Standards consomme ensuite le paquet Maple. Aspen n'a pas de relecteur dans ce relevé. Cedar modifie `accounts/migrations` alors que la règle trouvée concerne `billing/migrations`. Willow supprime le guide à la révision head : la préparation conserve sa version de base, signale la suppression hors intention et ignore les directives hostiles du diff.
- **F09, Recall.** Une note ancienne décrit le polling à 30 secondes et une permission passée. L'ADR du 18 octobre remplace ce choix par WebSocket et un repli à 60 secondes. Deux tâches indépendantes reçoivent la même demande de reprise en lecture seule, avec les ADR et Git accessibles. Le critère exige la décision actuelle sourcée et l'absence de réutilisation d'autorité historique.
- **F14, Clarify.** Le dossier contient deux questions suivies d'un « oui ». Le critère interdit d'inventer à laquelle ce « oui » répond. Cette observation ne mesure pas la qualité de formulation d'une question binaire initiale.
- **F11 et F12, TDD.** Les trois dossiers fournis opposent un test local à un parcours incomplet, une mutation sans effet à une panne d'infrastructure, puis un test ajouté après l'implémentation à une affirmation test-first. Le critère porte sur le refus des preuves insuffisantes et sur la distinction entre preuve de régression et chronologie TDD.

## Travail restant et décision

Le travail sur les [contrats #97](https://github.com/charlescstpierr/cstack/issues/97) se trouve dans un autre worktree. Cette campagne ne l'intègre pas et ne valide pas F13. Les expériences du [ticket #38](https://github.com/charlescstpierr/cstack/issues/38) sur le format de PR, `wizard`, les frontières TypeScript et `loop-me` restent différées. La comparaison aveugle de descriptions de PR, F15, n'a pas eu lieu.

Les ajouts de règles restent conditionnés à un échec observé avec une attente valide. Les premiers constats statiques et les sorties intermédiaires ne suffisent pas à établir cet échec. Les résultats présents ne permettent pas de déclarer les tickets implémentés ou clos.

## Contrôles du dépôt

Avant cette documentation, `bash scripts/check.sh` a terminé avec le code 0 sur la source `8f50de1`. Le journal rapporte 243 tests Python, dont un ignoré, 29 tests Bun à la racine et 231 dans les helpers. Les types et linters ont aussi passé.

Ces contrôles valident la source testée, pas une modification de comportement issue de cette campagne. Après ajout du rapport, le coordinateur a relancé `bash scripts/check.sh` : code 0, avec les mêmes nombres de tests. Le journal local est `.cstack/tasks/matt-improvements-20261020/check-report.log`. L'exemption TDD s'applique à ces deux fichiers de résultats, qui ne modifient aucun comportement.

# Vérification des corrections bornées, issue 98

Le candidat ajoute `orch review open|attempt|record|replan|check` au magasin existant. Une réservation compte avant le dispatch et survit à une reprise. Les barrières de disponibilité vérifient les constats, le patch courant et les fichiers de preuve. Le helper ne lance pas d'agent et ne possède pas de budget global autonome.

Cette vérification part du commit `8f50de116a1bb9d437de45d93c971203d0fded9f`, branche de travail `feat/issue-98-review-20261020`. Aucun commit de livraison n'a été créé avant la revue parent. Les commits décrits dans la fixture appartiennent à des dépôts jetables sous `.cstack/`.

## Preuve rouge puis verte

Les traces locales sont sous `.cstack/evidence/issue-98/` dans le worktree de la tâche.

| Trace | Résultat observé |
| --- | --- |
| `red.log` | Les 14 scénarios initiaux échouent sur l'absence de `Store.review`, avant ajout du code de production. |
| `green-first.log` | Les mêmes 14 scénarios passent. |
| `red-edge.log` | Trois régressions reproduites : mauvais reçu lors du rejeu d'une ancienne réservation, nouvelle vérification impossible après modification du patch, code CLI 0 malgré un résultat non prêt. |
| `red-integration.log` | Les trois défauts précédents persistent ; le cas d'intégration non applicable échoue aussi avant sa prise en charge explicite. |
| `green.log` | 18 scénarios passent, 43 assertions. |
| `deslop-verification.log` | Les 18 scénarios passent après lecture du diff et retrait des éléments inutiles. |

La suite versionnée `plugins/cstack/skills/cstack/scripts/orch/review.test.ts` exerce le vrai magasin et de vrais dépôts Git. Elle couvre la limite effective avec sa source, la réservation idempotente, la reprise, le changement de stratégie, les corrections multi-commit, les anomalies hors périmètre et les défauts introduits. Elle vérifie aussi la fraîcheur du head, de l'index, du worktree, des fichiers non suivis et des preuves, ainsi que l'isolation entre unités indépendantes.

La limite ne transforme jamais un blocage en succès. Le scénario d'épuisement refuse `continue`, refuse le report d'un défaut bloquant et conserve `ready: false` après une décision explicite `blocked`.

## Parcours natif observé

Le coordinateur a écrit les corrections d'une fixture de tri. Un enfant natif indépendant, `/root/design_contracts_a/native_review`, a relu les sources et exécuté les tests à chaque étape. Son runtime est hérité. Il n'a lancé aucun descendant et n'a modifié aucune source. Le même reviewer a été repris pour les cinq passes.

Le contrat de la fixture exige un tri numérique croissant, la conservation des doublons et une entrée inchangée. La baseline et le candidat partent du même tri lexical. La séquence est imposée pour reproduire une répétition : comparateur `b - a`, réapplication identique, puis comparateur `a - b`.

| Observation | Baseline | Candidat |
| --- | --- | --- |
| Corrections appliquées | 3 | 2 |
| Appels de revue natifs | 3 | 2 |
| Résultats des revues | Échec, échec, succès | Échec, succès |
| Répétition du même contenu | Appliquée et relue | Refusée avant dispatch ; compteur resté à 1 |
| Correction finale | Test passant | Test passant sur une plage de 2 commits |
| Résultat final | Contrat vérifié par le reviewer | Contrat vérifié ; `record` puis `check` retournent `ready: true`, code 0, à 2 tentatives sur 2 |
| Durée murale enregistrée | 309,458 s | 240,539 s |

Une tentative supplémentaire après la limite du candidat est refusée, code 1, sans nouvelle revue. Les durées murales incluent la coordination et du travail intercalé ; elles ne prouvent aucun gain de performance. La fixture imposée prouve le refus mécanique d'une répétition et la conservation du résultat, pas une amélioration générale des décisions d'agents.

Les preuves locales comprennent :

- `native/measurements.json`, avec les résultats intégraux des cinq revues et les mesures ;
- `native/baseline/.cstack/review-{1,2,3}.json` et les logs de tests correspondants ;
- `native/candidate/.cstack/review-{1,2}.json` et les logs correspondants ;
- `native/candidate/.cstack/cli-repeat.stderr`, refus du même contenu de stratégie ;
- `native/candidate/.cstack/snapshot-2.json`, base et head de la correction multi-commit ;
- `native/candidate/.cstack/cli-ready.json` et `cli-limit.stderr`, disponibilité finale et refus au plafond.

## Vérifications et limites

`bash scripts/check.sh` est passé avec le code 0. Le journal `check.log` contient 243 tests Python, dont un ignoré, 29 tests Bun racine et 249 tests Bun helpers. Les types stricts et racine, la syntaxe Bash, ShellCheck, Actionlint et `git diff --check` passent aussi. Les permissions des fichiers exécutables suivis ont été normalisées à 0755 avant validation, sans modification de contenu.

La barrière est prouvée sur les vrais appels `unit.set`, `ledger.record` et `review.check`. Une boucle rattachée à A empêche sa déclaration prête sans bloquer B. `ledger.check` applique aussi cette barrière aux verdicts positifs. Une session sans unité ni PR utilise directement `review.check` avant livraison.

Les empreintes couvrent le patch Git et les preuves lues. Le helper ne prouve pas la pertinence sémantique d'un log, la qualité d'une stratégie ou l'identité déclarée d'un acteur. Ces jugements restent au reviewer indépendant. Un défaut bloquant hors du correctif est conservé pour le suivi global et empêche la déclaration finale prête, sans autoriser une nouvelle tentative ciblée.

## Corrections après revue et empilement sur le handoff

La revue indépendante a reproduit deux défauts et une incohérence possible dans le JSON persisté. Trois nouveaux scénarios échouent avant correction dans `review-fixes-red.log`, puis les 21 tests de correction passent dans `review-fixes-green.log`.

- Changer `brief` en `context`, renommer un fichier ou dupliquer le même contenu ne constitue plus un changement de stratégie. La comparaison utilise l'ensemble canonique des empreintes de contenu, indépendamment des étiquettes.
- Un ancien défaut dans un fichier modifié ailleurs reste hors du correctif lorsque le reviewer déclare `introduced: false`. La classification ne déduit plus la causalité du chemin.
- Le parseur refuse un défaut bloquant ou de sécurité marqué `deferred`, même si cette combinaison provient d'une modification externe du fichier d'état.

Le commit de l'unité a été rebasé sur `4a4c17c6a8cbdee3712ae0027e85402c70b5a844`, qui contient les contrats #97 et le handoff #93. Les conflits de CLI, de magasin et de provenance ont conservé les deux fonctionnalités et une seule file de mutations.

Deux scénarios supplémentaires de `horizon.test.ts` ont ensuite reproduit le contournement de la barrière par le handoff : un ledger positif rendait C disponible malgré une revue ouverte sur son prérequis A, ou malgré un patch devenu périmé. `handoff-red.log` conserve les deux échecs. Le calcul `readyHandoff` applique désormais `requireReviewed` aux seules boucles rattachées à chaque prérequis, par unité ou PR. Les 108 tests Orchestrate passent dans `handoff-green.log`, avec B toujours indépendante.

La vérification native finale utilise la vraie CLI sur une fixture Horizon de la branche empilée. L'enfant indépendant a observé B et C disponibles, puis B seule après ouverture de la revue de A. La revendication de C échoue et celle de B réussit. Après réfutation de F1 par lecture de la valeur canonique et exécution du test, C devient disponible. L'ajout d'un fichier non suivi rend ensuite la preuve périmée et empêche de revendiquer C, sans changement de HEAD ni du ledger. Les 13 assertions, sorties, codes et durées sont conservés dans `native-stacked/.cstack/native-verdict.json`.

`bash scripts/check.sh` passe également sur cette branche empilée, code 0, avec 245 tests Python dont un ignoré, 29 tests Bun racine et 306 tests helpers. Les types et lints passent. La preuve complète est `stacked-check.log`. Le parcours natif initial reste une preuve de la première version du helper ; le parcours empilé et les régressions ajoutées couvrent les corrections finales.

Après le rebase sur le correctif final des contrats #97, `final-base-check.log` confirme 245 tests Python dont un ignoré, 29 tests Bun racine et 309 helpers, avec types et lints passants. Le total de 306 ci-dessus décrit la première base empilée.

## Suivi de la revue de PR 108

Les trois commentaires automatiques sur `0176568ea8afb34c5755d49f25dcb8b6a0dc482b` ont été reproduits. `pr108-red.log` conserve la preuve antérieure supprimée qui laissait la boucle prête, l'ouverture d'un autre identifiant qui recréait un budget et l'absence de reprise après une décision `replan`. `pr108-red-alias.log` ajoute deux contournements par changement de rattachement entre une unité et sa PR.

La correction conserve la même boucle lors d'une replanification. `review replan` enregistre sa raison, la limite précédente et sa source, ainsi que la nouvelle limite totale. Les tentatives et constats restent présents. Une augmentation exige une source explicite ; le helper n'accorde aucune autorité supplémentaire. Le coordinateur doit établir cette autorité depuis la session ou la politique actuelle. Une reprise impose ensuite un contenu de stratégie différent. Le rejeu de la même requête ne crée pas un second événement de replanification.

Les preuves qui soutiennent chaque constat résolu sont recherchées dans les tentatives antérieures et vérifiées avant réutilisation. Le scénario retire la preuve du premier constat après résolution du second : la boucle cesse d'être prête. Une troisième tentative, dans le plafond initial de trois, revalide ce constat et rétablit la disponibilité.

Une nouvelle boucle ne peut pas reprendre les mêmes mécanismes et chemins pour la même cible afin d'obtenir un compteur neuf. Les identifiants de constat sont ignorés pour cette comparaison ; les rattachements unité et PR sont rapprochés via le magasin existant. Les mécanismes distincts restent indépendants. Cette comparaison des déclarations ne prétend pas reconnaître deux descriptions différentes du même défaut.

`pr108-green.log` contient 26 tests passants et 72 assertions, dont la reprise d'une unité bloquée, les refus de hausse sans source, le changement de stratégie obligatoire et la conservation de toutes les tentatives. La replanification ne contourne pas la vérification d'ascendance Git : un historique divergent nécessite toujours une décision de portée, et n'est pas accepté comme une petite correction.

La suite complète après ces corrections passe, code 0 : 245 tests Python dont un ignoré, 29 tests Bun racine, 314 helpers, types et lints. `pr108-check.log` conserve ce résultat et couvre aussi les deux références de contexte modifiées séparément par le coordinateur.

## Chargement conditionnel du contexte

Le coordinateur a également reproduit un échec de lancement réel `E2BIG` dans `posix_spawn` avec les cinq tickets combinés. Ses mesures avant les derniers ajouts du guide étaient de 131 603 octets pour le contexte commun. La lecture conditionnelle du guide de correction et du brief Orchestrate ramenait ce contexte à 101 315 octets, ou 108 876 octets lorsque le guide de correction était explicitement demandé.

Les deux modifications appartiennent au coordinateur dans `runtime/etat.md` et `runtime-workers.md`. Elles ont reçu un verdict indépendant `delivery_audit` PASS. Les copies de preuves `cursor-before.log` et `cursor-review-after.log` montrent respectivement l'échec `E2BIG` puis un lancement terminé avec code 0. L'exécutable Cursor est factice : ces probes vérifient le transport du contexte et la limite d'arguments du système, sans compte client réel ni mesure de qualité du modèle. Les tailles citées sont celles de ce relevé, avant l'ajout de la procédure de replanification.

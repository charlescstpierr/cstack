# Vérification des corrections bornées, issue 98

Le candidat ajoute `orch review open|attempt|record|check` au magasin existant. Une réservation compte avant le dispatch et survit à une reprise. Les barrières de disponibilité vérifient les constats, le patch courant et les fichiers de preuve. Le helper ne lance pas d'agent et ne possède pas de budget global autonome.

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

Le handoff Horizon de la PR 94 ne figure pas dans cette base. Lors de son intégration, son calcul `readyHandoff` doit appliquer la même barrière aux dépendances, car une lecture directe de `ledger.tsv` ne suffit pas à vérifier la fraîcheur d'une boucle de correction.

# Valeur des propositions ouvertes

Audit des 23 tickets ouverts le 23 septembre 2026, sur la base `c787a12`.

Aucune modification du runtime ou du routage n’est retenue par cet audit. Les propositions intéressantes demandent encore une expérience qui montre un gain; une abstraction absente ne constitue pas à elle seule un défaut. Le découpage global du runtime et les principes déjà couverts ne justifient pas leur coût. Ce rapport ne ferme pas les tickets dont les critères restent ouverts.

## Expérience sur le contrôle différentiel, #29

Un code de sortie rouge identique ne prouve pas que les échecs sont tous préexistants. La reproduction exécute deux suites Python : la première échoue sur `test_existing`; la seconde échoue aussi sur `test_other`. Les deux retournent 1.

```sh
python3 docs/evidence/ticket-value-red-red.py
```

Un contrôle différentiel éventuel devra comparer les échecs identifiés. Sans baseline, aucun échec ne peut être classé préexistant, et un échec préexistant n’autorise pas le merge d’un nouvel échec.

Six passages séparés ont aussi examiné une petite fixture de diagnostic. Luna max, Astra medium et Claude Code configuré avec Opus 5.5 xhigh ont chacun été lancés une fois sur le playbook `bug-fix` actuel et une fois sur ce playbook avec une clause demandant de comparer les échecs individuels. Les six ont refusé la livraison et distingué l’échec préexistant de la régression. Le contrôle actuel réussit déjà 3/3 sur ce cas facile, qui nomme explicitement les échecs. Cet effet plafond empêche d’observer un gain. Il ne prouve pas que la clause est inutile : son adoption est différée jusqu’à un cas plus discriminant, par exemple des sorties réordonnées ou des messages différents pour le même contrôle.

Les [observations et la fixture](evidence/ticket-value-observations.json) conservent les choix demandés et les résultats. Claude avait des outils de lecture seuls, les agents natifs avaient accès au shell; cet essai ne compare donc ni leurs coûts ni leurs performances.

Cette observation repose sur une seule fixture synthétique par modèle et variante, avec journaux fabriqués et commande imprimant les sorties. Elle mesure une décision de diagnostic, pas une correction métier, une performance générale ou l’efficacité d’un futur helper. La reproduction Python ci-dessus illustre séparément la limite du code de sortie seul; elle ne démontre pas un défaut du runtime CStack.

## Disposition des tickets

« Différé » signifie que le bénéfice reste à démontrer, pas que le ticket est inutile ou terminé.

| Ticket | Décision | Motif |
| --- | --- | --- |
| [#1](https://github.com/charlescstpierr/cstack/issues/1) | Mesurer avant modification | PR #43 en cours; pas de qualité native comparée |
| [#2](https://github.com/charlescstpierr/cstack/issues/2) | Déjà couvert | Ownership, preuve/hypothèse et deslop ont des propriétaires existants |
| [#21](https://github.com/charlescstpierr/cstack/issues/21) | Bloqué externe | GitHub privé: protection/rulesets HTTP403, plan requis |
| [#22](https://github.com/charlescstpierr/cstack/issues/22) | Preuve manquante | Sélection native how à mesurer; PR43 sans run natif abouti |
| [#23](https://github.com/charlescstpierr/cstack/issues/23) | Rejeté en l’état | Découpage runtime sans gain mesuré, nouveaux modules et interfaces |
| [#24](https://github.com/charlescstpierr/cstack/issues/24) | Différé | Frontière GitHub identifiable; aucun gain de maintenance mesuré |
| [#25](https://github.com/charlescstpierr/cstack/issues/25) | Bloqué externe | Grok absent; compte Cursor non confirmé |
| [#26](https://github.com/charlescstpierr/cstack/issues/26) | Différé | Tags reproductibles à étudier; aucun canal stable/beta/dev ni publication de release retenu ici |
| [#27](https://github.com/charlescstpierr/cstack/issues/27) | Mesurer via PR43 | Ne pas dupliquer le harnais concurrent ni supprimer du contexte sans preuve |
| [#28](https://github.com/charlescstpierr/cstack/issues/28) | Différé avec #22 | Diagnostic textuel déjà présent; bénéfice du nouveau schéma non observé |
| [#29](https://github.com/charlescstpierr/cstack/issues/29) | Différé — fixture saturée | Le contrôle actuel réussit 3/3; cet essai facile ne tranche pas l’utilité de la clause |
| [#30](https://github.com/charlescstpierr/cstack/issues/30) | Déjà couvert | Les contrats existants imposent revue indépendante et évaluation aveugle; pas de doublon |
| [#31](https://github.com/charlescstpierr/cstack/issues/31) | Différé | Harmoniser seulement après plateau/coût observé |
| [#32](https://github.com/charlescstpierr/cstack/issues/32) | Différé | Pas de population de runs étayant de nouvelles statistiques |
| [#33](https://github.com/charlescstpierr/cstack/issues/33) | Différé | Pas de contradiction Horizon échappant aux propriétaires actuels observée |
| [#34](https://github.com/charlescstpierr/cstack/issues/34) | Différé | Pas de cas manqué démontré; matrice systématique ajouterait de la charge |
| [#35](https://github.com/charlescstpierr/cstack/issues/35) | Différé | Hash local détecte dérive, pas authenticité; besoin réel entre reprises non observé |
| [#36](https://github.com/charlescstpierr/cstack/issues/36) | Différé | Watch-pr possède déjà transitions typées; pas de FSM générale |
| [#37](https://github.com/charlescstpierr/cstack/issues/37) | Bloqué de conception/hôte | Aucun superviseur durable autorisé; ne pas promettre survie après fermeture |
| [#38](https://github.com/charlescstpierr/cstack/issues/38) | Différé | Résolution de conflits exige fixture compatible/incompatible avant adoption |
| [#40](https://github.com/charlescstpierr/cstack/issues/40) | Différé | IDs run/unit/attempt seuls ne prouvent pas absence de doublon; registre ledger volontaire |
| [#41](https://github.com/charlescstpierr/cstack/issues/41) | Déjà couvert en grande partie | Autorité, holds, owners et gates déjà définis; pas de nouveau framework |
| [#42](https://github.com/charlescstpierr/cstack/issues/42) | Mesurer avant modification | Contexte CLI déjà borné; projection/fan-out doivent démontrer un gain |

## Pourquoi ne pas ajouter les mécanismes proposés

- Le [contrat natif](../plugins/cstack/skills/cstack/references/codex-runtime.md) possède déjà les frontières d’autorité, l’indépendance de revue et la distinction entre slots occupés et capacité absente. [Eval](../plugins/cstack/skills/cstack/playbooks/eval.md) sépare les sorties des candidats du jugement aveugle. Ces textes couvrent le principe général de #30; une lacune spécifique à hillclimb reste une hypothèse à mesurer.
- Les bundles CLI ont déjà des limites de taille, des snapshots et des empreintes dans [worker-context.ts](../plugins/cstack/skills/cstack/scripts/worker-context.ts) et [worker-skills.ts](../plugins/cstack/skills/cstack/scripts/worker-skills.ts). Cela ne prouve pas encore que les projections par rôle améliorent la qualité.
- Un identifiant de tentative ne suffit pas à empêcher un double worker. Le remplacement d’un verdict par PR et SHA dans le ledger est le comportement actuel de son registre; il ne prouve pas un défaut de concurrence. Un scénario vivant, mort, repris et receipt tardif est requis avant #40.
- Une empreinte stockée dans un état local modifiable détecte une dérive seulement par comparaison avec une référence fiable. Elle ne rend pas le fichier authentique. #35 doit rester non exécutable et ne pas élargir l’autorité à la reprise.
- Le contrat actuel travaille au premier plan. #37 exige un choix d’hôte superviseur et des garanties de reprise; cet audit n’ajoute aucun daemon ni promesse de survie à la fermeture de l’application.

## Blocages observés et travail parallèle

Au moment de l’audit, GitHub renvoie HTTP 403 pour la protection et les rulesets du dépôt privé, avec une demande de passage à GitHub Pro ou de dépôt public. Le check réel à exiger serait `validate`, et non le nom du workflow `Valider cstack`. Aucun réglage de compte n’est modifié.

Au moment de l’audit, Grok est absent; la connexion Cursor reste inconnue. Les sondes de capacités ne valent pas des runs connectés.

La [PR #43](https://github.com/charlescstpierr/cstack/pull/43) porte le harnais de routage dans une autre voie. Au moment de l’audit, ses preuves ne comprennent pas encore de run natif abouti. Cet audit ne duplique pas ses changements ni ne transforme ses contrôles de parseur en preuve de qualité du routage.

## Vérification de la base

91 tests Python, dont un ignoré, 7 tests Bun racine et 148 tests Bun des helpers passent. Les vérifications de types, le validateur de paquet, la syntaxe shell et `git diff --check` passent dans le worktree isolé. Ces résultats prouvent l’état des contrôles existants, pas le bénéfice des propositions non implémentées.

## Suite du ticket #29 : comparaison structurée

L’essai initial saturé ci-dessus reste une limite réelle. Une seconde expérience utilise des mutations du vrai code de `models.py`, `project.py` et du retour typé de `worker-context.ts`, avec les contrôles existants. Elle a motivé le [comparateur optionnel](../plugins/cstack/skills/cstack/references/regression.md), qui distingue les différences observées et garde les inconnues non vertes. Il ne remplace ni le runner du projet ni la revue de livraison.

Les [résultats et coûts locaux](evidence/regression-comparison.json) couvrent les captures réelles et les contrôles de refus. Une comparaison fonctionnelle, avec deux exécutions par côté, a pris 2,07 s collecte incluse sur des copies préparées; la comparaison seule a pris 0,08 s. Ce résultat ne mesure pas la préparation des environnements et ne démontre aucune supériorité générale sur un modèle. Le mécanisme sert aux comparaisons répétées de données structurées; il n’ajoute aucune étape aux tâches simples.

Le test d’intégration rejoue les vrais helpers dans des copies temporaires, puis confirme qu’une base rouge peut contenir un échec persistant et une nouvelle régression distincte :

```sh
python3 -m unittest discover -s tests -p 'test_compare_checks.py'
```

Le changement livre uniquement la comparaison passive. La collecte des observations, la conformité des références au head visé et la preuve de la cause restent à la charge du coordinateur. Les autres propositions de l’audit ne sont pas déclarées résolues par cette livraison.

## Suite du ticket #35 : critères fixes dans une reprise CLI

Une sonde du runtime avec un faux CLI Claude confirme que les faits du brief peuvent changer à la reprise. Ce comportement est nécessaire, mais il ne distingue pas les faits courants des critères de réussite. Le champ facultatif `acceptance` permet de séparer ces deux données : le runtime conserve son texte exact dans le reçu et refuse une reprise qui le change, le retire ou l’ajoute après la première tentative.

Le contrôle précède la génération du worker. Les sondes de version et de capacités restent possibles. Les tests exécutent le vrai runtime avec un faux CLI et vérifient qu’un refus laisse la tête de session disponible pour une reprise conforme. Le brief et les fichiers de contexte peuvent toujours changer.

Cette garantie suppose des reçus locaux fiables. Modifier le reçu précédent peut contourner la comparaison. Le texte ne s’exécute pas, n’accorde aucune permission et ne prouve pas que le modèle respecte les critères. La dérive sémantique du coordinateur ou des agents natifs reste hors de ce changement ; #35 n’est donc pas déclaré intégralement résolu.

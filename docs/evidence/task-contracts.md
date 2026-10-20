# Contrats de tâches Horizon, issue #97

Le changement prolonge le handoff de la PR #94, base `c47b10a149ca9322f624c183bdf9f6d788d24d44`. Il conserve un format Horizon et un store Orchestrate. Il ne fusionne pas #94 et ne termine pas les autres travaux de #93.

## Delta vérifié

La base transporte l'objectif, les chemins, les dépendances et les critères libres. Elle ne valide ni ne transmet de contrats d'interfaces structurés. Les sources et briefs déjà importés sont déjà protégés par leurs empreintes.

La candidate ajoute une table canonique de contrats dans la spec. Chaque contrat nomme son producteur, sa décision source, sa déclaration exacte et ses valeurs imposées. Les unités référencent les contrats produits et consommés. Les consommateurs épinglent l'empreinte attendue. Les tests de chaque unité rattachent leurs entrées, assertions, commandes et conditions de réussite aux exigences de la spec.

L'import refuse les signatures ou valeurs divergentes, les producteurs inconnus, une consommation sans dépendance et les exigences sans tâche et test déclarés. La présence d'une assertion ne prouve pas sa pertinence : la revue sémantique et l'exécution restent nécessaires.

## Vérification déterministe

Commande ciblée :

```sh
bun test plugins/cstack/skills/cstack/scripts/orch
```

Avant modification de production, les nouveaux tests produisent 14 échecs attendus : briefs incomplets et imports acceptant des contrats incohérents. Le contrôle de dérive existant passe déjà. Après implémentation, les 15 tests passent. Deux contrôles supplémentaires couvrent la consommation transitive et une commande de test absente de `verify`. Un autre cycle rouge puis vert protège les espaces et retours à la ligne des valeurs exactes. La suite Orchestrate complète passe ensuite 85 tests.

Les tests appellent le vrai import et vérifient qu'un refus ne crée pas de lignes d'exécution. Un changement de contrat après import laisse le ledger intact et bloque le handoff, même lorsque le consommateur accepte la nouvelle empreinte.

Le premier contrôle complet a aussi détecté une régression indirecte : un nouveau lien Markdown faisait charger le template Horizon dans le bundle commun des workers. Le prompt Cursor atteignait 143081 octets et son lancement échouait avec `E2BIG`. La référence utilise maintenant une lecture sur demande, sans élargir le bundle commun. Le test Cursor ciblé passe après cette correction. Aucun code du runtime n'a été modifié.

## Expérience native exécutée

La fixture transmet trois briefs successifs à trois workers neufs, sans historique parent. A analyse des cents, B formate un montant CAD en consommant A, C construit une facture en consommant B. Les deux variantes utilisent les mêmes décisions, sources et assertions positives et négatives. Les commandes compilent les trois fichiers Python puis exécutent les trois contrôles d'intégration.

Les briefs sont produits par le vrai générateur de la base et celui de la candidate. Six acteurs neufs ont exécuté les tranches, sans historique parent : `/root/maple_amount`, `/root/maple_label`, `/root/maple_invoice`, puis `/root/pine_amount`, `/root/pine_label`, `/root/pine_invoice`. Ils ont reçu des dossiers aux noms neutres et leur seul brief. Chaque acteur a exécuté son contrôle avant et après l'écriture : module absent, puis réussite. Le coordinateur a ensuite compilé les trois fichiers et exécuté les trois contrôles positifs et négatifs pour chaque variante. Tous passent ; aucune erreur d'intégration ni question produit n'a été observée.

Les trois acteurs baseline ont signalé à tort une divergence entre le SHA du fichier spec et l'empreinte du brief. Celle-ci représente le jeu de sources entier. Le libellé a été précisé dans la candidate, ainsi que la base des chemins de décisions. Aucun acteur candidat n'a rapporté cette fausse divergence. Il s'agit d'un écart observé de compréhension, distinct des contradictions refusées mécaniquement à l'import.

| Mesure | Baseline | Candidate |
| --- | ---: | ---: |
| Octets des trois briefs | 3482 | 6667 |
| Octets des prompts transmis, enveloppe comprise | 5351 | 8533 |
| Acteurs de construction neufs | 3 | 3 |
| Erreurs d'intégration finales | 0 | 0 |
| Questions produit | 0 | 0 |

Ces tailles décrivent la campagne initiale enregistrée au commit `4a4c17c`, avant la correction du rendu multiligne ci-dessous. Elles ne mesurent pas la taille des briefs corrigés.

Les deux variantes ont relu la spec et les unités selon leurs rapports. Aucune baisse des relectures n'est démontrée ; les lectures internes ne sont pas instrumentées. Les contrats augmentent ici le texte transmis. Ce résultat préserve la qualité de la baseline et ajoute les refus avant dispatch, sans établir d'économie de contexte. Durées, tokens et coûts monétaires restent inconnus. Le [reçu d'intégration](task-contracts-native.json) conserve acteurs, tailles et résultats réellement exécutés.

Le contrôle complet `bash scripts/check.sh` passe après la correction du bundle. `review_contracts`, acteur indépendant en lecture seule, a relu le diff et exécuté les 85 tests Orchestrate sans échec. Les tests mécaniques couvrent l'import, les dépendances et la dérive ; l'essai natif couvre la consommation des briefs et les fichiers construits. Il ne prétend pas mesurer un ordonnancement autonome complet d'Orchestrate.

La PR dépend de #94, encore en brouillon avec ses propres limites de livraison. Ce travail n'en efface ni le gate TDD déclaré ni l'indisponibilité de la CI distante. La modification du format porte sur cette branche non publiée ; aucune migration silencieuse d'anciens magasins n'est ajoutée.


## Corrections de revue de PR105

Deux défauts ont été reproduits avant correction. Un contrat pouvait citer `spec.md` alors que seul `approved-plan.md` avait été chargé. Deux listes distinctes, `["a\nb", "c"]` et `["a", "b\nc"]`, devenaient le même texte lorsque leurs valeurs étaient concaténées par des retours à la ligne.

La source directe d'une décision correspond maintenant au nom réel du fichier chargé. Le brief conserve chaque liste dans un tableau JSON, avec échappement des retours à la ligne. Les tests vérifient le refus de la source fictive, l'acceptation de la source réelle et l'aller-retour exact des deux listes. Le passage rouge compte 17 tests réussis et 4 échecs attendus, dont l'ancien test d'espaces adapté au format de restitution. Après correction, les 88 tests Orchestrate passent.

La demande de compatibilité avec les handoffs de #94 concerne un format encore non publié. Lors de cette revue, `main` distant vaut `312ef0b81c0755f57d3462e3e4806a854cc5cef0` et ne contient pas `orch/horizon.ts`. La PR94 est ouverte en brouillon et le plugin installé 0.8.0 ne contient pas non plus cet adaptateur. Les fichiers incomplets de la branche expérimentale restent refusés explicitement ; aucune migration, réécriture d'état ou réutilisation silencieuse de preuves n'est ajoutée.


Le worker natif neuf `/root/explore_contract_review/cedar_values`, lancé sans historique parent, reçoit le brief contenant les deux tableaux. Son fichier `received.json` restitue exactement `{"first":["a\nb","c"],"second":["a","b\nc"]}`. Le parent compare les chaînes décodées et leurs frontières, puis exécute `python3 -m json.tool` avec sortie 0. Le [reçu ciblé](task-contracts-review-native.json) conserve la sortie, l'empreinte et la taille du brief. Les lectures internes et les coûts ne sont pas instrumentés. Cette sonde complète la campagne initiale ; elle ne répète pas les six constructions.

Le contrôle complet `bash scripts/check.sh` est relancé sur ce correctif et termine avec le code 0 : 245 tests Python dont un ignoré, 29 tests Bun racine et 286 tests helpers. Les vérifications de types et de lint passent également.

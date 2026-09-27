---
name: blast-radius
description: "Trouve ce qu'un changement pourrait casser ailleurs avant livraison, au-delà du diff, et prouve par du vrai code le fait qui le rend sûr. Utiliser pour $cstack:blast-radius, 'rayon d’impact de X', 'qu’est-ce que cela pourrait casser', ou la revue d'un petit diff douteux."
---

# Rayon d'impact

Runtime : [règles communes](../cstack/references/runtime/base.md), [intégrations](../cstack/references/runtime/integrations.md).

Trouve ce qu'un changement casse ailleurs avant qu'il parte en livraison. Utilise pour "rayon d’impact de X", "qu’est-ce que cela pourrait casser", ou la revue d'un petit diff auquel tu ne fais pas encore confiance.

Compagnon de `how` et `why`. `how` te dit ce que fait le code. `why` te dit pourquoi il a cette forme. Le rayon d'impact te dit ce qu'il casse ailleurs.

Lister les appelants n'est pas le travail. Le travail, c'est la casse que grep ne te montrera pas.

## Ne fais pas confiance à ton propre compte rendu

Un compte rendu de rayon d'impact qui sonne juste ne vaut rien. Il paraît convaincant qu'il soit vrai ou non. Ne rends donc pas seulement le compte rendu. Trouve les un ou deux faits dont tout dépend et prouve-les en exécutant du code.

### A quel point es-tu sur

Pour chaque fait dont dépend la sécurité du changement, descends aussi bas que possible dans cette liste à faible coût, puis dis ou tu t'es arrête.

1. Tu l'as dit. Sans plus, ça ne vaut rien.
2. Tu as pointe la ligne. Un vrai `file:line`, ou la source propre de la bibliothèque.
3. Tu as montre que le mauvais cas ne peut pas arriver. Tu as suivi l'échec étape par étape et il n'atteint pas ce point.
4. Tu l'as exécute. Un script ou test appelle le vrai code et échoue clairement si tu te trompes.
5. Tu l'as reproduit dans l'application en cours d'exécution.

Tout fait de sécurité que tu ne peux pas amener à l'étape 4 doit être declare comme tel. Ne le présente pas comme établi. L'étape 4 est habituellement un petit script qui importe la même bibliothèque que celle livree par l'app et appelle exactement la fonction qui t'inquiete.

## Etapes

1. Lis le changement. Le diff, les symboles qu'il ajoute, modifie et supprime, et ce qu'il fait maintenant différemment, y compris la partie que le diff n’explicite pas. Utilise l'étape 2 de `why` pour récupérer la PR et les commits.
2. Trouve le fait unique qui le rend sûr. La plupart des changements qui ont l'air risqués sont sûrs grâce à un seul fait, par exemple "cet appel supprime seulement des entrées de cache déjà mortes et ne fait rien d'autre". Trouve ce fait. S'il tient, la plupart des cas risqués sont écartés d'un coup. Passe ton temps ici, pas sur une longue liste de peut-être.
3. Regarde là où grep s'arrête. Lis la source de la bibliothèque que tu appelles, puis vérifie sa version épinglée et tout patch local. Comprends quand les choses s'exécutent : microtâches, unmount et teardown, Solid versus React. Suis ce qu'une recherche de symbole manque : le JSON renvoyé par une API, une colonne DB, un format réseau, un autre langage qui lit les mêmes octets, un feature flag, du code trois sauts plus loin.
4. Sois honnête sur chaque risque. Donne-lui une vraie probabilité d'arriver et un vrai coût si ça arrive. Garde les risques confirmés. Liste séparément ceux que tu as vérifiés et écartés. Mêmes règles que `why`. Cite un vrai `file:line`; une recherche qui ne trouve rien est quand même une réponse, et n'invente jamais un appelant ou une API.
5. Prouve le fait unique. Écris un script ou un test qui exécute le vrai code, lance-le, puis colle ce qui s'est passe. Si tu ne peux pas le prouver à faible coût, marque-le non prouvé. N'exagere pas.
6. Pour un changement gros ou large, passe-le dans `$cstack:arena`. Pose la même question à des relecteurs indépendants et fusionne les réponses. Une diversite de modèles vérifiée peut ajouter de la couverture, mais elle n'est pas requise.

## Ce qu'il faut rendre

- **Ce qu'il fait.** Ce qui a changé, y compris la partie qui n'est pas évidente.
- **Le fait unique qui le rend sûr.** Énonce-le, dis jusqu'à quelle étape tu l'as amené, et montre la preuve. Si tu n'as pas pu le prouver, écris non prouvé.
- **Risques.** Seulement les vrais. Chacun nommé comment ça casse, le `file:line`, sa probabilité, sa gravité et comment vérifier. Colle la preuve pour ceux qui comptent.
- **Ecartes.** Ce que tu as vérifie et pourquoi c'est correct.
- **Avant de merger.** Le test ou la repro la moins chère qui attrape le vrai bug, y compris le script que tu as écrit.

Passe-le par `unslop`, cite du vrai code et retire tout élément privé avant que ça parte dans un endroit public.

**Réponse :** le compte rendu ci-dessus, avec le fait de sécurité unique prouvé ou marqué non prouvé. Chaque affirmation porte sa preuve ou son étiquette dans la même phrase. Mesure, inférence ou supposition. Une prédiction ou une cause non observée est une supposition. Ne donne jamais à l'humain une vérification que tu pourrais exécuter.

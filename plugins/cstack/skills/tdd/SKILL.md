---
name: tdd
description: "À utiliser pour $cstack:tdd sur les bugs et les nouvelles fonctionnalités qui ajoutent ou modifient un comportement, même petites. Écrit d'abord un test qui échoue, puis le fait passer ; exempte les changements sans effet comportemental, et toute impossibilité réelle exige une exception motivée et une vérification alternative exécutée."
---

# Bugs et fonctionnalités en TDD

Runtime : [règles communes](../cstack/references/runtime/base.md), [délégation](../cstack/references/runtime/delegation.md).

Pour chaque bug ou comportement nouveau ou modifié, écris et exécute un test qui échoue pour la raison attendue avant de modifier le code de production. Fais-le ensuite passer avec le plus petit changement utile.

## Choisir le parcours

- **Comportement modifié :** TDD, y compris logique métier, validation, API et interactions UI testables.
- **Aucun comportement modifié :** documentation, texte, formatage ou présentation pure peuvent être exemptés. Nomme la raison et exécute les contrôles pertinents. Une modification d'interaction, de permission ou de validation ne devient pas exemptée parce qu'elle touche peu de lignes ou un fichier Markdown.
- **TDD réellement impraticable :** avant l'implémentation, consigne la contrainte concrète et la vérification alternative choisie. L'absence de demande explicite de TDD, la petite taille ou la seule volonté d'aller vite ne justifient pas une exception. Réutilise un test ou une reproduction exécutable existants avant de conclure à l'impossibilité.

## Cycle rouge → vert

1. Identifie le comportement attendu et la plus petite vérification observable. Pour une fonctionnalité, le test décrit le comportement à ajouter ; pour un bug, il reproduit le défaut.
2. Écris le test avec les outils du projet. Teste le comportement, pas la structure interne ni un mock qui répète sa propre entrée.
3. Exécute-le **avant** le changement de production. Garde la commande et sa sortie d'échec dans les preuves de tâche. Confirme la raison : une dépendance absente, un environnement cassé ou une erreur de syntaxe sans rapport ne constituent pas le rouge attendu.
4. Implémente le minimum nécessaire pour satisfaire le test sans affaiblir ses assertions.
5. Relance le même test et garde la commande et sa sortie passante. Puis lance les contrôles voisins pertinents et simplifie en conservant les tests verts.
6. Répète par comportement. N'écris pas toute l'implémentation avant de construire les tests. Un test ajouté après coup peut prouver une régression, mais ne prouve pas que le développement a suivi le TDD ; ne reconstitue pas une chronologie fictive.

Si le builder ne dispose pas des outils pour exécuter les tests, le coordinateur les lance et lui transmet la preuve rouge avant le changement de production, puis la preuve verte après. L’absence de shell chez un worker CLI ne justifie pas, à elle seule, une exception au TDD.

## Exceptions et vérifications alternatives

Une exception explique ce qui empêche réellement le cycle test-first : infrastructure indisponible, reproduction uniquement sur un système inaccessible ou test qui exigerait une simulation sans rapport avec le comportement. Elle nomme une vérification concrète : commande de reproduction, scénario navigateur, test d'intégration, comparaison de sorties ou inspection de l'artefact pertinent.

Exécute cette vérification et conserve son résultat. Si aucun contrôle pertinent ne peut aboutir, rapporte le blocage et ne déclare pas la livraison prête. Si l'absence de preuve rouge n'est découverte qu'après l'implémentation, rapporte le manquement ; une simple déclaration rétrospective ne vaut pas exception justifiée.

## Preuve et livraison

Le builder transmet au coordinateur l'un des parcours suivants, avec les chemins des preuves :

- **TDD :** comportement, test, commande et échec observé avant implémentation, puis commande et réussite après ; contrôles voisins.
- **Hors TDD :** absence d'effet comportemental, ou exception motivée, avec vérification alternative effectivement exécutée et résultat.

Le coordinateur et le reviewer examinent ces preuves avant de déclarer le travail prêt pour PR ou merge. **Bloque la livraison si ni le cycle rouge → vert ni le parcours hors TDD justifié et vérifié ne sont établis.** « Tests OK » ou une CI verte ne prouvent pas l'ordre test-first.

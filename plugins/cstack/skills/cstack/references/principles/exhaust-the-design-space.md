# Épuiser l'espace de conception

Lisez cette référence lorsqu'un processus cstack actif vous route ici ou lorsque l'utilisateur nomme ce principe. Suivez le [contrat d'exécution Codex](../codex-runtime.md) pour le périmètre et les permissions.

Lorsqu'une interaction nouvelle ou une décision architecturale n'a pas de précédent établi, explorez plusieurs alternatives concrètes avant l'implémentation. Construire la mauvaise chose coûte plus cher qu'explorer trois options.

**La règle.** Quand la bonne réponse n'est pas évidente, construisez 2 ou 3 prototypes ou croquis concurrents. Comparez-les côte à côte. Commitez seulement ensuite. « Le concevoir deux fois » est un autre nom pour cette règle. Une deuxième saveur de la première forme ne compte pas.

**Quand cela s'applique :**
- Interactions UI nouvelles (aucun précédent dans la base de code)
- Choix architecturaux avec plusieurs approches viables
- Décisions de conception produit où l'expérience utilisateur dépend du ressenti, pas de la logique

**Quand cela ne s'applique pas :**
- Implémentation mécanique où le motif est établi
- Corrections d'anomalies ou refactorisations avec un état cible clair
- Changements où les contraintes imposent une seule approche viable

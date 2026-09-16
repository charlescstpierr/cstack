# Modéliser le domaine

Lisez cette référence lorsqu'un processus cstack actif vous route ici ou lorsque l'utilisateur nomme ce principe. Suivez le [contrat d'exécution Codex](../codex-runtime.md) pour le périmètre et les permissions.

Encodez le vrai domaine dans une structure de données au lieu de le disperser entre des conditionnelles.

**Pourquoi :** les booléens dispersés, hypothèses de forme répétées et branchements éparpillés entre fichiers sont de la complexité accidentelle. Une structure qui correspond au domaine rend les états invalides irreprésentables et supprime des branches. La choisir à l'écriture est bon marché. La récupérer plus tard ressemble à une refactorisation et se fait reporter.

**Cherchez des structures comme celles-ci :**

- Une machine à états au lieu de booléens, phases ou contrôles de cycle de vie dispersés.
- Un objet/modèle typé au lieu de paramètres lâches ou d'hypothèses de forme répétées.
- Une map, un registre, une table de recherche ou une union discriminée au lieu de branchements éparpillés entre fichiers.
- Un modèle reducer ou commande/événement au lieu de mutations d'état ad hoc.
- Un module organisé autour d'un corps de connaissances de domaine au lieu d'une séquence comme charger, valider, transformer et sauvegarder. L'ordre d'exécution n'est pas la propriété.
- Une petite frontière de module qui rassemble comportement répété, propriété ou invariants.
- Une file, un cache, un index, un graphe/arbre ou une collection normalisée lorsque le motif d'accès aux données l'exige.
- Toute autre structure qui convient. Quand aucune ne convient, déterminez ce que le code ne doit jamais permettre et comment les données sont lues, puis trouvez la structure qui encode exactement cela.

Ne forcez pas une abstraction. Préférez le code banal si la forme courante est déjà claire, locale et peu susceptible de grossir. Méfiez-vous d'une abstraction qui ajoute de l'indirection sans retirer de branches, de règles dupliquées, d'états invalides ou de risques de cycle de vie.

Le signe que vous avez sauté ceci est une nouvelle fonctionnalité qui ajoute une branche de plus à une chaîne if/else existante, ou un deuxième booléen qui doit rester synchronisé avec le premier. La décomposition temporelle est un autre signe. Les modules nommés par phase répètent les mêmes règles de domaine entre étapes.

# Pensée fondationnelle

Lisez cette référence lorsqu'un processus cstack actif vous route ici ou lorsque l'utilisateur nomme ce principe. Suivez le [contrat d'exécution Codex](../codex-runtime.md) pour le périmètre et les permissions.

**Les décisions structurelles** protègent la valeur d'option. **Les décisions au niveau du code** protègent la simplicité.

**Les structures de données d'abord.** Obtenez la bonne forme de données avant d'écrire la logique. Définissez tôt les types centraux, tracez chaque motif d'accès et choisissez des structures qui correspondent aux chemins dominants.

Au niveau du code, appliquez DRY à la structure, pas à chaque ligne. Les types et modèles de données doivent converger. Trois instructions similaires battent encore une abstraction prématurée. Préférez l'explicite au malin. Testez le comportement et les cas limites, pas le nombre de lignes.

**Corollaire de concurrence.** Avant de partager de l'état entre acteurs, demandez « que se passe-t-il si un autre acteur modifie ceci en même temps ? ». Si la réponse n'est pas « rien », isolez.

**Échafauder d'abord.** Si quelque chose aide toutes les phases ultérieures, faites-le d'abord. Demandez « chaque phase suivante profite-t-elle du fait que cela existe ? ». CI, linting, infrastructure de tests et types partagés sont de l'échafaudage. Séquencez pour la valeur d'option : configuration avant fonctionnalités, tests avant correctifs. Gardez les commits petits et à objectif unique.

Chaque incrément doit livrer une abstraction cohérente ou approfondir une abstraction existante. Ne dispersez pas une nouvelle capacité entre appelants comme coordination au cas par cas.

La soustraction vient avant l'échafaudage. Retirez d'abord le code mort, puis posez les fondations.

# Minimiser la charge du lecteur

Lisez cette référence lorsqu'un processus cstack actif vous route ici ou lorsque l'utilisateur nomme ce principe. Suivez le [contrat d'exécution Codex](../codex-runtime.md) pour le périmètre et les permissions.

La maintenabilité est le travail qu'un lecteur doit faire pour comprendre le code. Suivez deux axes :
1. **Couches à suivre.** Combien d'indirections se trouvent entre la question et la réponse.
2. **État à retenir.** Combien de contexte caché ou mutable le lecteur doit garder en tête.

**Pourquoi :** le code est lu bien plus qu'il n'est écrit. LOC, complexité cyclomatique et « clean architecture » sont des proxys. La charge du lecteur est ce qui compte. Les deux axes sont indépendants. Un fichier plat avec 50 globales peut être aussi difficile à raisonner qu'une pile d'adaptateurs à 6 couches. Gardez les deux. C'est l'analogue humain de [Garder la fenêtre de contexte](guard-the-context-window.md). La mémoire de travail est finie pour les lecteurs aussi.

**Le motif :**
- **Réduisez les couches** qui coûtent plus qu'elles ne rapportent : wrappers avec un seul appelant, adaptateurs sans deuxième implémentation, indirection spéculative qui n'a jamais été nécessaire. Inlinez-les.
- **Faites changer l'abstraction par les couches adjacentes.** Une couche qui répète les mêmes méthodes et arguments ajoute de la charge lecteur sans compression. Réduisez les couches pass-through.
- **Exigez une compression d'interface.** Une interface large qui cache peu de complexité force les lecteurs à apprendre à la fois la surface et l'implémentation. Préférez les frontières qui cachent des décisions significatives.
- **Réduisez le périmètre d'état :** préférez les fonctions pures (retours plutôt que mutations), les locales aux champs, les champs à l'état de module, et l'état de module aux globales. Dérivez au lieu de synchroniser.
- **Nommez l'invariant à la frontière,** pas dans chaque consommateur, afin que le lecteur l'apprenne une seule fois.
- Avant d'ajouter une couche ou un morceau d'état, demandez : cela réduit-il la charge lecteur ailleurs au moins autant ?

**Le test :** un nouveau lecteur peut-il répondre à « d'où vient X ? » et « qu'est-ce qui peut changer X ? » en moins de 30 secondes ? Sinon, coupez des couches ou coupez de l'état.

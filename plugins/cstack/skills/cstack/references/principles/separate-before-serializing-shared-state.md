# Séparer avant de sérialiser l'état partagé

Lisez cette référence lorsqu'un processus cstack actif vous route ici ou lorsque l'utilisateur nomme ce principe. Suivez le [contrat d'exécution Codex](../codex-runtime.md) pour le périmètre et les permissions.

Lorsque des acteurs concurrents pourraient partager un état mutable, demandez d'abord s'ils ont besoin du même objet mutable. Sinon, éliminez le partage. Quand le partage est réel, imposez la sérialisation structurellement : fichiers de verrou, phases séquentielles, propriété exclusive. Les instructions et conventions ne sont pas du contrôle de concurrence.

**Pourquoi :** les écritures concurrentes dans un état partagé créent des conditions de course intermittentes, difficiles à reproduire et coûteuses à déboguer.

**Motif :**
1. **Identifier l'état mutable partagé** (fichiers à la fois lus et écrits, branches où les deux poussent, API à la fois définies et consommées).
2. **Par défaut : éliminer la cible d'écriture partagée.** Demandez : ces acteurs ont-ils besoin d'un objet canonique unique, ou publient-ils des faits indépendants ? Donnez à chaque acteur son propre fichier, clé, branche ou répertoire d'état, et fusionnez seulement à la frontière de lecture/rapport. Deux workers qui écrivent leur propre champ `lastX` dans un seul `state.json` font encore une mutation partagée. `indexer-state.json` + `metrics-state.json` ne le font pas.
3. **Seulement lorsqu'une cible d'écriture partagée est un vrai invariant, sérialiser l'accès structurellement** (fichiers de verrou, phases séquentielles, acteur écrivain unique ou compare-and-swap atomique). Traitez « il nous faut un verrou » comme une odeur de conception à vérifier, pas comme la réponse par défaut.

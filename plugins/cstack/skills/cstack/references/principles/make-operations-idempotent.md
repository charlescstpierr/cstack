# Rendre les opérations idempotentes

Lisez cette référence lorsqu'un processus cstack actif vous route ici ou lorsque l'utilisateur nomme ce principe. Suivez le [contrat d'exécution Codex](../codex-runtime.md) pour le périmètre et les permissions.

Concevez les opérations pour qu'elles convergent vers l'état correct, peu importe combien de fois elles s'exécutent ou d'où elles partent. Chaque opération qui mute l'état doit répondre : « Que se passe-t-il si ceci s'exécute deux fois ? Que se passe-t-il si l'exécution précédente a crashé à mi-chemin ? »

**Pourquoi :** les commandes, opérations de cycle de vie et boucles de traitement s'exécutent là où les crashs, redémarrages et tentatives sont normaux. Si un changement d'état partiel modifie le résultat de l'exécution suivante, chaque redémarrage devient une session de débogage.

**Le motif :**
- Démarrage convergent : scanner l'état existant, nettoyer les artefacts périmés, adopter les sessions vivantes
- Nettoyage basé sur le contenu : comparer par équivalence de contenu, pas par ordre de création
- Verrous autoréparateurs : utiliser la détection de verrous périmés basée sur les PID
- Planification idempotente : le travail échoué renaît proprement, l'entrée fraîche est régénérée après chaque cycle

**Le test :**
1. Que se passe-t-il si ceci s'exécute deux fois d'affilée ?
2. Que se passe-t-il si l'exécution précédente a crashé à chaque point possible ?
3. La réexécution converge-t-elle vers le même état final ?

Si une réponse est « cela dépend de l'état laissé derrière », l'opération a besoin d'une étape de réconciliation.

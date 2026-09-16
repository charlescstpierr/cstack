### Forensique exécution

Suivez [le contrat d’exécution Codex](../references/codex-runtime.md).

**Tu possèdes le diagnostic. Instrumente le processus vivant, ne théorise pas depuis la source.** Le livrable est un diagnostic cité, pas un correctif.

1. Capture le signal vivant avec un navigateur, simulateur, profileur ou outil terminal natif disponible. Utilise un profil CPU pour un processus qui boucle, un heap snapshot pour une fuite, ou une trace navigateur pour une anomalie visuelle. Capture un vrai artéfact.
2. Réduis l’artéfact à la pièce décisive : la fonction sur le chemin chaud, la chaîne de rétention de l’objet fuité vers une racine GC, la boucle qui se déclenche sans entrée. Parse les grands artéfacts dans un sous-agent (référence du principe [Protéger la fenêtre de contexte](../references/principles/guard-the-context-window.md)), garde le constat réduit dans le fil principal.
3. Prouve le mécanisme. Utilise l’évaluation exécution disponible ou une instrumentation temporaire pour confirmer l’hypothèse avec le plus petit changement réversible.
4. Rattache le constat à la source : fichier, symbole, ligne qui alloue ou planifie.
5. Le point de contrôle de débit reste sur une ligne : `throughput checkpoint: n/a, read-only forensics`.

**Réponse :** le signal capturé, le constat réduit, comment tu as prouvé le mécanisme, l’emplacement source, les chemins d’artéfact. Pas de correctif sauf demande. Repasse à Bug fix ou Perf une fois la cause connue. Chaque affirmation porte sa preuve ou son étiquette dans la même phrase. Mesuré, inféré ou supposition. Une prédiction ou une cause non observée est une supposition. Ne remets jamais à l’humain un contrôle que tu pourrais lancer.

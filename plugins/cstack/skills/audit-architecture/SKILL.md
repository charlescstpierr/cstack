---
name: audit-architecture
description: "Mène un audit d'architecture brownfield borné et en lecture seule, qui trouve des pistes d'approfondissement étayées sans refactorer. Utiliser pour $cstack:audit-architecture ou quand l'utilisateur demande quelle architecture devrait être améliorée."
---

# Auditer l'architecture

Runtime : [règles communes](../cstack/references/runtime/base.md), [exploration](../cstack/references/runtime/exploration.md), [délégation](../cstack/references/runtime/delegation.md), [modèles](../cstack/references/runtime/modeles.md) · rôle : `how explorer` (explorateurs).

Examine le code existant pour trouver des améliorations architecturales utiles. Cette skill trouve et compare des candidats; elle ne reconçoit pas et ne refactore pas le code.

## Portée et exploration

1. Utilise comme portée le sous-système ou les chemins nommés par l'utilisateur. S'il n'en nomme aucun, inspecte un historique récent borné (`git log --oneline -20`) et suis les fichiers et zones qui changent activement. Énonce la portée avant de scanner.
2. Lis le code réel, les appelants, les tests, la configuration et les consignes de projet pertinentes dans cette portée. N'infère pas un candidat depuis les noms de fichiers ou des conseils d'architecture génériques.
3. Pour la carte initiale, établis les faits directement ou applique le [contrat d’exploration déléguée](../cstack/references/runtime/exploration.md) si une couverture séparée est utile. Donne à chaque explorateur sa portée et demande chemins, symboles, appelants, points chauds et preuves; ils ne doivent pas modifier de fichiers, lancer de descendants ni proposer de refactor.
4. L'agent principal synthétise les résultats des explorateurs avec son inspection directe. Un résumé délégué n'est pas une preuve tant que le code cité n'a pas été lu.

## Standard d'un candidat

Un candidat doit nommer :

- les chemins et symboles touchés;
- le problème et la friction actuelle, avec des preuves `path:line` et les appelants pertinents;
- le test de suppression : si retirer le module proposé concentrerait la complexité derrière une interface plus petite ou ne ferait que la déplacer;
- la profondeur d'interface : ce que les appelants savent aujourd'hui, ce qu'une frontière proposée cacherait, et quels invariants ou politiques gagneraient en localité;
- une recommandation : `Strong`, `Worth exploring`, `Speculative` ou `No worthwhile candidate`;
- une esquisse avant/après plausible étiquetée **proposé, non vérifié**.

Utilise les termes existants du domaine. Garde les candidats liés au code observé et accepte de conclure qu'il n'y a aucun candidat utile. N'invente pas un second adaptateur, un appelant, un invariant, un gain de performance ou une raison historique.

Le rapport par défaut est du Markdown dans la conversation. En mode Plan ou lors d'une demande qui interdit les écritures de fichiers, garde le rapport dans le chat et ne crée aucun artefact. Sinon, crée un artefact de rapport seulement quand l'utilisateur demande ou autorise cette sortie; les sources et la configuration restent en lecture seule. N'exige pas de navigateur, CDN, Mermaid, `xdg-open` ou capture d'écran; utilise un navigateur disponible seulement quand l'utilisateur demande explicitement une inspection visuelle et que l'outil existe.

## Limites strictes

Cette exécution est en lecture seule. Ne modifie pas les sources, les tests, `AGENTS.md`, `CONTEXT.md`, les ADR, `.cstack/` ou la configuration. Ne crée pas de branches, commits, PR, messages, installations, dépendances ou travaux en arrière-plan. N'applique pas automatiquement un candidat et ne démarre pas de playbook de refactorisation.

Si l'utilisateur choisit un candidat, transmets les preuves et contraintes à `$cstack:architect`. Garde le résultat en conception seulement, sauf si l'implémentation a déjà été explicitement autorisée dans la même tâche. Laisse Architect préserver le nombre de panels `architect runners` configuré et chaque sélection de modèle/effort de raisonnement; n'ajoute pas de taille de panel fixe et ne substitue pas un autre moteur de reconception.

Les outils manquants sont des manques de preuve à signaler, jamais des raisons de fabriquer des résultats.

Chaque affirmation porte sa preuve ou son étiquette dans la même phrase. Mesure, inférence ou supposition. Une prédiction ou une cause non observée est une supposition. Ne donne jamais à l'humain une vérification que tu pourrais exécuter.

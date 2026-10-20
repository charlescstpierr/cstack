### Correction de bug

Suivez [le contrat d’exécution Codex](../references/codex-runtime.md).

**Tu possèdes cette tâche. Planifie, relis, vérifie.** Choisis l’ancrage et l’auteur selon le [parcours proportionné](../references/runtime/parcours-court.md).

Sois scientifique. Chaque ligne livrée remonte à une preuve exécution. Un double garde-fou qui « pourrait aider » est une hypothèse, pas un correctif. Il ne part pas en livraison. Quand les preuves réfutent une hypothèse, rétablis ce qu’elle a motivé. Le plus petit changement justifié par les preuves part en livraison, rien de plus.

1. Reproduis-le sur la vraie interface avec les outils natifs disponibles. Pour un navigateur ou une app en cours d’exécution, utilise un outil navigateur ou simulateur quand la session en expose un. Pour une CLI, lance la commande dans un terminal. Si aucun outil natif n’atteint la cible, pousse la reproduction aussi loin que possible et indique l’écart précis. Synthétise le déclencheur ou ajoute de l’instrumentation avant de demander à l’utilisateur de le reproduire.
2. Recherche la cause par dichotomie. Hors parcours court, lis et applique `../../how/SKILL.md` sur le sous-système touché et `../../why/SKILL.md` pour l’historique de régression. Ventile l’ancrage selon la règle plus bas. Écarte les hypothèses avec des preuves exécution. Ajoute de l’instrumentation quand l’état est flou. Continue une chasse difficile au premier plan. Confirme le mécanisme survivant avant la revue de conception.
3. Avant de modifier le comportement, applique `../../tdd/SKILL.md`. Pour une édition déléguée, transmets au builder la preuve rouge → vert attendue ou son parcours d’exception motivée et vérifiée. Planifie le correctif. S’il traverse une frontière de fonction, lis et applique d’abord `../../architect/SKILL.md`. Hors parcours court, délègue une implémentation bornée. Préserve le rôle choisi par l’appelant, y compris `simple edits` pour les petits changements bornés. Utilise `feature, refactoring` quand aucun rôle n’a été sélectionné. Suis le contrat d’exécution pour l’héritage ou le modèle et l’effort configurés. Relis le diff. Pour une capacité manquante, applique [Orchestration requise](../references/runtime/orchestration.md).
4. Vérifie sur la même surface. La repro originale passe maintenant. « Inconclusive » ou une mauvaise surface n’est pas une réussite. Signale-le. Les tests unitaires montrent le comportement de branche, pas l’absence de bug.
   Quand cette vérification compare deux rapports d'observations, applique [Comparer des observations de contrôles](../references/regression.md) avant de conclure.
5. Rassemble les preuves du parcours TDD retenu. En cycle rouge → vert, stage les commits pour que la reproduction échouante précède le correctif dans l’historique.
   C’est la référence canonique du principe [Séquencer le travail en unités vérifiables](../references/principles/sequence-verifiable-units.md), le test échouant d’abord et le correctif au-dessus. Lance `../../deslop/SKILL.md` sur le diff avant chaque commit. Garde `deslop skipped: <reason>` quand une étape ne peut vraiment pas s’exécuter.
6. Lance **Ouvrir une PR** selon la portée de livraison du contrat d’exécution.

Quand le parcours requiert `how`, exécute son ancrage dans la session qui possède la ventilation, selon le [contrat d'exploration déléguée](../references/runtime/exploration.md). Délègue ses angles plutôt que la compétence entière à une feuille sans descendants. Les recherches `why` indépendantes peuvent avancer en parallèle sous le même coordinateur.

**Réponse :** ce qui était cassé, la cause racine, le correctif, comment tu as vérifié. Colle mot pour mot la sortie de repro échouante puis passante. Chaque affirmation porte sa preuve ou son étiquette dans la même phrase. Mesuré, inféré ou supposition. Une prédiction ou une cause non observée est une supposition. Ne remets jamais à l’humain un contrôle que tu pourrais lancer.

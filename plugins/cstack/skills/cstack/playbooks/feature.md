### Fonctionnalité

Suivez [le contrat d’exécution Codex](../references/codex-runtime.md).

**Tu possèdes la conception. Planifie, relis, vérifie.** Délègue l’implémentation. Reste en tête.

1. Lis et applique `../../how/SKILL.md` sur le sous-système touché. L’ancrage `how` ventile par défaut 2 à 4 explorateurs parallèles, dans la limite de la concurrence native ; la passe unique exige un test nommé de son Étape 1.
2. Lis et applique `../../architect/SKILL.md` pour l’exploration de conception. Limite le nombre de exécutants de conception simultanés à la capacité native et mets le reste en file. Garde `architect skipped: <reason>` quand l’étape ne mérite pas son coût.
3. Écris le point de contrôle de débit comme quatre todos. Une dimension qui ne s’applique vraiment pas (fichier unique, pas de ventilation) garde son item avec `n/a: <reason>` au lieu d’être supprimée :
   - **Premières étapes bloquantes.** Les barrières passent avant la ventilation.
   - **Flux de travail indépendants.** Les fichiers, services ou couches disjoints se parallélisent. Les écritures partagées se sérialisent.
   - **État mutable partagé.** Par défaut, diviser la cible (référence du principe [Séparer avant de sérialiser l’état partagé](../references/principles/separate-before-serializing-shared-state.md)). Sérialiser seulement pour de vrais invariants.
   - **Plus petite décomposition sûre.** Si un seul worker est préférable, nomme pourquoi.
4. Délègue l’écriture du code. Relis toi-même le diff. Donne au délégué la propriété des fichiers, la forme de données nommée, sa structure organisatrice et les critères de réussite. Préserve le rôle choisi par l’appelant, y compris `simple edits` pour les petits changements bornés. Utilise `feature, refactoring` seulement quand aucun rôle n’a été sélectionné. Suis le contrat d’exécution pour l’héritage ou le modèle et l’effort configurés. Quand l’implémentation admet plusieurs formes valides (gestion d’erreurs, couche d’abstraction, structure de tests), lis et applique `../../arena/SKILL.md`. Obligatoire : aucune échappatoire skip-with-reason, et Protocole de paresse ne le remplace pas. Applique [Orchestration requise](../references/codex-runtime.md#orchestration-requise) avant d’exécuter ou de déléguer le travail qui en dépend. Garde des éditions chirurgicales. Ré-ancre les fichiers dérivés de l’amont contre leur source. Applique les améliorations partagées à chaque consommateur et vérifie chacun. Lance `../../deslop/SKILL.md` sur le diff avant chaque commit. Garde `deslop skipped: <reason>` quand une étape ne peut vraiment pas s’exécuter.
5. Vérifie sur la surface correspondante. « Inconclusive » ou une mauvaise surface n’est pas une réussite. Signale-le.
6. Rebase en petits commits ordonnés. Empile les suivis.
   Utilise la référence du principe [Séquencer le travail en unités vérifiables](../references/principles/sequence-verifiable-units.md), en construisant, vérifiant et committant chaque petite unité avant la suivante.
7. Si la conception est contestée, `interrogate` avant livraison.
8. Lance **Ouvrir une PR** selon la portée de livraison du contrat d’exécution.

Le travail couplé au code va à un seul propriétaire avec le point de reprise inline. Ne ventile que les artéfacts indépendants, comme des audits, investigations inter-sous-systèmes ou expériences concurrentes. Réécris le point de reprise aux frontières de phase. Donne au travail de suivi un brief complet au lieu de dépendre d’un contexte perdu.

**Réponse :** ce que tu as construit, ce que tu as choisi et pourquoi, le point de contrôle de débit, les décisions ouvertes. Tableaux pour les alternatives de conception. Chaque affirmation porte sa preuve ou son étiquette dans la même phrase. Mesuré, inféré ou supposition. Une prédiction ou une cause non observée est une supposition. Ne remets jamais à l’humain un contrôle que tu pourrais lancer.

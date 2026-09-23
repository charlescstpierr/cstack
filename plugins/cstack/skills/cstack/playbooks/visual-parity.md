### Parité visuelle

Suivez [le contrat d’exécution Codex](../references/codex-runtime.md).

**Tu possèdes l’équivalence exacte au pixel. La référence est la spécification. Tu n’y touches pas.** L’équivalence se vérifie par diff d’image, pas à l’œil.

1. Établis d’abord la référence, avant toute migration : un harnais de régression visuelle qui capture le composant courant dans ses états, plus la cible quand deux implémentations doivent correspondre. Pas de référence, pas de revendication de parité. C’est un prérequis bloquant, pas un suivi.
2. Clauses anti-raccourci, énoncées et tenues : pas de modification du harnais, pas de falsification de référence, pas de restructuration de composant pour faire passer un diff. Si la référence semble fausse, arrête et demande, ne l’édite pas.
3. Migre un composant à la fois. Parallélise entre worktrees, un propriétaire par composant (référence du principe [Séparer avant de sérialiser l’état partagé](../references/principles/separate-before-serializing-shared-state.md)). Les primitives partagées migrent d’abord comme phase bloquante.
4. Vérifie chaque composant contre sa référence avec un navigateur natif ou outil simulateur disponible et un diff d’image. Un diff non nul échoue. Investigue le delta pixel et continue au premier plan jusqu’à ce que le diff soit zéro ou qu’il reste une variance plateforme documentée.
5. Lance **Ouvrir une PR** par composant ou lot sûr, selon la portée de livraison du contrat d’exécution.

**Réponse :** composants migrés, résultat de diff pour chacun, emplacement du harnais de référence, ce qui reste. Chaque affirmation porte sa preuve ou son étiquette dans la même phrase. Mesuré, inféré ou supposition. Une prédiction ou une cause non observée est une supposition. Ne remets jamais à l’humain un contrôle que tu pourrais lancer.

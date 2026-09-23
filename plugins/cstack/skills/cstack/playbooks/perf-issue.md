### Problème de performance

Suivez [le contrat d’exécution Codex](../references/codex-runtime.md).

**Tu possèdes l’histoire de mesure. Planifie, relis, vérifie les chiffres.** Relie chaque correctif à une mesure, ne lis pas la source à la place de mesurer.

1. Capture une trace de référence avec le navigateur, simulateur, profileur ou outil terminal natif disponible pour la cible.
2. Lance `how` pour ancrer les hypothèses, avec sa ventilation d’explorateurs par défaut. Ne prétends pas connaître un plafond de perf sans l’avoir d’abord exécuté.
   La plupart des correctifs viennent de huit familles de stratégies. Utilise-les comme générateurs d’hypothèses, pas comme checklist. Une famille mérite une tentative seulement quand la trace montre le signal qu’elle nomme.
   - **Élimination.** Avant d’optimiser le chemin chaud, demande s’il doit exister : calcul que personne ne consomme, feature barrière toujours off pour cet utilisateur, sync qui miroir redondamment l’état, chemin legacy gardé « au cas où ». La trace montre ce qui est lent, jamais ce qui est supprimable ; cette famille a donc besoin de la passe `how`, pas du profiler.
   - **Diviser pour régner.** Le coût dominant varie avec la taille d’entrée. Divise le travail pour que chaque morceau touche moins (chunk, shard, réduire l’espace de recherche) ou pour que des morceaux indépendants s’exécutent en parallèle.
   - **Cache.** Le même calcul ou fetch se répète sur des entrées identiques. Stocke et réutilise le résultat. Nomme ce qui l’invalide avant de revendiquer la victoire.
   - **Indirection.** Le chemin chaud fait un travail coûteux qu’un intermédiaire moins cher pourrait absorber : index au lieu d’un scan, file qui déplace du travail hors du thread interactif, handle qui permet de remplacer par une implémentation moins chère. Ajoute le saut seulement quand il retire plus du chemin critique qu’il n’ajoute.
   - **Batching.** Beaucoup de petites opérations paient chacune un overhead fixe (RPC, requête, syscall, draw call). Regroupe-les pour payer l’overhead une fois par lot.
   - **Redondance.** L’attente dépend d’une instance ou tentative lente. Duplique le travail (réplicas, requêtes hedged, exécution spéculative) et prends le résultat le plus rapide. La trace doit montrer que l’attente domine et que le système a de la marge.
   - **Évaluation paresseuse.** Le coût tombe sur des résultats jamais utilisés ou pas encore nécessaires (init eager sur le boot path, rendu d’items hors écran). Diffère le travail jusqu’à la première utilisation.
   - **Planification.** Le travail doit avoir lieu, mais pas pendant le moment interactif. Déplace-le là où personne n’attend : idle callbacks, préchauffage en arrière-plan après boot, pré-calcul avant l’arrivée utilisateur, nettoyage après le commit de frame. La victoire est la latence perçue, donc mesure le chemin interactif, pas le travail total effectué.
3. Planifie le correctif depuis la trace. S’il traverse une frontière de fonction, lis et applique d’abord `../../architect/SKILL.md`. Délègue une implémentation bornée. Préserve le rôle choisi par l’appelant, y compris `simple edits` pour les petits changements bornés. Utilise `feature, refactoring` quand aucun rôle n’a été sélectionné. Suis le contrat d’exécution pour l’héritage ou le modèle et l’effort configurés. Relis le diff. Pour une capacité manquante, applique [Orchestration requise](../references/codex-runtime.md#orchestration-requise) avec `route: Review`. Capture une trace post-correctif. Lance `../../deslop/SKILL.md` sur le diff avant chaque commit. Garde `deslop skipped: <reason>` quand une étape ne peut vraiment pas s’exécuter.
   Applique la référence du principe [Séquencer le travail en unités vérifiables](../references/principles/sequence-verifiable-units.md), en vérifiant chaque tentative avant d’essayer la suivante.
4. Parse et compare les artéfacts (JSON vers sqlite, diff). « Inconclusive » ou une mauvaise surface n’est pas une réussite. Signale-le.
5. Cite la mesure dans la PR.
6. Lance **Ouvrir une PR** selon la portée de livraison du contrat d’exécution.

Pour une amélioration soutenue contre une métrique plutôt qu’un correctif ponctuel, utilise le playbook Hillclimb (`hillclimb.md`).

**Réponse :** chiffre de référence, chiffre post-correctif, delta, chemin d’artéfact. Chaque affirmation porte sa preuve ou son étiquette dans la même phrase. Mesuré, inféré ou supposition. Une prédiction ou une cause non observée est une supposition. Ne remets jamais à l’humain un contrôle que tu pourrais lancer.

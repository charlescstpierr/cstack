### Exécution autonome

Suivez [le contrat d’exécution Codex](../references/codex-runtime.md).

**Tu possèdes la condition de sortie. Définis ce que signifie terminé, puis avances jusqu’à l’atteindre sans t’arrêter.**

1. Énonce la condition de sortie comme prédicat vérifiable avant la première itération (tests verts, repro corrigée, les N PR toutes fusionnées, pixel-diff à zéro).
2. Continue au premier plan avec les attentes natives. Pour la CI, un merge ou un changement de ref, utilise l’outil sensible aux événements ou le watcher fourni via le lanceur du plugin. Utilise un planificateur natif seulement s’il est disponible et si l’utilisateur a demandé une continuation planifiée. Calibre le polling au moment où un résultat vaut la peine d’être vérifié. Ne promets pas que le travail survit à la fermeture de l’app.
3. Chaque itération effectue le plus petit changement justifié par les preuves, le vérifie contre le prédicat, committe s’il fait avancer, et abandonne les changements qui n’aident pas. Un double garde-fou qui « pourrait aider » est rétabli, pas laissé en place. Abandonne seulement les fichiers touchés par cette itération, avec `git checkout -- <paths>` ou `git stash push <paths>`. Jamais `reset --hard`, jamais `git clean`, jamais `checkout -- .`. Lance `../../deslop/SKILL.md` sur le diff avant chaque commit. Garde `deslop skipped: <reason>` quand une étape ne peut vraiment pas s’exécuter.
   Séquence le travail avec la référence de principe [Séquencer le travail en unités vérifiables](../references/principles/sequence-verifiable-units.md), en vérifiant chaque unité avant la suivante plutôt que de regrouper les contrôles à la fin.
4. Traite les compétences cassées dans le périmètre, bugs liés, vérificateurs flaky, bruit de revue, pannes d’outillage, suivis orphelins et dérive réparable. Mets les correctifs non liés dans un changement proposé séparé et ne crée pas sa PR sans autorisation. Demande seulement pour un travail destructeur ou irréversible, une autorité manquante, un vrai choix produit ou une véritable impasse. Reviens au prédicat après chaque correctif latéral.
5. Crée un point de reprise à chaque itération via la compétence **show-me-your-work**, avec une ligne indiquant ce qui a changé et si le prédicat a progressé.
6. Si le prédicat atteint a produit une branche d’implémentation non livrée, lance **Ouvrir une PR** selon la portée de livraison du contrat d’exécution.
7. Arrête quand le prédicat est atteint. Un plateau n’est pas un arrêt : continue et change d’approche pour le dépasser. Remonte une vraie impasse au lieu de tourner en rond, et n’assouplis jamais le prédicat pour déclarer victoire.

**Réponse :** la condition de sortie, les itérations lancées, ce qui a atterri, ce qui a été abandonné, l’état final du prédicat. Chaque affirmation porte sa preuve ou son étiquette dans la même phrase. Mesuré, inféré ou supposition. Une prédiction ou une cause non observée est une supposition. Ne remets jamais à l’humain un contrôle que tu pourrais lancer.

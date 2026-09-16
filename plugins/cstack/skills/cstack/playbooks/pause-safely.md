### Mettre en pause sans risque

Suivez [le contrat d’exécution Codex](../references/codex-runtime.md).

**Tu possèdes un arrêt propre. Laisse un point de reprise qu’un agent partant de zéro peut reprendre.** C’est uniquement explicite. Sur « keep going », « going to bed, keep going » ou « don’t stop », ne mets pas en pause.

1. Arrête à une frontière sûre. Termine l’étape atomique courante ou annule-la. Ne t’arrête jamais au milieu d’une édition dans un état connu cassé. Ne commence rien de nouveau et annule tout sous-agent imbriqué.
2. Ne fais aucune action irréversible pour mettre en pause. Pas de PR ni de push sauf si tu en avais déjà un sorti.
3. Rends le travail durable. Stage seulement les chemins de cette tâche et committe-les en un commit `wip:` clair sur la branche courante pour ne rien perdre. Laisse les changements non liés non commités et liste-les. Si l’arbre est cassé, dis-le dans le corps du commit en une ligne.
4. Écris la note de reprise sous `.cstack/resume/<slug>.md`. Capture l’intention, la progression, les résultats vérifiés, l’état courant, les prochaines étapes, les fichiers clés et les risques. Si une trace show-me-your-work existe, lie-la au lieu de la dupliquer.

**Réponse :** où tu en es dans la boucle, ce qui est sur disque par rapport à ce qui reste dans ta tête (chemins, pas de dumps de diff), les commits faits et si l’arbre est propre, puis la première action à la reprise. C’est une pause, pas un rapport final. Chaque affirmation porte sa preuve ou son étiquette dans la même phrase. Mesuré, inféré ou supposition. Une prédiction ou une cause non observée est une supposition. Ne remets jamais à l’humain un contrôle que tu pourrais lancer.

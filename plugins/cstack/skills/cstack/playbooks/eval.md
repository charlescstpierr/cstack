### Évaluation

Suivez [le contrat d’exécution Codex](../references/codex-runtime.md).

**Tu possèdes la conception de l’expérience. Planifie, aveugle, lance, synthétise.**

**Non négociables pour l’aveuglement :**

- Aucun `eval`, `test`, `judge`, `experiment`, `rubric`, `score`, `compare`, `benchmark`, `candidate` ni `arena` dans tout répertoire, fichier ou prompt que le candidat voit.
- Le prompt candidat ressemble à une demande utilisateur organique. Énonce l’objectif, pas le méta.
- Aucun indice qui sollicite la chaîne. Ne demande pas au candidat de lister les compétences, principes ou fichiers appliqués. Demande des notes de conception générales et note le suivi de chaîne à partir de la forme du code, pas de l’auto-rapport.
- Nettoie les noms de répertoire et de slug. Utilise des noms en forme de projet qu’un utilisateur pourrait choisir.
- Ne dis pas au candidat qu’il existe d’autres candidats.
- Le juge peut savoir qu’il juge, mais voit les sorties seulement par libellé nettoyé, jamais par nom de modèle.
- Comparaison de deux variantes : un juge note les deux ensembles dans une seule passe sur une seule échelle, aveugle à la provenance de chaque ensemble.

**Étapes :**

1. **Cadrer.** Énonce quelle variante est testée et quel comportement compte comme réussite. Écris la rubrique (3 à 6 critères concrets) pour le juge seulement. Ne la donne pas aux candidats. Quand la variante est une règle de compétence, l'autre variante est la même compétence sans cette règle ; une règle sans échec de référence observé n'est pas promue.
2. **Mettre en place des environnements nettoyés.** Répertoire de travail par candidat avec la variante en place. Plante tout contexte qu’une tâche organique aurait : squelette de projet, compétences que le candidat lirait naturellement.
3. **Rédiger un prompt organique.** Ce qu’un utilisateur taperait. Aucune fuite sur ce qui est mesuré.
4. **Lancer le panel de candidats.** Lis et applique `../../arena/SKILL.md`. Sans configuration de panel, lance trois candidats indépendants en modèle hérité. Donne à chaque candidat le même prompt et un répertoire inscriptible séparé. Limite le travail à la capacité native et lance les candidats excédentaires par vagues. Utilise seulement les surcharges disponibles depuis `.cstack/models.json`.
5. **Lancer un juge aveuglé.** Préfère un modèle disponible différent quand la session en expose déjà un. Si la capacité de revue manque, applique [Orchestration requise](../references/runtime/orchestration.md) avec `route: Review`. Quand la session n’a qu’un modèle, étiquette le verdict `single-model` et ne le décris jamais comme un bakeoff multi-modèle aveuglé. Si un modèle de juge explicite est indisponible, garde cette sélection `BLOCKED` et rapporte le refus sans hériter ni substituer un autre modèle. Le juge voit les libellés nettoyés et la rubrique, jamais les noms de modèle.
6. **Vérifier depuis les artéfacts observables.** Inspecte les fichiers, commandes, diffs et résultats d’outil de chaque candidat disponibles dans cette tâche. Utilise une transcription de tâche native seulement quand la session courante l’expose. Ne cherche jamais dans des conversations non liées ni dans l’historique privé du workspace. Traite l’auto-rapport comme un pointeur, pas comme une preuve.
7. **Lis toi-même chaque sortie candidat** de bout en bout. Compare au verdict du juge. Un désaccord signifie qu’un modèle est biaisé ou que la rubrique est ambiguë. Synthétise.

**Réponse :** variante testée, rubrique, notes par candidat, verdict du juge, ta synthèse et une recommandation sur la promotion de la variante. Nomme l’étiquette du juge (`single-model` ou multi-model). Chaque affirmation porte sa preuve ou son étiquette dans la même phrase. Mesuré, inféré ou supposition. Une prédiction ou une cause non observée est une supposition. Ne remets jamais à l’humain un contrôle que tu pourrais lancer.

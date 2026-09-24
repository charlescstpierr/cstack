### Investigation

Suivez [le contrat d’exécution Codex](../references/codex-runtime.md).

**Tu possèdes la réponse. Planifie, route, rédige.**

Les demandes d’investigation sont en lecture seule. Elles produisent une explication citée ou une recommandation, pas un changement de code.

1. Lis et applique `../../how/SKILL.md` dans cette session, avec le [contrat d’exploration déléguée](../references/codex-runtime.md#exploration-déléguée). Pour les questions de motivation, lis aussi `../../why/SKILL.md`. Un délégué ne lance pas de descendants sans décision explicite du parent, donc ventile les explorateurs plutôt que les compétences elles-mêmes.
2. Le point de contrôle de débit reste sur une ligne : `throughput checkpoint: n/a, read-only investigation`.
3. Produis la sortie en forme `how` (Vue d’ensemble / Concepts clés / Fonctionnement / Emplacements / Pièges), ou une recommandation avec tableau de compromis si la demande est une décision entre alternatives.
4. Applique la compétence **unslop** à la réponse.

Pas de PR, pas de babysit, pas de `architect` sauf si l’investigation précède un changement de code. Si c’est le cas, repasse à l’utilisateur et reroute vers Bug fix ou Feature.

**Réponse :** la sortie d’investigation. Pour les réponses à « sommes-nous sûrs ? », inclus ton vrai jugement avec raisons. Repousse la prémisse si elle est fausse (voir Autonomy). Chaque affirmation porte sa preuve ou son étiquette dans la même phrase. Mesuré, inféré ou supposition. Une prédiction ou une cause non observée est une supposition. Ne remets jamais à l’humain un contrôle que tu pourrais lancer.

---
name: swarm
description: "À utiliser pour $cstack:swarm, « lance un swarm sur ceci », ou la couverture parallèle, les courses, gauntlets et explorations. Déploie N workers parallèles, récupère leurs résultats et rend un rapport unique."
---

# Swarm

Runtime : [règles communes](../cstack/references/runtime/base.md), [délégation](../cstack/references/runtime/delegation.md), [modèles](../cstack/references/runtime/modeles.md), [orchestration](../cstack/references/runtime/orchestration.md) · rôles : `swarm workers`.

Déploie N workers parallèles. Ils peuvent couvrir des tranches séparées, courir sur le même brief, ou mélanger les deux. Le parent attend, agrège et rend un rapport unique.

## Démarrage

Suis un élément par phase dans la tâche courante avant tout lancement.

1. Cadrer
2. Déployer
3. Agréger
4. Rapporter

## Phase A : Cadrer

1. Énonce le prédicat de terminé et l'artefact ou rapport que le swarm doit rendre.
2. Choisis la forme. Partitionne en tranches, fais courir N workers sur des briefs identiques, ou mélange les deux. Pour une course ou forme mixte, déclare `first pass`, `rank all` ou `best-of` avant le lancement.
3. Fixe N depuis l'utilisateur ou dérive-le de la forme : au moins deux tranches dès que la forme l'admet ; un seul worker exige une raison nommée. N est le total de workers, pas la fenêtre d'exécution ; celle-ci compte l'emplacement parent des sous-agents natifs.
4. Le rôle ou la sélection fournis par l'appelant priment ; sinon, `swarm workers`. Pour une course de modèles, nomme dès le début la sélection vérifiée de chaque bras.
5. Donne à chaque worker sa propre sortie inscriptible quand il écrit.

## Phase B : Déployer

Lance les N workers en parallèle. Chaque brief assigne une portée bornée, la propriété exclusive des fichiers quand le worker écrit, et la lecture seule pour l'investigation et la revue.

Chaque brief tient seul. Inclus l'objectif, la portée, la tranche ou le bras de course exact, comment vérifier, et quoi rapporter. Les rapports utilisent `PASS`, `ISSUES` ou `BLOCKED` avec preuves.

Si un worker abandonne, continue avec N-1 et note-le.

## Phase C : Agréger

Lis les résultats terminaux. Pour la couverture, chaque tranche requise doit avoir un résultat. Pour une course, applique la règle de sélection déclarée dès le début. Ne colle pas les dumps bruts des workers.

Garde un tableau de résultats compact, des problèmes étayés en une ligne, et les manques ou abandons explicites.

## Phase D : Rapporter

Rends dans le chat un rapport consolidé unique : tableau, problèmes en une ligne, manques ou abandons, règle de course le cas échéant. Étiquette chaque affirmation selon [Rédiger le rapport](../cstack/SKILL.md#rédiger-le-rapport).

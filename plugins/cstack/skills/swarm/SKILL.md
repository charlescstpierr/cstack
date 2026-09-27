---
name: swarm
description: "Déploie N workers parallèles, récupère leurs résultats et rend un rapport unique. Utiliser pour $cstack:swarm, 'lance un swarm sur ceci', ou la couverture parallèle, les courses, gauntlets et explorations."
---

# Swarm

Contrat d'exécution : [`../cstack/references/codex-runtime.md`](../cstack/references/codex-runtime.md).

Pour chaque sélection avec `runtime`, applique le [dispatch CLI](../cstack/references/runtime-workers.md) à la place du lancement natif. Conserve la taille et l’ordre du panel, le rôle spécialisé et les étapes de vérification. Les replis single-agent de ce document concernent seulement les sélections natives ; une position CLI bloquée n’est jamais remplacée silencieusement par Codex.

Déploie N workers parallèles. Ils peuvent couvrir des tranches séparées, courir sur le même brief, ou melanger les deux. Le parent attend, agrége et rend un rapport unique.

## Démarrage

Suis un élément par phase dans la tâche courante avant de lancer quoi que ce soit.

1. Cadrer
2. Déployer
3. Agreger
4. Rapporter

## Phase A : Cadrer

1. Énonce le prédicat de terminé et l'artefact ou rapport que le swarm doit rendre.
2. Choisis la forme. Partitionne en tranches, fais courir N workers sur des briefs identiques, ou melange les deux. Pour une course ou forme mixte, declare `first pass`, `rank all` ou `best-of` avant le lancement.
3. Fixe N depuis l'utilisateur ou dérive-le de la forme. Sans N donné, pars d'au moins deux tranches dès que la forme en admet deux ; un seul worker exige une raison nommée. Conserve N comme nombre total de tranches. Plafonne seulement la fenêtre d’exécution à la capacité disponible et tiens compte de l’emplacement parent pour les sous-agents natifs ; les workers excédentaires passent dans les vagues suivantes.
4. Utilise d'abord le rôle spécialisé ou la sélection complète fournie par l'appelant. Sinon, résous `swarm workers` sous le contrat d’exécution. Préserve le modèle et l'effort de raisonnement au dispatch et signale les surcharges ou capacités non prises en charge sans substitution. Pour une course de modèles, nomme les surcharges vérifiées dès le début.
5. Donne à chaque worker sa propre sortie inscriptible quand il écrit.

## Phase B : Déployer

Lance les N workers en parallèle, selon leur sélection native ou CLI. Chaque brief doit assigner une portée bornée et une propriété exclusive des fichiers quand le worker écrit. Utilise des portées en lecture seule pour l'investigation et la revue. La concurrence native limite le nombre d'exécutions simultanées. Mets les workers restants en file pour des vagues ultérieures. Pour les replis, délégués sans descendants et capacités manquantes, applique [Orchestration requise](../cstack/references/runtime/orchestration.md). Le manque de capacité ne supprime jamais une tranche requise.

Chaque brief tient seul. Inclus l'objectif, la portée, la tranche où le bras de course exact, comment vérifier, et quoi rapporter. Les rapports utilisent `PASS`, `ISSUES` ou `BLOCKED` avec preuves.

Si un worker abandonne, continue avec N-1 et note-le.

## Phase C : Agreger

Lis les résultats terminaux. Pour la couverture, chaque tranche requise doit avoir un résultat. Pour une course, applique la règle de sélection declaree dès le début. Utilise first pass, rank all ou best-of. Ne colle pas les dumps bruts des workers.

Garde un tableau de résultats compact, des problèmes etayes en une ligne, et les manques ou abandons explicites.

## Phase D : Rapporter

Rends dans le chat un rapport consolidé unique avec le tableau, les problèmes en une ligne, les manques ou abandons, et la règle de course quand elle est utilisée. Chaque affirmation porte sa preuve ou son étiquette dans la même phrase. Mesure, inférence ou supposition. Une prédiction ou une cause non observée est une supposition. Ne donne jamais à l'humain une vérification que tu pourrais exécuter.

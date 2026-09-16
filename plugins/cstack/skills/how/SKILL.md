---
name: how
description: >-
  À utiliser pour $cstack:how, « comment X fonctionne-t-il ? », les parcours de
  code avant de changer quelque chose, et les questions de placement /
  propriété / couches (« où cela doit-il vivre ? », « quel package possède ceci
  ? », « est-ce la bonne couche ? »). Explique l'architecture du sous-système,
  le flux runtime et les modèles mentaux d'accueil. Utilise $cstack:why pour la
  motivation.
---

# How

Runtime : [`../cstack/references/codex-runtime.md`](../cstack/references/codex-runtime.md).

Explore le codebase pour répondre aux questions "comment X fonctionne ?". Produis des explications architecturales au niveau d'un ingénieur senior qui arrive sur un sous-système : assez pour construire un modèle mental opérationnel, sans devenir une source annotée.

Suis le chemin d'héritage direct du contrat runtime quand rien n'est configuré; sinon résous chaque rôle nommé avec son helper et transmets à chaque spawn natif la sélection complète, effort de raisonnement compris. Signale les lacunes de capacité de l'hôte au lieu de supprimer un champ sélectionné.

Un subagent manquant sérialise une étape. Il ne la retire jamais. Quand aucun slot de subagent n'est disponible, exécute la passe explorer, explainer ou synthesizer dans la même session comme passe séparée et explicitement recadrée, étiquette le résultat `single-agent`, et signale l'indépendance manquante.

## Étape 1. Évaluer la complexité

Si la portée est ambiguë, indique ton interprétation et explore. L'utilisateur peut rediriger.

- **Simple** (un seul module, un petit utilitaire, une question étroite comme "comment fonctionne la fonction X") : pas d'explorers. Un explainer explore et explique en une seule passe. Va à l'Étape 2b.
- **Complexe** (un sous-système couvrant plusieurs fichiers ou services, une fonctionnalité transversale, une vue architecturale complète) : lance d'abord des explorers parallèles, puis transmets à l'explainer. Va à l'Étape 2a.

En cas de doute, prends le chemin simple.

## Étape 2a. Explorer (questions complexes seulement)

Décompose la question en 2 à 4 angles d'exploration, chacun étant une tranche distincte du sous-système. Lance des subagents natifs en lecture seule en parallèle. Ils héritent du modèle parent par défaut. Si `.cstack/models.json` définit `how explorer`, suis le contrat runtime et ne substitue pas silencieusement une surcharge explicite indisponible.

Chaque explorer reçoit le prompt dans `references/explorer-prompt.md` avec son angle rempli. Va ensuite à l'Étape 3.

## Étape 2b. Expliquer directement (questions simples)

Lance un subagent natif en lecture seule qui explore et explique en une passe. Il hérite du modèle parent par défaut. Si `.cstack/models.json` définit `how explainer`, suis le contrat runtime et ne substitue pas silencieusement une surcharge explicite indisponible.

Construis son prompt depuis `references/explainer-prompt.md` sans la section des résultats d'explorers. Va à l'Étape 4.

## Étape 3. Synthétiser (questions complexes seulement)

Une fois tous les explorers revenus, lance un subagent natif en lecture seule pour synthétiser leurs résultats en une seule explication. Il hérite du modèle parent par défaut. Si `.cstack/models.json` définit `how explainer`, suis le contrat runtime et ne substitue pas silencieusement une surcharge explicite indisponible.

Construis son prompt depuis `references/explainer-prompt.md` avec les résultats de chaque explorer remplis.

## Étape 4. Présenter

Présente la sortie de l'explainer à l'utilisateur. De légères retouches pour la clarté ou le contexte de conversation sont acceptables. Ne la réécris pas substantiellement.

## Format de sortie

L'explication utilise les sections définies dans `references/explainer-prompt.md`, en supprimant celles qui ne s'appliquent pas : Vue d'ensemble, Concepts clés, Fonctionnement, Où vivent les choses, Pièges.

Chaque affirmation porte sa preuve ou son étiquette dans la même phrase. Mesuré, inféré ou supposition. Une prédiction ou une cause non observée est une supposition. Ne donne jamais à l'humain une vérification que tu pourrais exécuter.

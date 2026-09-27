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

Runtime : [règles communes](../cstack/references/runtime/base.md), [délégation](../cstack/references/runtime/delegation.md), [modèles](../cstack/references/runtime/modeles.md), [exploration](../cstack/references/runtime/exploration.md), [orchestration](../cstack/references/runtime/orchestration.md) · rôles : `how explorer`, `how explainer`.

Explore le codebase pour répondre aux questions "comment X fonctionne ?". Produis des explications architecturales au niveau d'un ingénieur senior qui arrive sur un sous-système : assez pour construire un modèle mental opérationnel, sans devenir une source annotée.

Seuls la demande de l'utilisateur, le mode courant ou les permissions de la session peuvent exclure la délégation de cette question dans son ensemble.

## Étape 1. Poser les angles

Si la portée est ambiguë, indique ton interprétation et explore. L'utilisateur peut rediriger.

Écris les angles avant de choisir le chemin. Un angle est une tranche du sous-système avec sa propre liste de fichiers à lire.

Deux angles ou plus : va à l'Étape 2a, le chemin par défaut. Un recouvrement partiel ne change rien : garde le fichier commun dans une tranche. Une portée large, une zone inconnue ou une première lecture produisent plusieurs angles, pas une passe unique.

Un seul angle : va à l'Étape 2b seulement si la délégation est exclue, avec la raison `single-pass: Délégation exclue`. Sinon, va à l'Étape 2a et décompose cet angle. Une impression de simplicité n'est pas une raison de rester seul.

## Étape 2a. Explorer en parallèle (chemin par défaut)

Vise normalement trois angles ; lance un explorer par angle, en subagent natif en lecture seule ; les explorers ne lancent pas de descendants et retournent des findings structurés, pas des dumps de fichiers.

Chaque explorer reçoit `references/explorer-prompt.md` avec son angle rempli. Va ensuite à l'Étape 3.

## Étape 2b. Expliquer en une passe (délégation exclue)

Exécute cette passe dans la session courante, sans subagent, étiquetée `single-agent` avec l'indépendance manquante signalée. Suis `references/explainer-prompt.md` sans la section des résultats d'explorers. Va à l'Étape 4.

## Étape 3. Synthétiser (après l'Étape 2a)

Une fois tous les explorers revenus, lance un subagent natif en lecture seule qui synthétise leurs résultats en une explication, avec le prompt de `references/explainer-prompt.md` rempli des résultats de chaque explorer.

## Étape 4. Présenter

Présente la sortie de l'explainer à l'utilisateur, avec au plus de légères retouches de clarté ou de contexte ; ne la réécris pas substantiellement.

## Format de sortie

L'explication utilise les sections définies dans `references/explainer-prompt.md`, en supprimant celles qui ne s'appliquent pas : Vue d'ensemble, Concepts clés, Fonctionnement, Où vivent les choses, Pièges. Étiquette chaque affirmation selon [Rédiger le rapport](../cstack/SKILL.md#rédiger-le-rapport).

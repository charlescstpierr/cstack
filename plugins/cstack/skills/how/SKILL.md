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

## Étape 1. Poser les angles

Si la portée est ambiguë, indique ton interprétation et explore. L'utilisateur peut rediriger.

Écris les angles avant de choisir le chemin. Un angle est une tranche du sous-système avec sa propre liste de fichiers à lire. Vise 2 à 4 angles.

Deux angles ou plus : va à l'Étape 2a. C'est le chemin par défaut. Un recouvrement partiel entre leurs listes de fichiers ne change rien ; retire le fichier commun de toutes les tranches sauf une et garde les angles. Une portée large, une zone inconnue ou une première lecture produisent plusieurs angles ; elles ne justifient pas la passe unique. Un flux qui traverse plusieurs modules, une remontée d'erreur ou toute fonctionnalité transversale produisent toujours plusieurs angles : découpe-les par module.

Un seul angle : va à l'Étape 2b. Cette sortie exige un des trois tests ci-dessous. Nomme dans ta réponse celui qui s'applique, sous la forme `single-pass: <test>`.

- **Cible unique.** La question nomme une seule fonction, un seul type ou un seul fichier, et tu peux citer ce chemin avant d'explorer.
- **Fichiers indissociables.** Les fichiers à lire tiennent dans un seul module et aucune seconde tranche n'aurait de fichier à elle. Une chaîne d'appels qui traverse plusieurs modules ne satisfait jamais ce test.
- **Délégation exclue.** La demande de l'utilisateur, le mode courant ou les permissions de la session interdisent les sous-agents.

Aucun test satisfait : va à l'Étape 2a. Une impression de simplicité n'est pas un test.

## Étape 2a. Explorer en parallèle (chemin par défaut)

Décompose la question en 2 à 4 angles d'exploration, chacun étant une tranche distincte du sous-système. Lance des subagents natifs en lecture seule en parallèle. Ils héritent du modèle parent par défaut. Si `.cstack/models.json` définit `how explorer`, suis le contrat runtime et ne substitue pas silencieusement une surcharge explicite indisponible. Ne dépasse pas 4 explorers, reste dans la limite de la concurrence native et mets l'excédent en file. Les explorers ne lancent pas de descendants et retournent des findings structurés, pas des dumps de fichiers.

Chaque explorer reçoit le prompt dans `references/explorer-prompt.md` avec son angle rempli. Va ensuite à l'Étape 3.

## Étape 2b. Expliquer en une passe (exception nommée)

Quand le test `Délégation exclue` t'a envoyé ici, exécute cette passe dans la session courante, étiquette le résultat `single-agent` et signale l'indépendance manquante. Ne lance aucun subagent dans ce cas.

Sinon, lance un subagent natif en lecture seule qui explore et explique en une passe. Il hérite du modèle parent par défaut. Si `.cstack/models.json` définit `how explainer`, suis le contrat runtime et ne substitue pas silencieusement une surcharge explicite indisponible.

Construis son prompt depuis `references/explainer-prompt.md` sans la section des résultats d'explorers. Va à l'Étape 4.

## Étape 3. Synthétiser (après l'Étape 2a)

Une fois tous les explorers revenus, lance un subagent natif en lecture seule pour synthétiser leurs résultats en une seule explication. Il hérite du modèle parent par défaut. Si `.cstack/models.json` définit `how explainer`, suis le contrat runtime et ne substitue pas silencieusement une surcharge explicite indisponible.

Construis son prompt depuis `references/explainer-prompt.md` avec les résultats de chaque explorer remplis.

## Étape 4. Présenter

Présente la sortie de l'explainer à l'utilisateur. De légères retouches pour la clarté ou le contexte de conversation sont acceptables. Ne la réécris pas substantiellement.

## Format de sortie

L'explication utilise les sections définies dans `references/explainer-prompt.md`, en supprimant celles qui ne s'appliquent pas : Vue d'ensemble, Concepts clés, Fonctionnement, Où vivent les choses, Pièges.

Chaque affirmation porte sa preuve ou son étiquette dans la même phrase. Mesuré, inféré ou supposition. Une prédiction ou une cause non observée est une supposition. Ne donne jamais à l'humain une vérification que tu pourrais exécuter.

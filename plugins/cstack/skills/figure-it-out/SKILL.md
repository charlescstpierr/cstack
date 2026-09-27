---
name: figure-it-out
description: "Conçoit un playbook auditable quand aucun plus étroit ne convient : grande migration, changement ambitieux en plusieurs parties, ou travail qu'un humain relit après s'être absenté. Ajuste la rigueur à la tâche, exécute une boucle d'hypothèses et journalise les décisions via show-me-your-work. Utiliser pour $cstack:figure-it-out, 'figure it out', une grande migration ou quand aucun playbook plus étroit ne s'applique."
---

# Figure it out

Runtime : [règles communes](../cstack/references/runtime/base.md), [délégation](../cstack/references/runtime/delegation.md), [orchestration](../cstack/references/runtime/orchestration.md).

Quand la tâche ne correspond à aucun playbook, conçois-en un. Le livrable avant tout code est le flux de travail lui-même : une séquence de phases qui ajuste la rigueur à la tâche, applique la méthode scientifique et laisse une trace de décisions qu'un humain peut auditer après s'être absenté. Biaise vers plus de rigueur. Le coût de construire la mauvaise chose écrase le coût d'être prudent.

## Démarrage

Commence la liste de tâches par la lecture des règles communes et routes de principes de la [skill cstack](../cstack/SKILL.md) et des références dont les déclencheurs s'appliquent, puis ajoute les phases ci-dessous. Réutilise un handoff Horizon et les décisions vérifiées existants pour le cadrage ; les portes de revue et de vérification restent.

## Phase A : Cadrer

Ancre d'abord, puis engage-toi. Ne démarre pas l'exécution tant que tu ne peux pas énoncer :

- La définition de terminé comme prédicat falsifiable ([prouver que ça marche](../cstack/references/principles/prove-it-works.md)).
- La portée, quantifiée : unités et effort approximatifs, plus les bloqueurs révélés par l'ancrage.
- Le niveau de rigueur, avec biais haut. Les portes à sens unique et forts rayons d'impact en reçoivent plus. Les étapes réversibles à faible enjeu en reçoivent moins. La rigueur, ce sont des portes et des artefacts, pas "try harder".

Présente le cadrage et les compromis avant de t'engager dans une longue exécution. Le travail réversible avance ([ne jamais bloquer sur l'humain](../cstack/references/principles/never-block-on-the-human.md)), mais une exécution de plusieurs heures mérite un checkpoint.

## Phase B : Concevoir le flux de travail

Décompose en unités atomiques et livrables indépendamment. Séquence les inconnues les plus risquées d'abord. L'échafaudage et la vérification viennent avant les fonctionnalités ([pensée fondatrice](../cstack/references/principles/foundational-thinking.md)).

- Construis le harnais de vérification avant le travail, avec la baseline capturée depuis l'état pré-changement, pour que la vérification se lise comme "ancienne valeur vs nouvelle valeur".
- Pour les décisions de conception à portée à sens unique, exécute la skill **architect** (elle exécute **arena**). Saute-la pour le travail mécanique dont la forme est déjà concrète. Une seconde arena sur une conception tranchée est de la suringénierie ([Laziness Protocol](../cstack/references/principles/laziness-protocol.md)).
- Décide ce qui se déploie en parallèle. Parallélise seulement entre frontières, et donne à chaque worker son propre worktree ou sa propre branche ([séparer avant de sérialiser l'état partagé](../cstack/references/principles/separate-before-serializing-shared-state.md)). Ne déploie pas trop.
- Écris la liste de phases conçue. L'humain relit cette liste.

Ensuite, exécute la conception. Ajoute ses étapes à la liste de tâches, entre les phases C et D. Exécute chacune selon la discipline de boucle de la phase C, et tisse le journal de phase D à travers elles à mesure que chaque étape atterrit.

## Phase C : Exécuter la boucle

Chaque unité est une expérience. Énonce l'hypothèse, fais le plus petit changement, mesure contre le prédicat sur le vrai artefact, garde-le s'il a fait avancer, revert s'il ne l'a pas fait.
Applique [séquencer le travail en unités vérifiables](../cstack/references/principles/sequence-verifiable-units.md) : vérifie chaque unité avant la suivante au lieu de regrouper les checks à la fin.

- Vérifie en inspectant l'artefact, jamais un auto-rapport. Quand quelque chose passe trop facilement, soupçonne la méthode d'observation avant le système.
- Associe le travail délégué à un juge et audite toi-même les artefacts des délégués avant de leur faire confiance. Si un worker manipule la porte, réinitialise et durcis le contrat. Si la porte elle-même est fausse, corrige la porte dans son propre changement au lieu de la contourner.
- Un verdict est VERIFIED, NOT VERIFIED ou INCONCLUSIVE. Inconclusive n'est pas un succès. Ne cache pas un négatif.

## Phase D : Garder la trace d'audit

Journalise l'exécution via la skill **show-me-your-work**, dans un TSV canonique avec une ligne par décision et par unité, et les preuves en liens. Le travail de figure-it-out est généralement assez ambitieux pour committer la trace afin que le relecteur puisse la lire dans la PR. Committe-la quand il faut montrer la confiance. Préfère les preuves produites par des scripts committés. La trace plus le diff permettent à l'humain de revenir et de faire confiance au travail.

## Phase E : Vérifier et remettre

Vérifie l'ensemble contre le prédicat de phase A sur le vrai produit, pas seulement le harnais. Encode toute correction récurrente comme porte, règle de lint, check ou script ([encoder les leçons dans la structure](../cstack/references/principles/encode-lessons-in-structure.md)).

**Réponse :** le playbook que tu as conçu, le niveau de rigueur et pourquoi, le chemin de la trace de décision, ce qui est vérifié contre le prédicat et ce qui reste ouvert.

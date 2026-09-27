---
name: architect
description: "À utiliser pour $cstack:architect, « architecturer ceci », « concevoir ceci » ou un travail non trivial où passer directement au code figerait la mauvaise forme. Ébauche les types, signatures et structure de modules avant le code, puis reste dans la boucle pendant que l'implémentation remplit le tout."
---

# Architecte

Runtime : [règles communes](../cstack/references/runtime/base.md), [délégation](../cstack/references/runtime/delegation.md), [modèles](../cstack/references/runtime/modeles.md), [orchestration](../cstack/references/runtime/orchestration.md) · rôles : `architect runners`.

Conçois avant d'implémenter. Ébauche les types, signatures de fonctions, formes de classes et frontières de modules avec des corps `not implemented` et du pseudocode. Synthétise plusieurs perspectives de modèles, puis remplis le code selon l'ébauche choisie. Si l'implémentation prouve que l'ébauche est mauvaise, jette-la et reconçois.

## Démarrage

Suis un élément par phase dans la tâche courante avant de commencer.

1. Ancrer
2. Ébaucher
3. Valider
4. Implémenter
5. Jeter

## Phase A : Ancrer le problème

Construis un vrai modèle mental de chaque système touché par le nouveau code. Exécute la compétence **how** sur les sous-systèmes pertinents, dans cette session : un délégué ne lance pas de descendants sans décision explicite du parent, donc ventile les explorateurs, pas les ancrages.

Nommer un fichier n'est pas ancrer. Produis le modèle tracé prescrit par `how`. Si la conception redéfinit la propriété ou les couches, exécute aussi la compétence **why** sur la forme existante afin que la justification devienne une contrainte, pas une supposition.

Saute la Phase A seulement pour un travail réellement nouveau, sans système environnant à intégrer.

## Phase B : Ébaucher

Exécute la compétence **arena** avec la tâche d'ébauche et les artefacts d'ancrage de la Phase A, et `references/runner-prompt.md` comme prompt de chaque exécuteur. Chaque candidat produit un dossier de conception conforme à `references/rationale-template.md`.

Résous le panel `architect runners` ; configuré, il compte au moins deux entrées, sinon c'est une erreur de configuration à signaler au lieu de modifier silencieusement son compte. Passe ce panel exact à Arena, où il prime sur `arena runners` même si les deux clés sont configurées.

Conçois-le deux fois. Exige au moins deux candidats structurellement distincts avant la synthèse, même si le premier semble suffisant. C'est [Épuiser l’espace de conception](../cstack/references/principles/exhaust-the-design-space.md) rendu concret. Des alternatives de forme globale, pas des corrections ponctuelles dans une forme.

Passe chaque candidat au crible de [`references/design-red-flags.md`](references/design-red-flags.md) avant la synthèse. Rejette ou révise les modules superficiels, les fuites d'information, la décomposition temporelle et les méthodes relais.

Compare les candidats viables selon la profondeur d'interface. Préfère la conception qui cache le plus de complexité derrière la surface publique la plus petite et simple. Une interface riche peut raccourcir les chaînes d'appels en concentrant la capacité plutôt que l'éparpiller entre couches.

Arena retourne un dossier de conception synthétisé ; sa décision de synthèse remplit la section "Décision de synthèse" de la justification.

## Phase C : Valider (sur demande)

Si la tâche autorise déjà l'implémentation, avance avec la conception synthétisée sans point de contrôle redondant. Une demande de conception seule ou le mode Codex Plan retourne la conception, sans implémentation ni commit.

Active un point de contrôle seulement sur demande explicite ("$cstack:architect avec point de contrôle", "montre-moi avant d’implémenter" ou semblable) : présente la conception synthétisée et attends la validation.

Pendant une implémentation autorisée, la synthèse peut être son propre commit, mode "échafaudage d’abord" de [Pensée fondatrice](../cstack/references/principles/foundational-thinking.md). Pour une pression adversariale avant l'implémentation, exécute la compétence **interrogate** sur l'ébauche synthétisée dans la même portée.

Si l'humain repousse la forme (au point de contrôle ou après coup), c'est une preuve de Phase A : ré-ancre et relance la Phase B avant d'écrire plus de code.

## Phase D : Implémenter selon l'ébauche

Remplace les corps `not implemented` par du code, le pseudocode par de la logique. L'ébauche synthétisée est le contrat.

Les écarts à l'ébauche sont des signaux à exposer, pas une friction à absorber en silence. Si une fonction a besoin d'un paramètre que l'ébauche n'avait pas anticipé, demande si l'ébauche était mauvaise, si l'exigence a été manquée ou si l'implémentation va trop loin.

## Phase E : Jeter quand l'architecture est mauvaise

Si l'implémentation produit constamment une friction que l'ébauche ne peut absorber, jette-la. Ne boulonne pas des correctifs sur une mauvaise conception, selon [Reconcevoir depuis les premiers principes](../cstack/references/principles/redesign-from-first-principles.md) et [Corriger les causes racines](../cstack/references/principles/fix-root-causes.md).

Le signal est un *motif*, pas des cas isolés. Indices :

- La même forme de contournement revient dans du code sans lien.
- Plusieurs cas limites sans rapport exigent des branches spéciales.
- Des types exigent des échappatoires (`any`, casts, champs optionnels toujours définis en pratique) pour compiler.
- Le réflexe "il faut un verrou" alors que l'ébauche disait l'état non partagé.
- Les appelants doivent connaître les règles internes de l'abstraction.
- Deux écarts de Phase D indépendants ou plus ont la même forme.

Fais preuve de jugement. Quelques cas limites ne condamnent pas une architecture. Certains problèmes sont légitimement complexes. La complexité dans les données n'est pas la complexité dans la conception.

Quand tu jettes :

1. Relance **how** sur ce qui a été construit.
2. Reconçois comme si les nouvelles contraintes étaient des hypothèses du premier jour.
3. [Soustrais avant d’ajouter](../cstack/references/principles/subtract-before-you-add.md) : la nouvelle ébauche rétrécit avant de grandir.
4. Retourne à la Phase B et relance arena.

## Sorties

L'usage côté appelant s'écrit d'abord ; l'ébauche de types en dérive. Petit changement : un fichier de nouveaux types et signatures. Travail plus large : carte de modules et définitions de types. La justification l'accompagne, conforme à `references/rationale-template.md`, avec l'ébauche d'usage et la décision de synthèse.

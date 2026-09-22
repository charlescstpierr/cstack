---
name: architect
description: "Ébauche les types, signatures et structure de modules avant le code, puis reste dans la boucle pendant que l'implémentation remplit le tout. À utiliser pour $cstack:architect, « architecturer ceci », « concevoir ceci », ou un travail non trivial où passer directement au code figerait la mauvaise forme."
---

# Architecte

Environnement d'exécution : [`../cstack/references/codex-runtime.md`](../cstack/references/codex-runtime.md).

Conçois avant d'implémenter. Ébauche les types, signatures de fonctions, formes de classes et frontières de modules avec des corps `not implemented` et du pseudocode. Synthétise plusieurs perspectives de modèles, puis remplis le code selon l'ébauche choisie. Si l'implémentation prouve que l'ébauche est mauvaise, jette-la et reconçois.

## Démarrage

Suis un élément par phase dans la tâche courante avant de commencer.

1. Ancrer
2. Ébaucher
3. Valider
4. Implémenter
5. Jeter

## Phase A : Ancrer le problème

Construis un vrai modèle mental de chaque système touché par le nouveau code. Exécute la compétence **how** sur les sous-systèmes pertinents, dans cette session, pour que son ancrage ventile ses explorateurs par défaut. Un délégué ne lance pas de descendants sans décision explicite du parent : ancrer deux sous-systèmes comme deux enfants coûte la ventilation d'explorateurs de chacun. Ventile les explorateurs, pas les ancrages.

Nommer un fichier n'est pas ancrer le problème. Produis le modèle tracé prescrit par `how`. Si la conception redéfinit la propriété ou les couches, exécute aussi la compétence **why** sur la forme existante afin que la justification devienne une contrainte, pas une supposition. Un ancrage réduit à une passe unique nomme le test de l'Étape 1 de `how` qui l'autorise.

Saute la Phase A seulement quand le travail est réellement nouveau et qu'aucun système environnant n'est à intégrer.

## Phase B : Ébaucher

Exécute la compétence **arena** avec la tâche d'ébauche de conception et les artefacts d'ancrage de la Phase A. Passe `references/runner-prompt.md` comme prompt de chaque exécuteur. Chaque candidat produit un dossier de conception conforme à `references/rationale-template.md`.

Résous le panneau `architect runners`, par défaut avec trois tentatives héritant du modèle. Un panneau configuré doit contenir au moins deux entrées; signale un panneau plus court comme erreur de configuration au lieu de modifier silencieusement son compte. Résous les sélections complètes selon le contrat runtime, en conservant le modèle et l'effort de raisonnement. Passe ce panneau exact et ce compte à Arena; il a priorité sur `arena runners` pour cette invocation, même si les deux clés sont configurées. Signale toute surcharge explicite indisponible sans substituer silencieusement un autre modèle.

Conçois-le deux fois. Exige au moins deux candidats structurellement distincts avant la synthèse, même si le premier semble suffisant. C'est la référence au principe [Épuiser l’espace de conception](../cstack/references/principles/exhaust-the-design-space.md) rendue concrète. Il faut des alternatives de forme globale, pas des corrections ponctuelles dans une seule forme.

Passe chaque candidat au crible de [`references/design-red-flags.md`](references/design-red-flags.md) avant la synthèse. Rejette ou révise les modules superficiels, les fuites d'information, la décomposition temporelle et les méthodes relais.

Compare les candidats viables selon la profondeur d'interface. Préfère la conception qui cache le plus de complexité derrière une surface publique plus petite et plus simple. Une interface riche peut raccourcir les chaînes d'appels en concentrant la capacité au lieu de l'éparpiller entre les couches.

Arena retourne un dossier de conception synthétisé. La décision de synthèse remplit la section "Décision de synthèse" de la justification.

## Phase C : Valider (sur demande)

Si la tâche concrète autorise déjà l'implémentation, avance avec la conception synthétisée sans point de contrôle redondant. Pour une demande de conception seule ou en mode Codex Plan, retourne la conception et arrête avant l'implémentation.

Active un point de contrôle quand l'appelant le demande explicitement : "$cstack:architect avec point de contrôle", "arrête-toi et montre-moi avant d’implémenter", ou formulation semblable. Présente alors la conception synthétisée et mets-toi en pause pour validation.

Pendant une implémentation déjà autorisée, la synthèse peut être son propre commit, comme mode "échafaudage d’abord" de la référence au principe [Pensée fondatrice](../cstack/references/principles/foundational-thinking.md). Une invocation de conception seule ou en mode Plan ne crée pas de commits. Pour une pression adversariale avant l'implémentation, exécute la compétence **interrogate** sur l'ébauche synthétisée dans la même portée.

Si l'humain repousse la forme (dans un point de contrôle ou après coup), traite cela comme une preuve de Phase A. Ré-ancre et relance la Phase B avant d'écrire plus de code.

## Phase D : Implémenter selon l'ébauche

Remplace les corps `not implemented` par du code, le pseudocode par de la logique. L'ébauche synthétisée est le contrat.

Les écarts par rapport à l'ébauche sont des signaux à exposer, pas de la friction à absorber en silence. Si une fonction a besoin d'un paramètre que l'ébauche n'avait pas anticipé, demande si l'ébauche était mauvaise, si l'exigence a été manquée ou si l'implémentation va trop loin.

## Phase E : Jeter quand l'architecture est mauvaise

Si l'implémentation produit constamment de la friction que l'ébauche ne peut pas absorber, jette l'ébauche. Ne boulonne pas des correctifs sur une mauvaise conception, conformément aux références de principes [Reconcevoir depuis les premiers principes](../cstack/references/principles/redesign-from-first-principles.md) et [Corriger les causes racines](../cstack/references/principles/fix-root-causes.md).

Le signal est un *motif*, pas des cas isolés. Indices :

- La même forme de contournement apparaît à répétition dans du code sans lien direct.
- Plusieurs cas limites sans rapport exigent tous des branches spéciales.
- Des types ont besoin d'échappatoires (`any`, casts, champs optionnels toujours définis en pratique) pour compiler.
- Le réflexe "il nous faut un verrou" quand l'ébauche disait que l'état n'était pas partagé.
- Les appelants doivent connaître les règles internes de l'abstraction pour l'utiliser.
- Deux écarts de Phase D indépendants ou plus ont la même forme dans l'implémentation.

Fais preuve de jugement. Quelques cas limites ne condamnent pas une architecture. Certains problèmes sont légitimement complexes. La complexité dans les données n'est pas la complexité dans la conception.

Quand tu jettes :

1. Relance la compétence **how** sur ce qui a été construit.
2. Reconçois comme si les nouvelles contraintes avaient été des hypothèses du premier jour, conformément à la reconception depuis les premiers principes.
3. Soustrais avant d'ajouter, conformément à la référence au principe [Soustraire avant d’ajouter](../cstack/references/principles/subtract-before-you-add.md). La nouvelle ébauche doit être plus petite que l'ancienne avant de grandir.
4. Retourne à la Phase B et relance arena.

## Sorties

L'usage côté appelant est écrit d'abord et l'ébauche de types en dérive. Un seul fichier avec nouveaux types et signatures pour les petits changements. Carte de modules plus définitions de types pour les travaux plus larges. La justification accompagne le tout, conforme à `references/rationale-template.md`, avec l'ébauche d'usage et la décision de synthèse.

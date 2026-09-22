---
name: arena
description: "Lance N candidats en parallèle sur la même tâche, choisit une base et y greffe les meilleures parties des autres. Utiliser pour $cstack:arena, « passe ceci dans l'arène », « mets ceci dans l'arène », une comparaison concurrentielle, une course ou un choix entre N implémentations ou conceptions concurrentes."
---

# Arena

Contrat d’exécution : [`../cstack/references/codex-runtime.md`](../cstack/references/codex-runtime.md).

Pour chaque sélection avec `runtime`, applique le [dispatch CLI](../cstack/references/runtime-workers.md) à la place du lancement natif. Conserve la taille et l’ordre du panel, le rôle spécialisé et les étapes de vérification. Les replis single-agent de ce document concernent seulement les sélections natives ; une position CLI bloquée n’est jamais remplacée silencieusement par Codex.

Déploie N tentatives parallèles sur la même tâche. Lis chaque candidat de bout en bout. Choisis le plus solide comme base. Greffe-y les meilleures idées des autres. Vérifie le résultat synthétisé.

## Démarrage

Suis un élément par phase dans la tâche courante avant de lancer quoi que ce soit.

1. Cadrer
2. Déployer
3. Juger croisé
4. Choisir
5. Greffer
6. Vérifier

## Phase A : Cadrer

Les N candidats recevront le même prompt; le prompt est donc le contrat.

1. Nomme l'artefact que chaque candidat doit produire.
2. Derive la grille. Dis à quoi ressemble la réussite pour *cette* tâche, puis transforme-la en 3 à 6 critères concrets et notables. La grille est l'outil de sélection en phase D. Les candidats ne voient que la tâche.
3. Choisis les concurrents. Un panel explicite fourni par l'appelant a priorité, y compris celui résolu par Architect. Sinon, utilise `arena runners` dans `.cstack/models.json`, ou trois tentatives avec le modèle hérité s'il est absent. Résous les sélections complètes selon le contrat d’exécution et conserve le modèle ainsi que l'effort de raisonnement à chaque dispatch de concurrent; ne remplace pas silencieusement une sélection explicite indisponible. La taille du panel sélectionné fixe N. La capacité disponible limite seulement les exécutions simultanées, jamais le nombre total de candidats.
4. Assigne les chemins de sortie. Chaque candidat écrit dans son propre emplacement (un worktree git quand c'est possible, sinon `/tmp/arena-<slug>/candidate-<n>/`), selon la référence de principe [séparer avant de sérialiser l'état partagé](../cstack/references/principles/separate-before-serializing-shared-state.md).

## Phase B : Déployer

Lance les N workers en parallèle, selon leur sélection native ou CLI, chacun avec la tâche, le chemin vers le contexte partagé, son propre chemin de sortie et les consignes pour produire à la fois l'artefact et un court raisonnement. Donne à chaque agent rédacteur la propriété exclusive de son chemin de sortie. La concurrence native limite le nombre d'exécutions simultanées. Mets les candidats restants en file pour des vagues ultérieures. Si aucun emplacement de sous-agent n'est disponible, exécute chaque candidat dans la même session comme passe distincte et explicitement recadrée, étiquette le résultat `single-agent`, puis signale l'indépendance manquante. Le manque de capacité ne supprime jamais un candidat.

Chaque raisonnement nomme les alternatives envisagées par le candidat et ce qu'il a rejeté.

Si un candidat ne produit rien, continue avec N-1 et note l'abandon dans le registre de synthèse.

## Phase C : Juger croisé

Une fois tous les candidats de la phase B terminés, lance un worker de revue seule comme juge, selon sa sélection native ou CLI. Il hérite par défaut du modèle parent. Si `.cstack/models.json` définit `arena cross-judge pool`, suis le contrat d’exécution et ne remplace pas silencieusement une surcharge explicite indisponible. Le juge voit la grille et les candidats par étiquette de chemin, note chaque critère et recommande une base avec son raisonnement. Il peut tourner pendant la lecture du parent en phase D. Ne le lance pas pendant que les candidats écrivent encore. Si aucun emplacement de sous-agent n'est disponible, fais la passe du juge dans cette session après une relecture propre de chaque candidat, étiquette-la `single-agent review`, puis signale l'indépendance manquante. La comparaison ne disparaît jamais.

## Phase D : Choisir une base

Lis chaque candidat de bout en bout avant de choisir.

Note chaque candidat selon la grille, critère par critère, pas au ressenti global. Compare avec le juge croisé. Un accord sur la base confirme le choix. Un désaccord signifie que l'un de vous est biaisé ou que la grille était ambiguë. Lis les deux raisonnements avant de décider.

Choisis comme base le candidat qu'un futur mainteneur pourra étendre le plus facilement sans casser les invariants. Quand deux candidats semblent à égalité, préfère la frontière la plus nette ou la plus petite API, selon le Laziness Protocol.

Consigne le choix et sa raison dans une courte note de synthèse à côté de l'artefact de base, avec le verdict du juge croisé.

## Phase E : Greffer

Relis chaque candidat non retenu une fois de plus et identifie ce qui mérite d'être porté dans la base. Le signal tient habituellement en une ou deux choses par candidat, pas dans la majorité du contenu.

Intègre chaque greffe à la main, selon la référence de principe [reconcevoir depuis les premiers principes](../cstack/references/principles/redesign-from-first-principles.md). Ne colle pas mécaniquement. Le résultat doit rester cohérent sous un seul modèle mental.

Consigne ce qui a été greffé, depuis quel candidat, ainsi que ce qui a été rejeté et pourquoi.

Quand N candidats convergent vers la même forme, c'est un fort signal d'accord. Note la convergence dans le registre et livre la forme consensuelle. Aucune greffe n'est nécessaire. Quand N candidats divergent fortement, la phase A était sous-spécifiée. Recadre et relance au lieu de faire une moyenne de la divergence.

## Phase F : Vérifier

L'artefact synthétisé doit tenir sous le même examen que toute autre sortie, selon la référence de principe [prouver que ça marche](../cstack/references/principles/prove-it-works.md).

Si la vérification révèle un problème que l'arena n'a pas attrapé, soit la phase A était mauvaise (recadre et relance), soit un candidat l'avait capturé et tu as manqué la greffe (retourne à la phase E). Ne maquille pas le problème.

## Sorties

Un artefact synthétisé. Une courte note de synthèse à côté, nommant la base, les greffes (avec le candidat source), les rejets, les abandons s'il y en a et le résultat de vérification. Chaque affirmation porte sa preuve ou son étiquette dans la même phrase. Mesure, inférence ou supposition. Une prédiction ou une cause non observée est une supposition. Ne donne jamais à l'humain une vérification que tu pourrais exécuter.

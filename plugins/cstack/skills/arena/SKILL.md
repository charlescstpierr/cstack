---
name: arena
description: "Lance N candidats en parallèle sur la même tâche, choisit une base et y greffe les meilleures parties des autres. Utiliser pour $cstack:arena, « passe ceci dans l'arène », « mets ceci dans l'arène », une comparaison concurrentielle, une course ou un choix entre N implémentations ou conceptions concurrentes."
---

# Arena

Runtime : [délégation](../cstack/references/runtime/delegation.md), [modèles](../cstack/references/runtime/modeles.md), [orchestration](../cstack/references/runtime/orchestration.md) · rôles : `arena runners`, `arena cross-judge pool`.

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
3. Choisis les concurrents. Un panel explicite fourni par l'appelant a priorité, y compris celui résolu par Architect. Sinon, utilise `arena runners`. La taille du panel fixe N ; la capacité limite seulement les exécutions simultanées, jamais le nombre de candidats.
4. Assigne les chemins de sortie. Chaque candidat écrit dans son propre emplacement (un worktree git quand c'est possible, sinon `/tmp/arena-<slug>/candidate-<n>/`), selon la référence de principe [séparer avant de sérialiser l'état partagé](../cstack/references/principles/separate-before-serializing-shared-state.md).

## Phase B : Déployer

Lance les N workers en parallèle, chacun avec la tâche, le chemin du contexte partagé, son propre chemin de sortie en propriété exclusive et la consigne de produire l'artefact et un court raisonnement.

Chaque raisonnement nomme les alternatives envisagées par le candidat et ce qu'il a rejeté.

Si un candidat ne produit rien, continue avec N-1 et note l'abandon dans le registre de synthèse.

## Phase C : Juger croisé

Une fois tous les candidats de la phase B terminés, lance un juge en revue seule (`arena cross-judge pool`). Il voit la grille et les candidats par étiquette de chemin, note chaque critère et recommande une base avec son raisonnement. Il peut tourner pendant la lecture du parent en phase D. Ne le lance pas pendant que les candidats écrivent encore.

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

Un artefact synthétisé. Une courte note de synthèse à côté, nommant la base, les greffes (avec le candidat source), les rejets, les abandons s'il y en a et le résultat de vérification. Chaque affirmation porte sa preuve ou son étiquette : mesuré, inféré ou supposition (toute prédiction ou cause non observée) ; ne laisse à l'humain aucune vérification exécutable.

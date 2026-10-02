---
name: arena
description: "À utiliser pour $cstack:arena, « passe ceci dans l'arène », « mets ceci dans l'arène », une comparaison concurrentielle, une course ou un choix entre N implémentations ou conceptions concurrentes. Lance N candidats en parallèle sur la même tâche, choisit une base et y greffe les meilleures parties des autres."
---

# Arena

Runtime : [règles communes](../cstack/references/runtime/base.md), [délégation](../cstack/references/runtime/delegation.md), [modèles](../cstack/references/runtime/modeles.md), [orchestration](../cstack/references/runtime/orchestration.md) · rôles : `arena runners`, `arena cross-judge pool`.

Déploie N tentatives parallèles sur la même tâche. Lis chaque candidat de bout en bout. Choisis le plus solide comme base. Greffe-y les meilleures idées des autres. Vérifie le résultat synthétisé.

## Démarrage

Suis un élément par phase dans la tâche courante avant de lancer quoi que ce soit.

1. Cadrer
2. Déployer
3. Vérifier chaque candidat, puis juger croisé
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

## Phase C : Vérifier chaque candidat, puis juger croisé

Une fois tous les candidats de la phase B terminés, gèle leurs sorties.

1. **Vérifier chaque candidat.** Quand l'artefact est exécutable ou vérifiable, lance la même vérification du projet (tests, typecheck, commande VERIFY) dans l'emplacement de chaque candidat, et note pour chacun vert, rouge avec l'échec, ou non vérifiable avec la raison. Une conception sans contrôle exécutable est non vérifiable ; ne la déclare pas verte.
2. **Anonymiser.** Donne aux candidats des étiquettes neutres tirées dans un ordre aléatoire (`cand-A`, `cand-B`…). Retire des chemins, raisonnements et rapports transmis au juge les noms de runtime, de modèle et de reçu. Garde la correspondance étiquette → candidat pour toi seul.
3. **Juger.** Lance un juge en revue seule (`arena cross-judge pool`). Il voit la grille, les candidats anonymisés et leurs résultats de vérification, note chaque critère et recommande une base avec son raisonnement. À partir de trois candidats, lance un second jugement indépendant qui reçoit les candidats dans l'ordre inverse. Si les deux jugements ne recommandent pas la même base, c'est un signal de biais de position ou d'une grille ambiguë : consigne-le pour la phase D.

Le juge peut tourner pendant la lecture du parent en phase D. Ne le lance pas pendant que les candidats écrivent encore.

## Phase D : Choisir une base

Lis chaque candidat de bout en bout avant de choisir.

Note chaque candidat selon la grille, critère par critère, pas au ressenti global. Un candidat rouge à la vérification de la phase C ne peut pas devenir la base, sauf si tous les candidats vérifiables sont rouges ; dis-le alors dans la note de synthèse. Ses bonnes idées restent greffables en phase E. Compare avec le juge croisé. Un accord sur la base confirme le choix. Un désaccord signifie que l'un de vous est biaisé ou que la grille était ambiguë. Lis les deux raisonnements avant de décider.

Choisis comme base le candidat qu'un futur mainteneur pourra étendre le plus facilement sans casser les invariants. Quand deux candidats semblent à égalité, préfère la frontière la plus nette ou la plus petite API, selon le Laziness Protocol.

Consigne le choix et sa raison dans une courte note de synthèse à côté de l'artefact de base, avec les résultats de vérification par candidat et le verdict du juge croisé, ou les deux verdicts et leur désaccord éventuel.

## Phase E : Greffer

Relis chaque candidat non retenu une fois de plus et identifie ce qui mérite d'être porté dans la base. Le signal tient habituellement en une ou deux choses par candidat, pas dans la majorité du contenu.

Intègre chaque greffe à la main, selon la référence de principe [reconcevoir depuis les premiers principes](../cstack/references/principles/redesign-from-first-principles.md). Ne colle pas mécaniquement. Le résultat doit rester cohérent sous un seul modèle mental.

Consigne ce qui a été greffé, depuis quel candidat, ainsi que ce qui a été rejeté et pourquoi.

Quand N candidats convergent vers la même forme, c'est un fort signal d'accord. Note la convergence dans le registre et livre la forme consensuelle. Aucune greffe n'est nécessaire. Quand N candidats divergent fortement, la phase A était sous-spécifiée. Recadre et relance au lieu de faire une moyenne de la divergence.

## Phase F : Vérifier

L'artefact synthétisé doit tenir sous le même examen que toute autre sortie, selon la référence de principe [prouver que ça marche](../cstack/references/principles/prove-it-works.md).

Si la vérification révèle un problème que l'arena n'a pas attrapé, soit la phase A était mauvaise (recadre et relance), soit un candidat l'avait capturé et tu as manqué la greffe (retourne à la phase E). Ne maquille pas le problème.

## Sorties

Un artefact synthétisé. Une courte note de synthèse à côté, nommant la base, les greffes (avec le candidat source), les rejets, les abandons s'il y en a, la vérification de chaque candidat et le résultat de vérification final. Chaque affirmation porte sa preuve ou son étiquette : mesuré, inféré ou supposition (toute prédiction ou cause non observée) ; Ne donne jamais à l'humain une vérification que tu pourrais exécuter.

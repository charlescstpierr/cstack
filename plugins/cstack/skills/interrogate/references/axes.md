# Axes Standards, Spec et Adversarial

Lis ce document aux Étapes 3 et 4 de [interrogate](../SKILL.md) pour affecter les axes selon la taille du panel et synthétiser par axe.

## Panel

La longueur du panneau `interrogate reviewers` est le nombre exact de reviewers ; une revue impossible suit [Orchestration requise](../../cstack/references/runtime/orchestration.md) avec `route: Review`.

## Affectation des axes

Le panneau par défaut contient trois reviewers avec ces responsabilités :

- Reviewer 1 : Standards, en utilisant les sources de standards fournies par le dépôt.
- Reviewer 2 : Spec, en utilisant seulement les preuves d'exigences approuvées. Sans source approuvée, rapporte l'écart de preuve et n'invente pas d'exigences.
- Reviewer 3 : Adversarial, couvrant exactitude, sécurité, cause racine, vérification et maintenabilité.

Pour un panneau à deux reviewers, combine Adversarial avec Standards et garde Spec séparé. Pour un panneau à un reviewer, couvre tous les axes en une passe et divulgue qu'il n'y a pas de revues d'axes indépendantes. Pour un panneau plus grand que trois, garde ces trois premières affectations et donne une couverture complète à chaque reviewer additionnel. Chaque reviewer peut rapporter une finding à fort impact d'un autre axe quand les preuves le soutiennent, tout en gardant l'axe assigné comme principal. Cela préserve le compte configuré; n'ajoute pas un second panneau "Matt".

## Synthèse par axe

À mesure que les résultats reviennent, construis une image unifiée :

1. **Analyse toutes les findings** des reviewers et conserve l'axe principal de chaque finding.
2. **Garde séparés les résultats Standards et Spec.** Le consensus est une preuve dans un axe, pas une raison de rétrograder une finding d'exigence Spec unique parce qu'un seul reviewer avait l'affectation Spec.
3. **Identifie le consensus**. Les findings soulevées indépendamment par au moins deux reviewers sont le signal le plus fort dans leur axe.
4. **Identifie les findings d'un seul reviewer**. Elles valent encore lecture, surtout les findings Spec, sécurité ou exactitude concrètes; pondère-les par preuve, pas seulement par nombre de reviewers.
5. **Déduplique**. Les reviewers peuvent décrire le même problème différemment. Fusionne seulement quand elles partagent le même axe et mécanisme, et note quels reviewers les ont soulevées.
6. **Note les désaccords**. Si un reviewer signale quelque chose et qu'un autre dit explicitement l'inverse, garde le désaccord sous l'axe pertinent.
7. **Rejette la dérive de portée**. Écarte les findings fondées sur des fichiers ou exigences hors de l'instantané figé, et signale toute affirmation non vérifiée sur un worktree changeant.

---
name: interrogate
description: >-
  À utiliser pour $cstack:interrogate, « revue adversariale », « revue
  multi-modèle », « conteste ceci », « mets ce code à l'épreuve », « trouve les
  angles morts » ou « démonte ceci ». Des reviewers indépendants contestent les
  changements sous plusieurs angles.
---

# Interrogate

Runtime : [`../cstack/references/codex-runtime.md`](../cstack/references/codex-runtime.md).

Pour chaque sélection avec `runtime`, applique le [dispatch CLI](../cstack/references/runtime-workers.md) à la place du lancement natif. Conserve la taille et l’ordre du panel, le rôle spécialisé et les étapes de vérification. Les replis single-agent de ce document concernent seulement les sélections natives ; une position CLI bloquée n’est jamais remplacée silencieusement par Codex.

Lance exactement le nombre configuré de reviewers indépendants pour relire adversarialement des changements de code. Chaque reviewer reçoit le même instantané de portée, les mêmes preuves d'exigences approuvées, le même prompt et la même rubrique, avec un axe principal assigné. Le signal adversarial vient des passes indépendantes et, quand des surcharges de modèles vérifiées sont disponibles, de la diversité des modèles. N'ajoute pas de reviewers au-delà du panneau configuré.

Le livrable est un verdict synthétisé. N'applique PAS automatiquement les changements.

Suis le chemin d'héritage direct du contrat runtime quand rien n'est configuré; sinon résous chaque rôle nommé avec son helper et transmets à chaque dispatch la sélection complète, effort de raisonnement compris. Signale les lacunes de capacité de l'hôte au lieu de supprimer un champ sélectionné.

## Étape 1, Déterminer la portée

Identifie ce qui doit être relu depuis le contexte :

- Si l'utilisateur pointe vers des fichiers ou un diff précis, utilise cela.
- Si l'utilisateur demande le travail courant ou en cours, fige une seule fois les SHA exacts de base et de `HEAD`. Capture `git diff <base-sha>...<head-sha>`, `git diff --cached` et `git diff` pour les changements commités, staged et unstaged suivis, puis liste les fichiers non suivis avec `git ls-files --others --exclude-standard` et instantane leur contenu avec des lectures natives. Ne lance jamais `git add`, `git stash`, `git checkout`, `git reset` ni une autre commande qui change le worktree. Enregistre l'heure de l'instantané; si le worktree change pendant sa lecture, indique que l'instantané de contenu peut ne pas être atomique.
- Si l'utilisateur demande une branche, une plage de commits ou une revue de PR, fige une seule fois les SHA base et head résolus et relis seulement cette portée commit-à-commit. N'inclus pas silencieusement les changements sales du worktree.
- Si le message utilisateur référence un travail récent, rassemble les fichiers pertinents et préserve la portée demandée.

Emballe la portée figée (ou l'instantané de contenu) plus seulement les fichiers de contexte environnants dont les reviewers ont besoin pour comprendre le code. Une comparaison à trois points est valide seulement pour les SHA de commits figés; elle ne prouve pas la couverture du travail staged, unstaged ou non suivi.

## Étape 2, Énoncer l'intention

Avant de lancer les reviewers, énonce explicitement l'intention et les preuves d'exigences. Les exigences viennent seulement d'une spec approuvée par l'utilisateur, d'une issue ou d'un énoncé de conversation. N'infère pas d'exigences depuis l'implémentation, les messages de commit ou le comportement apparent du code. Si aucune source d'exigences approuvée n'existe, enregistre un écart de preuve Spec et poursuis la revue Standards et adversariale sans inventer ni bloquer sur les exigences.

Dérive l'intention depuis :

- Le message de l'utilisateur
- Une spec ou issue approuvée fournie par l'utilisateur
- Une description de PR ou un énoncé de conversation approuvé

Écris un paragraphe clair et nomme chaque source d'exigences fournie. Si la source approuvée est incomplète, rapporte l'écart au lieu de le combler depuis le code.

## Étape 3, Lancer les reviewers

Résous `interrogate reviewers` une fois selon le contrat runtime. La longueur de son panneau est le nombre exact de reviewers, borné seulement par la concurrence native; mets les tentatives excédentaires en vagues. Préserve la sélection complète du modèle et de l'effort de raisonnement pour chaque position. Quand aucun slot de subagent n'est disponible, exécute chaque passe reviewer dans la même session comme passe séparée et explicitement recadrée, étiquette le résultat `single-agent` et signale l'indépendance manquante. L'absence de capacité ne supprime jamais un reviewer ni un axe. Le panneau par défaut contient trois reviewers avec ces responsabilités :

- Reviewer 1 : Standards, en utilisant les sources de standards fournies par le dépôt.
- Reviewer 2 : Spec, en utilisant seulement les preuves d'exigences approuvées. Sans source approuvée, rapporte l'écart de preuve et n'invente pas d'exigences.
- Reviewer 3 : Adversarial, couvrant exactitude, sécurité, cause racine, vérification et maintenabilité.

Pour un panneau à deux reviewers, combine Adversarial avec Standards et garde Spec séparé. Pour un panneau à un reviewer, couvre tous les axes en une passe et divulgue qu'il n'y a pas de revues d'axes indépendantes. Pour un panneau plus grand que trois, garde ces trois premières affectations et donne une couverture complète à chaque reviewer additionnel. Chaque reviewer peut rapporter une finding à fort impact d'un autre axe quand les preuves le soutiennent, tout en gardant l'axe assigné comme principal. Cela préserve le compte configuré; n'ajoute pas un second panneau "Matt".

Lis `references/reviewer-prompt.md` et remplis le modèle avec :
1. L'intention énoncée
2. L'instantané de portée figée, avec ses SHA base et head et l'indication d'inclusion ou non des fichiers sales du worktree
3. Les preuves d'exigences approuvées, ou l'écart explicite de preuve Spec
4. L'axe principal du reviewer et les autres axes qu'il peut rapporter quand l'impact est fort
5. Le diff ou les contenus de fichiers
6. La rubrique de revue depuis `references/rubric.md`
7. La lentille de qualité de code depuis `references/code-quality-review.md`

Le même modèle rempli va à tous les reviewers, donc chaque passe applique la lentille de qualité de code.

## Étape 4, Synthétiser

À mesure que les résultats reviennent, construis une image unifiée :

1. **Analyse toutes les findings** des reviewers et conserve l'axe principal de chaque finding.
2. **Garde séparés les résultats Standards et Spec.** Le consensus est une preuve dans un axe, pas une raison de rétrograder une finding d'exigence Spec unique parce qu'un seul reviewer avait l'affectation Spec.
3. **Identifie le consensus**. Les findings soulevées indépendamment par au moins deux reviewers sont le signal le plus fort dans leur axe.
4. **Identifie les findings d'un seul reviewer**. Elles valent encore lecture, surtout les findings Spec, sécurité ou exactitude concrètes; pondère-les par preuve, pas seulement par nombre de reviewers.
5. **Déduplique**. Les reviewers peuvent décrire le même problème différemment. Fusionne seulement quand elles partagent le même axe et mécanisme, et note quels reviewers les ont soulevées.
6. **Note les désaccords**. Si un reviewer signale quelque chose et qu'un autre dit explicitement l'inverse, garde le désaccord sous l'axe pertinent.
7. **Rejette la dérive de portée**. Écarte les findings fondées sur des fichiers ou exigences hors de l'instantané figé, et signale toute affirmation non vérifiée sur un worktree changeant.

## Étape 5, Jugement du lead

Tu es le lead reviewer, un ingénieur senior pragmatique, pas un agrégateur neutre.

Lis `references/lead-judgment.md` pour le cadre complet.

Classe chaque finding dans ces seaux :

- **Act on**. Vrais problèmes qui affectent exactitude, sécurité ou maintenabilité au regard des objectifs réels. Ils bloqueraient une vraie PR.
- **Consider**. Points légitimes, mais tu n'es pas sûr qu'ils valent leur coût maintenant. Méritent l'attention de l'utilisateur.
- **Noted**. Techniquement valides mais non actionnables. Dépendants du contexte, optimisation prématurée ou faible impact au stade courant.
- **Dismissed**. Faux, pinailleur ou manquant de contexte. Brève explication du pourquoi.

Pour chaque finding, inclus :
- Quel reviewer ou quels reviewers l'ont soulevée
- L'axe : Standards, Spec ou Cross-cutting
- La catégorie (act on / consider / noted / dismissed)
- Une justification d'une ligne pour la classification

## Format de sortie

Présente le verdict avec cette structure :

Chaque affirmation porte sa preuve ou son étiquette dans la même phrase. Mesuré, inféré ou supposition. Une prédiction ou une cause non observée est une supposition. Ne donne jamais à l'humain une vérification que tu pourrais exécuter.

### Intent
> [Le paragraphe d'intention énoncé à l'Étape 2]

### Reviewers
- Reviewer [label] : [nom du modèle si connu, sinon inherited], [N findings] (une puce par reviewer)

### Standards
[Findings Standards, classées act on / consider / noted / dismissed. Cite le standard fourni ou étiquette un jugement de baseline.]

### Spec
[Findings Spec, classées act on / consider / noted / dismissed. Cite l'exigence approuvée. Si aucune source approuvée n'existe, indique l'écart de preuve et ne fabrique pas de findings.]

### Cross-cutting and adversarial
[Findings à fort impact qui traversent les axes ou viennent de l'affectation adversariale. Garde leurs étiquettes d'axe originales.]

### Act On
[Findings transversales à traiter. Pour chacune : description, reviewers qui l'ont soulevée, pourquoi cela compte.]

### Consider
[Findings transversales à considérer. Pour chacune : description, reviewers qui l'ont soulevée, compromis impliqué.]

### Noted
[Valide mais faible priorité. Liste brève.]

### Dismissed
[Findings rejetées avec brève justification.]

### Agreement Map
[Où les reviewers sont d'accord, où ils divergent et ce que le motif révèle.]

---
name: interrogate
description: >-
  À utiliser pour $cstack:interrogate, « revue adversariale », « revue
  multi-modèle », « conteste ceci », « mets ce code à l'épreuve », « trouve les
  angles morts » ou « démonte ceci ». Des reviewers indépendants contestent les
  changements sous plusieurs angles.
---

# Interrogate

Runtime : [délégation](../cstack/references/runtime/delegation.md), [modèles](../cstack/references/runtime/modeles.md), [orchestration](../cstack/references/runtime/orchestration.md) · rôles : `interrogate reviewers`.

Lance exactement le nombre configuré de reviewers indépendants pour relire adversarialement des changements de code. Chaque reviewer reçoit le même instantané de portée, les mêmes preuves d'exigences approuvées, le même prompt et la même rubrique, avec un axe principal assigné. Le signal adversarial vient des passes indépendantes et, quand des surcharges de modèles vérifiées sont disponibles, de la diversité des modèles. N'ajoute pas de reviewers au-delà du panneau configuré.

Le livrable est un verdict synthétisé. N'applique PAS automatiquement les changements.

## Étape 1, Déterminer la portée

Identifie ce qui doit être relu depuis le contexte :

- Si l'utilisateur pointe vers des fichiers ou un diff précis, utilise cela.
- Pour le travail courant, une branche, une plage ou une PR, fige une seule fois les SHA base et head selon [l'instantané figé](references/scope-snapshot.md), sans jamais changer le worktree.
- Si le message utilisateur référence un travail récent, rassemble les fichiers pertinents et préserve la portée demandée.

## Étape 2, Énoncer l'intention

Avant de lancer les reviewers, énonce explicitement l'intention et les preuves d'exigences. Les exigences viennent seulement d'une spec approuvée par l'utilisateur, d'une issue ou d'un énoncé de conversation. N'infère pas d'exigences depuis l'implémentation, les messages de commit ou le comportement apparent du code. Si aucune source d'exigences approuvée n'existe, enregistre un écart de preuve Spec et poursuis la revue Standards et adversariale sans inventer ni bloquer sur les exigences.

Dérive l'intention depuis le message de l'utilisateur, une spec ou issue approuvée fournie par l'utilisateur, ou une description de PR ou un énoncé de conversation approuvé. Écris un paragraphe clair et nomme chaque source d'exigences fournie. Si la source approuvée est incomplète, rapporte l'écart au lieu de le combler depuis le code.

## Étape 3, Lancer les reviewers

Résous `interrogate reviewers` une fois; la longueur du panneau est le nombre exact de reviewers, dans l'ordre, et l'absence de capacité ne supprime jamais un reviewer ni un axe. Par défaut : Standards, Spec, Adversarial. Affecte les axes selon la taille du panel avec [les règles d'axes](references/axes.md).

Remplis `references/reviewer-prompt.md` avec l'intention, l'instantané figé (SHA base et head, fichiers sales inclus ou non), les preuves d'exigences ou l'écart Spec, l'axe principal et les axes rapportables à fort impact, le diff ou les fichiers, `references/rubric.md` et `references/code-quality-review.md`. Le même modèle rempli va à tous les reviewers, donc chaque passe applique la lentille de qualité de code.

## Étape 4, Synthétiser

Synthétise par axe selon [les règles d'axes](references/axes.md#synthèse-par-axe) : garde Standards et Spec séparés, pondère par preuve et non par nombre, déduplique seulement à axe et mécanisme égaux, garde les désaccords et rejette la dérive hors de l'instantané figé.

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

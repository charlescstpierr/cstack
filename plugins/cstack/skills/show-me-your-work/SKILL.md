---
name: show-me-your-work
description: "À utiliser pour $cstack:show-me-your-work, les exécutions autonomes ou multi-phases, ou le travail qu'un humain relit après s'être absenté. Garde une trace de décisions relisible pour les travaux longs ou sans surveillance : un journal TSV avec une ligne par décision (quoi, pourquoi, preuve, résultat). Local par défaut ; committe-le quand un relecteur a besoin de la trace pour faire confiance au résultat."
---

# Montrer ton travail

Runtime : [règles communes](../cstack/references/runtime/base.md), [délégation](../cstack/references/runtime/delegation.md), [modèles](../cstack/references/runtime/modeles.md), [orchestration](../cstack/references/runtime/orchestration.md) · rôle : `judgment and prose`.

Garde un journal canonique unique.

## Le format

Un seul fichier TSV, une ligne par décision. Les cellules restent sur une seule ligne. La preuve est un pointeur, pas de la prose.

Copie `references/decision-log-template.tsv` (la ligne d'en-tête) pour démarrer un journal propre. Colonnes :

- **ts.** Horodatage ISO8601.
- **phase.** La phase où le flux de travail.
- **décision.** Ce qui a été choisi ou fait, en une ligne.
- **why.** La raison en mots simples. Si un principe l'a guidée, dis-le clairement, pas comme une étiquette de jargon.
- **évidence.** Un lien ou chemin qui le prouve : SHA de commit, numéro de PR, `file:line`, ou chemin d'artefact, trace ou capture. Jamais un paragraphe.
- **result.** Le résultat ou l'état du prédicat : `tests green`, `reverted`, `pixel-diff 0`, `INCONCLUSIVE`, `open`.

Exemple formule simplement pour qu'un relecteur le lise d'un coup d'œil. C'est une illustration seulement. Ne copie pas ces lignes dans un vrai journal.

```
ts	phase	decision	why	evidence	result
2026-05-24T09:02:00Z	cadrage	compte le travail d'abord, environ 100 composants et 75 heures	voulais connaître la taille avant de démarrer une longue exécution	commit 3a9f1c2	trouver 5 choses à régler avant de commencer
2026-05-24T09:40:00Z	harnais	pris des captures de l'ancienne version avant de changer quoi que ce soit	pour comparer ancien contre nouveau et attraper tout changement visuel	scripts/snapshot.sh, baseline/	sauve 120 captures de référence
2026-05-24T11:15:00Z	widget	migre les styles du widget sans changer son apparence	garder le changement petit et le résultat identique	commit 7c21e0a, pixel-diff 0	apparence identique, tests passants
2026-05-24T12:30:00Z	widget	rejete le travail d'un helper parce que ses captures etaient vides	vérifie les vrais fichiers au lieu de faire confiance à son resume	worktree reset	reverte, consignes durcies pour la prochaine fois
```

## Journaliser une ligne

Écris chaque entrée comme tu raconterais à un coéquipier ce que tu as fait. Mots simples, actions concrètes, pas de langage IA ni de jargon abstrait (la skill **unslop** s'applique aussi au texte du journal).

Utilise le helper `scripts/log.sh <logfile> <phase> <decision> <why> <evidence> <result>`. Il tamponne `ts`, écrit l'en-tête à la première utilisation, retire les tabulations/nouvelles lignes parasites et préfixe toute cellule commençant par `=`, `+`, `-` ou `@` avec une apostrophe simple. Un simple `printf` qui ajoute une ligne fonctionne aussi, mais surveille ces mêmes octets si les cellules viennent de texte généré ou fourni par l'utilisateur.

Journalise les points de décision et checkpoints, pas chaque action : un embranchement choisi, une unité terminée avec son résultat de vérification, un pivot ou revert avec son déclencheur, un bloqueur remonté, une portée corrigée. Pour les boucles, une ligne par itération. Saute le trivial et l'évident.

## Ou il vit

Par défaut, le journal est un artefact de travail non suivi dans `.cstack/tasks/<task-slug>/decisions.tsv` dans le workspace cible. Donne des répertoires distincts aux tâches concurrentes.

Exporte une copie assainie vers un chemin de rapport suivi seulement quand l'utilisateur demande explicitement une trace d'comité d'audit. Préserve le journal de tâche original et exclut les identifiants secrets ainsi que le contenu de conversation sans rapport.

## Règles

- Une ligne est une décision ou un checkpoint.
- Ajout seulement. Un mauvais choix reçoit une nouvelle ligne qui le remplace. Ne modifie ou supprime jamais l'historique.
- Préfère les preuves produites par des scripts committés aux one-offs faits à la main (référence de principe [encoder les leçons dans la structure](../cstack/references/principles/encode-lessons-in-structure.md)).

## Auditer le journal contre le registre de tâche

À la fin de l'exécution, vérifie que le journal dit la vérité. Préfère les outils natifs d'historique de tâches bornées à ce projet et à cette tâche. Sinon, utilise le contexte courant et les checkpoints. Lis une transcription locale seulement quand ses métadonnées correspondent explicitement à ce projet et à cette session; n'infère jamais un chemin de stockage et ne scanne pas de projets sans rapport. Compare le journal avec ce qui s'est vraiment passé :

- Chaque ligne correspond à une vraie action. Coupe les entrées inventées ou aspirationnelles.
- La preuve de chaque ligne se résout et montre ce que la ligne affirme.
- Un embranchement, pivot ou approche abandonnée qui a façonné le travail sans être journalisé est un manque. Ajoute-le.
- Supprime le remplissage.

Corrige le journal, pas l'histoire. Si le travail a diverge de ce qu'une ligne affirme, la ligne est fausse.

## Revue indépendante de la trace

Avant de rendre, exécute une revue indépendante de la trace. Préfère un relecteur natif. Le relecteur lit la trace d'audit et le registre de tâche, puis signale les preuves faibles où les risqués. La revue ne disparaît jamais.

- Decisions journalisées avec preuves faibles ou absentes.
- Étapes de vérification sautées ou affirmées sans preuve dans le registre de tâche.
- Choix qui semblent risqués avec le recul (prématurés, élargissant la portée, masquant un symptôme).
- Manques que l'utilisateur raterait autrement en lecture rapide.

Chaque réponse pour une exécution qui a produit une trace se termine par une section "Attention". Identifie un vrai relecteur délégué comme `independent native reviewer`, ou étiquette le fallback `single-agent audit`, fait sur une relecture propre de la trace. Inclus un modèle seulement quand le contrat d’exécution le rapporte. Liste les signalements avec des lignes ou moments précis; ne traite pas une revue indépendante manquante comme un verdict indépendant propre.

## Relire la trace

Lis de haut en bas, suis les pointeurs de preuve, vérifie ponctuellement. GitHub rend un TSV explicitement exporté comme tableau. Exécute `column -s$'\t' -t "<workspace>/.cstack/tasks/<task-slug>/decisions.tsv"` avec le vrai workspace et slug de tâche pour inspecter la trace locale dans un terminal.

## Composer avec cette skill

Les autres skills routent leur trace d'audit ici au lieu d'en inventer une. Référence-la par nom et laisse-la posséder le format. Ne répète pas les colonnes.

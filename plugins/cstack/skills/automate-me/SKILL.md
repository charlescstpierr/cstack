---
name: automate-me
description: "À utiliser pour $cstack:automate-me, « automate me », « create/update/refresh my -mode skill » ou pour transformer les préférences et le style de travail de l'utilisateur en skill. Rédige ou révise une skill personnelle -mode avec $cstack:unslop, en utilisant facultativement l'historique récent borné au projet."
---

# Automate me

Runtime : [règles communes](../cstack/references/runtime/base.md), [délégation](../cstack/references/runtime/delegation.md), [intégrations](../cstack/references/runtime/integrations.md).

Un flux guide pour transformer les conventions de travail de l'utilisateur en skill que les agents suivront. La sortie est une skill `-mode` adaptee à lui (par exemple `jay-mode`, `priya-mode`).

Cette skill enchaine une passe d'extraction en ligne, la skill native `skill-creator` quand elle est disponible, puis la skill **unslop**. Si `skill-creator` est indisponible, écris directement la skill valide minimale.

## Flux

### 0. Vérifier s'il existe déjà une skill

Cherche récursivement une `.agents/skills/**/*-mode/SKILL.md` locale au projet et une `$CODEX_HOME/skills/**/*-mode/SKILL.md` personnelle correspondant à l'identifiant de l'utilisateur. Quand `CODEX_HOME` n'est pas défini, utilise `~/.codex/skills`. S'il en existe une et que l'utilisateur n'a pas déjà dit "update my skill" ou équivalent, utilise l'outil natif d'entrée utilisateur structurée pour choisir :

- Mettre à jour la skill existante (défaut lors des exécutions répétées)
- Repartir de zéro (rare, demander pourquoi avant de le faire)

Le mode mise à jour change le reste du flux :
- L'étape 1 extrait seulement l'historique depuis la dernière modification de la skill (`git log -1 --format=%cI <path>`).
- L'étape 2 demande ce qui a changé ou manque, pas ce qu'il faut capturer depuis zéro.
- L'étape 4 modifie le fichier existant en place. Préserve les sections que l'utilisateur n'a pas contredites. Révise celles qui ont de nouvelles preuves. Ajoute de nouvelles sections seulement pour des règles vraiment nouvelles.

### 1. Extraire son historique

Utilise les outils natifs d'historique de tâches bornées au projet actif quand ils sont disponibles. Sinon, utilise le contexte de la tâche courante et les checkpoints explicites. Lis les fichiers de transcription locaux seulement quand leurs métadonnées correspondent explicitement au projet actif et à la session demandée; ne devine jamais un chemin de stockage et ne scanne pas de projets sans rapport. Exclus les passages `<private>` selon [l'état](../cstack/references/runtime/etat.md).

Examine uniquement la période demandée pour chercher les motifs récurrents. Parallélise des tranches bornées d'historique quand le corpus est assez grand pour que ça aide. Chaque sous-agent d'extraction renvoie une courte liste structurée avec des pointeurs de preuve. Signaux par défaut qui valent la peine d'être cherchés :

- Préférences de réponse (longueur, ton, format, corrections du type "dumb it down")
- Habitudes de délégation (sous-agents, modèles, flux de travail spécialisés, parallélisme)
- Posture de vérification (ce que "termine" signifie, tests unitaires vs repro live, relecteurs)
- Discipline de code et de prose (style, principes cites, outils de lint/format)
- Conventions de processus (worktrees, commits, PR, outils de revue/merge)
- Préférences meta (corriger des skills en cours de tâche, en proposer de nouvelles)

Recoupe les tranches avant de promouvoir un signal. Les motifs vus dans au moins deux tranches ont une forte confiance. Les signaux isolés sont faibles et sont habituellement abandonnés.

### 2. Demander directement à l'utilisateur

L'extraction manque les intentions qui ne se sont pas encore manifestees. Utilise l'outil natif d'entrée utilisateur structurée quand il est disponible.

Forme : une ou deux questions avec 4 à 6 options chacune, `allow_multiple: true` pour les questions de catégorie. Commence large ("Quelles zones comptent le plus ?"), puis poursuis sur les zones choisies avec des options précises. Après les tours structures, une question libre dans le chat capturé ce que les options ont manque.

Ne déverse pas 20 questions.

### 3. Regrouper les constats

Regroupe les signaux combinés en sections. Sections courantes (utilise seulement ce qui s'applique) :

- **Style de réponse** : longueur, ton, format.
- **Autonomie** : combien faire sans demander, usage des outils MCP.
- **Comprendre d'abord** : quelles skills prendre pour cadrer ou enquêter sur un changement.
- **Sous-agents** : défaut, parallélisme, modèle par tâche, flux de travail spécialisés.
- **Discipline prose / code** : principes, outils de lint, guides de style.
- **Revue et vérification** : posture de repro, skills de vérification, outils de tests live.
- **Processus** : worktrees git, commits, PR, outils de revue/merge.
- **Skills** : habitudes de création de skills, corriger-la-skill-d'abord, proposer de nouvelles skills.

La skill **cstack** montre la forme. Lis-la pour le niveau de granularité. Ne copie pas son contenu; les règles de l'utilisateur lui appartiennent.

### 4. Rediger la skill

Utilise la skill native `skill-creator` quand elle est présente. Sinon, crée directement un `SKILL.md` autonome. Emplacement :

- Chemin : préserve la catégorie d'une skill mode existante. Pour un nouveau mode local au projet, utilise `.agents/skills/<handle>-mode/SKILL.md`. Pour une skill personnelle, utilise `$CODEX_HOME/skills/<handle>-mode/SKILL.md` ou `~/.codex/skills/<handle>-mode/SKILL.md` quand `CODEX_HOME` n'est pas défini.
- Identifiant : le prénom de l'utilisateur ou l'identifiant choisi.
- Frontmatter `description` : déclencher sur son nom + `$<handle>-mode` + "travailler dans son style", pas sur des mots-clés génériques comme "écrire du code" ou "relire une PR".
- Formatage du frontmatter : suis `skill-creator` quand disponible. Garde `description` comme un scalaire YAML. Mets-la entre guillémets ou utilise `description: >-` avec des lignes de continuation indentées quand la ponctuation ou le wrapping l'exige.
- Rends l'invocation explicite par défaut avec le réglage `policy.allow_implicit_invocation: false` dans `agents/openai.yaml`. Active l'invocation implicite seulement si l'utilisateur la veut explicitement.

### 5. Iterer sur la prose

Applique la skill **unslop** et, quand elles sont disponibles, les consignes de rédaction de `skill-creator` à chaque ligne.

Montre le brouillon à l'utilisateur et prends ses retours. Prévois plusieurs itérations. Coupe sans pitié. Une skill mode n'est pas un manuel.

### 6. La livrer

Valide la skill et laisse-la à l'emplacement local demandé. Commit ou ouvre une PR seulement quand l'utilisateur a concrètement demandé cette action externe.

## Garde-fous

- **Ne surajuste pas à une seule conversation.** Une préférence dite une fois puis contredite ailleurs est du bruit. Exige plusieurs occurrences avant de la codifier.
- **Ne fais pas le malin.** Reformuler le contenu d'autres skills, inventer des métaphores ou écrire une prose "poetique" pour un agent lecteur coûte sans benefice. Reste opérationnel.
- **Référence, n'intègre pas.** Les autres skills sur lesquelles l'utilisateur s'appuie doivent apparaître comme références de chemin, pas comme extraits collés. Même chose pour les documents de principes qu'il maintient ailleurs.
- **Garde les sections minimales.** Ajoute une section seulement si l'utilisateur a une règle spécifique et non par défaut à y mettre. "Communiquer clairement" n'est pas une section. "Paragraphes courts. Tableaux pour comparer des options. Puces seulement quand les éléments sont vraiment parallèles." en est une.
- **Nomme les conventions de façon générique.** Utilise "l'utilisateur" ou "l'humain" dans les imperatifs, pas le prénom de l'auteur.
- **Ne force pas la symétrie.** Si l'utilisateur n'a pas de règles de processus qui valent d'être écrites, saute entièrement la section Processus.

## Evaluation

Une skill `-mode` est une sortie subjective. Une boucle de benchmark n'est pas utile ici. Fais une vérification de ton avec l'utilisateur : est-ce que ça lui ressemble? Est-ce qu'il manque quelque chose? Puis livre.

Lance une boucle d'optimisation de description seulement si la précision de declenchement de la skill s'avere être un problème en pratique.

## Quand ne pas l'utiliser

- L'utilisateur veut une skill propre à une tâche (pas des conventions de travail) : utilise `skill-creator` quand disponible ou écris-la directement; aucune extraction requise.
- L'utilisateur veut capturer un flux de travail étroit (par exemple "how I write commit messages"). C'est une skill normale, pas une skill mode.

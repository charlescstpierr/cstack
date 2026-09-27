# Instantané de portée figée

Lis ce document à l'Étape 1 de [interrogate](../SKILL.md) quand la portée est le travail courant, une branche, une plage de commits ou une PR.

## Travail courant ou en cours

Fige une seule fois les SHA exacts de base et de `HEAD`. Capture `git diff <base-sha>...<head-sha>`, `git diff --cached` et `git diff` pour les changements commités, staged et unstaged suivis, puis liste les fichiers non suivis avec `git ls-files --others --exclude-standard` et instantane leur contenu avec des lectures natives. Ne lance jamais `git add`, `git stash`, `git checkout`, `git reset` ni une autre commande qui change le worktree. Enregistre l'heure de l'instantané; si le worktree change pendant sa lecture, indique que l'instantané de contenu peut ne pas être atomique.

## Branche, plage de commits ou PR

Fige une seule fois les SHA base et head résolus et relis seulement cette portée commit-à-commit. N'inclus pas silencieusement les changements sales du worktree.

## Emballage

Emballe la portée figée (ou l'instantané de contenu) plus seulement les fichiers de contexte environnants dont les reviewers ont besoin pour comprendre le code. Une comparaison à trois points est valide seulement pour les SHA de commits figés; elle ne prouve pas la couverture du travail staged, unstaged ou non suivi.

Le prompt de chaque reviewer porte l'instantané de portée figée, avec ses SHA base et head et l'indication d'inclusion ou non des fichiers sales du worktree.

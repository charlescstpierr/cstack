# Positionnement de cstack

cstack n'est pas le seul outil de réalisation disponible dans cette chaîne
d'outils. AZDone occupe un créneau voisin. Ce fichier fixe la frontière entre
les deux pour éviter que leurs périmètres se recouvrent au fil des versions.

## Les deux créneaux

### cstack — la voie Codex et la mécanique de livraison Git/GitHub

Travail de code sur Codex App et CLI, avec piles de PR, suivi de PR outillé et
orchestration multi-worktree.

Actifs exclusifs à cstack :

- `watch-pr` et `watch-pr --stack` : découverte des ancêtres et descendants
  ouverts d'une PR, relations head/base, rejet des relations ambiguës ou
  cycliques, identification par dépôt et nom de branche, vérification du SHA
  de tête réel.
- `orch` : orchestration multi-worktree avec verrou à marqueur d'acquisition
  unique.
- Les 23 principes en références internes.
- Les 23 guides d'exécution.
- `deslop`, `unslop` et `no-comments` : trois nettoyages, trois cibles.
- 19 rôles de sous-agents et 4 comités, configurables dans `.cstack/models.json`.

Ce que cstack ne couvre pas : une politique de confiance exécutoire, et tout
hôte autre que Codex.

### AZDone — la voie multi-hôtes et la confiance vérifiable

Claude Code, Cursor et Codex. Un objectif mène à un verdict prouvé sous une
politique d'autorité déclarée dans le dépôt utilisateur.

Actifs exclusifs à AZDone :

- `.azdone/trust.yaml` : matrice action par niveau, valeur `never` non
  contournable, liste toujours-pause réappliquée si elle est retirée.
- Un hook d'enforcement qui bloque les commandes shell que la politique refuse,
  sous les hôtes qui exposent des hooks.
- Un ledger append-only des runs, et la confiance gagnée par runs `verified`
  consécutifs.
- Les verdicts `verified | partial | blocked | failed`, chacun avec sa preuve et
  sa `next_safe_action`.
- Cartes, readiness et graphe de décisions.

Ce que AZDone ne couvre pas : les piles de PR outillées, et un catalogue de
principes.

## Règle de choix

Codex seul, avec une pile de PR à mener : cstack. Un autre hôte, ou le besoin de
borner ce que l'agent fait sans demander : AZDone.

## Règle de non-recouvrement

Pour les évolutions futures :

- Ce qui touche l'autorité et la confiance va dans AZDone.
- Ce qui touche la mécanique Git/GitHub outillée va dans cstack.

On ne duplique pas une capacité de l'autre créneau. On pointe vers lui. Une
demande qui semble exiger les deux est le signal d'un choix d'hôte à trancher
avant d'écrire du code, pas d'une fonctionnalité à porter.

## Cohabitation dans un même projet

Les deux peuvent être installés côte à côte :

- Les invocations restent distinctes : `$cstack:cstack` et `$cstack:architect`
  d'un côté, `/azd` et `/azdone:azd` de l'autre.
- Les états ne se touchent pas : `.cstack/` et `.azdone/` sont deux
  répertoires séparés, tous deux à exclure des commits.
- N'activez pas les deux modes dans la même tâche. Ils portent deux
  vocabulaires de verdicts et deux conventions de modèles ; les mélanger rend
  le résultat illisible.

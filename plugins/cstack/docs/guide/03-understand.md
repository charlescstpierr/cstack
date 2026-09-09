# Comprendre le code avant de le modifier

Une correction commence par un modèle du comportement actuel. cstack fournit quatre points d'entrée explicites pour lire le système, son historique et votre contexte récent.

## Tracer le comportement avec `$how`

```text
$how comment cette initialisation fonctionne-t-elle ? Montre le flux, les types et les propriétaires.
```

[`$how`](../../skills/how/SKILL.md) explique le flux d'exécution et les couches utiles. Il convient avant une modification ou une question de placement.

## Chercher les raisons avec `$why`

```text
$why pourquoi la limite de retry vaut-elle cinq ? La justification existe-t-elle encore ?
```

[`$why`](../../skills/why/SKILL.md) rassemble les éléments disponibles dans le dépôt et les connecteurs autorisés. Il distingue les faits des inférences et indique quand l'historique est absent.

## Construire une explication avec `$teach`

```text
$teach-moi comment cette PR change les retries et pourquoi elle corrige la cause.
```

[`$teach`](../../skills/teach/SKILL.md) combine le comportement et la motivation à un niveau lisible. Utilisez-le quand un résumé ne suffit pas.

## Reconstituer votre contexte avec `$recall`

```text
$recall mon travail sur l'export de la semaine dernière.
```

[`$recall`](../../skills/recall/SKILL.md) reconstruit le contexte récent à partir des traces disponibles. Il aide à reprendre un sujet, tandis que la reprise d'une tâche précise passe par le playbook de session.

## Reprendre un travail précédent

```text
$cstack reprends cette worktree. Lis les décisions et vérifie le point de reprise sans refaire le travail terminé.
```

Le [playbook de reprise de session](../../skills/cstack/playbooks/session-pickup.md) vérifie les affirmations héritées contre l'objectif original. Il conserve les preuves utiles et évite de réinventer l'analyse.

Suivant : [concevoir le changement](./04-design.md).

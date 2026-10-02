# Comprendre le code avant de le modifier

Une correction commence par un modèle du comportement actuel. cstack fournit quatre points d'entrée explicites pour lire le système, son historique et votre contexte récent.

## Tracer le comportement avec `$cstack:how`

```text
$cstack:how comment cette initialisation fonctionne-t-elle ? Montre le flux, les types et les propriétaires.
```

[`$cstack:how`](../../skills/how/SKILL.md) explique le flux d'exécution et les couches utiles. Il convient avant une modification ou une question de placement.

Par défaut, `how` découpe la question en angles distincts, normalement trois quand ils sont utiles, envoie au moins deux explorateurs en lecture seule quand l'exploration est déléguée, puis fait synthétiser une explication unique. Une cible unique suit la même règle si elle est déléguée ; elle reste une passe directe du parent seulement si la délégation est explicitement exclue ou réellement indisponible. Une demande qui interdit la délégation reste sur une passe directe.

## Chercher les raisons avec `$cstack:why`

```text
$cstack:why pourquoi la limite de retry vaut-elle cinq ? La justification existe-t-elle encore ?
```

[`$cstack:why`](../../skills/why/SKILL.md) rassemble les éléments disponibles dans le dépôt et les connecteurs autorisés. Il distingue les faits des inférences et indique quand l'historique est absent.

## Construire une explication avec `$cstack:teach`

```text
$cstack:teach comment cette PR change les retries et pourquoi elle corrige la cause.
```

[`$cstack:teach`](../../skills/teach/SKILL.md) combine le comportement et la motivation à un niveau lisible. Utilisez-le quand un résumé ne suffit pas.

## Reconstituer votre contexte avec `$cstack:recall`

```text
$cstack:recall mon travail sur l'export de la semaine dernière.
```

[`$cstack:recall`](../../skills/recall/SKILL.md) reconstruit le contexte récent à partir des traces disponibles. Il aide à reprendre un sujet, tandis que la reprise d'une tâche précise passe par le guide d'exécution de session. Il dresse d'abord un index des tâches (date, sujet), puis ne développe que celles qui servent votre demande.

Un passage placé entre `<private>` et `</private>` dans une conversation ou une note n'est jamais extrait : ni `recall`, ni `reflect`, ni `automate-me` ne le citent ou ne le résument.

## Reprendre un travail précédent

```text
$cstack:cstack reprends cette worktree. Lis les décisions et vérifie le point de reprise sans refaire le travail terminé.
```

Le [guide d'exécution de reprise de session](../../skills/cstack/playbooks/session-pickup.md) vérifie les affirmations héritées contre l'objectif original. Il conserve les preuves utiles et évite de réinventer l'analyse.

Suivant : [concevoir le changement](./04-design.md).

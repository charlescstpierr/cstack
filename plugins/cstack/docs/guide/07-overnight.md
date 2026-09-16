# Faire avancer une tâche pendant votre absence

Une tâche autonome doit avoir une condition d'arrêt, un périmètre et une trace lisible. Codex peut continuer une attente au premier plan quand l'exécution le permet. Il ne faut pas promettre qu'un agent local survivra à la fermeture de l'application.

## Le contrat d'une tâche autonome

Donnez :

- le résultat attendu et le test qui le prouve ;
- les chemins et systèmes autorisés ;
- les actions externes interdites ou explicitement permises ;
- la condition d'arrêt et la forme du rapport.

Pour les migrations ou tâches longues, utilisez [`$cstack:figure-it-out`](../../skills/figure-it-out/SKILL.md) et [`$cstack:show-me-your-work`](../../skills/show-me-your-work/SKILL.md). Le journal reste dans l'espace de travail afin d'être relu.

## Ce que fait la boucle

```text
$cstack:cstack continue jusqu'à ce que chaque fixture passe. N'envoie aucun message externe. Journalise les décisions et arrête-toi sur un blocage.
```

Le travail avance par unités vérifiables. `$cstack:swarm` peut répartir des tranches indépendantes, avec une vérification par tranche. Les erreurs, les permissions manquantes et les ambiguïtés matérielles deviennent des blocages explicites.

Une planification récurrente n'est utilisée que si un planificateur natif est disponible et demandé explicitement. cstack ne simule pas de webhook, de cron ou d'agent persistant.

## L'audit du matin

Relisez l'objectif, le journal, le diff et les commandes exécutées. Rejouez la vérification finale. Un rapport d'agent est un indice ; la preuve vient du fichier, du processus ou de la valeur observée.

## Quand la nuit contient une file

Pour plusieurs changements indépendants, isolez les worktrees et donnez à chaque item un propriétaire, une condition de fin et une limite. Ne faites pas écrire plusieurs agents dans le même état partagé. La fusion, la publication et les messages restent des décisions séparées.

Suivant : [piloter avec les principes](./08-principles.md).

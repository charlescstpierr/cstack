# Faire avancer une tâche pendant votre absence

Une tâche autonome doit avoir une condition d'arrêt, un périmètre et une trace lisible. Codex peut continuer une attente au premier plan quand l'exécution le permet. Il ne faut pas promettre qu'un agent local survivra à la fermeture de l'application.

## Le contrat d'une tâche autonome

Donnez :

- le résultat attendu et le test qui le prouve ;
- les chemins et systèmes autorisés ;
- les actions externes interdites ou explicitement permises ;
- la condition d'arrêt et la forme du rapport.

Pour les migrations ou tâches longues, utilisez [`$cstack:figure-it-out`](../../skills/figure-it-out/SKILL.md) et [`$cstack:show-me-your-work`](../../skills/show-me-your-work/SKILL.md). Le journal reste dans l'espace de travail afin d'être relu.

## Un Goal pour toute la livraison

Pour une implémentation multi-phase, le prompt proposé par le sélecteur cstack contient une demande explicite de Goal natif. Elle doit figurer dans le message réellement envoyé. Une invocation nue de `$cstack:cstack` ne l'active pas. Vous pouvez aussi écrire :

```text
$cstack:cstack ajoute cette fonctionnalité. Je demande un Goal natif global jusqu'à une PR testée et revue. Utilise les agents configurés.
```

Le coordinateur conserve le même objectif pendant l'exploration, l'implémentation, les tests, la revue et l'ouverture de PR. Il annonce les playbooks, les skills et les appels d'agents avec leur runtime, modèle et effort, puis actualise la todo. Une exploration déléguée utilise au moins deux explorateurs, normalement trois angles distincts, en vagues si nécessaire.

La PR prête pour revue est la fin par défaut. Une demande « local seulement » arrête plus tôt ; merge, installation et déploiement exigent une autorisation explicite. Les questions et petites modifications mécaniques suivent le parcours ordinaire. Sans outils Goal, cstack signale la limite et poursuit au premier plan sans annoncer un Goal actif.

La boucle fonctionne aussi en journée. Elle continue tant que le résultat convenu reste à atteindre et que la session le permet. Une pause demandée suspend le Goal ; un blocage réel ou une limite native est rapporté sans recréer d'objectif pour le contourner. Aucun budget n'est ajouté sans demande. Fermer l'application ne garantit pas la continuation.

## Ce que fait la boucle

```text
$cstack:cstack continue jusqu'à ce que chaque fixture passe. N'envoie aucun message externe. Journalise les décisions et arrête-toi sur un blocage.
```

Le travail avance par unités vérifiables. `$cstack:swarm` peut répartir des tranches indépendantes, avec une vérification par tranche. Pour une file de PR menée jusqu'au merge (Autopilot-full), des vérificateurs neufs lancent une ronde au head code-ready du propriétaire puis à chaque push qui change le patch ; seul un verdict propre sur le patch qui fusionne autorise le merge. Les erreurs, les permissions manquantes et les ambiguïtés matérielles deviennent des blocages explicites.

Une planification récurrente n'est utilisée que si un planificateur natif est disponible et demandé explicitement. cstack ne simule pas de webhook, de cron ou d'agent persistant.

## Passer d'Horizon à l'exécution

Pour un grand objectif qui traverse plusieurs phases ou sessions, commencez par la planification :

```text
$cstack:horizon planifie la migration progressive de notre moteur de recherche. Garde les artefacts locaux sous .cstack/horizon/recherche/.
```

Invoqué directement, Horizon s'arrête à son résultat de planification. Quand le handoff est prêt, demandez son exécution :

```text
$cstack:cstack exécute .cstack/horizon/recherche/spec.md avec le playbook orchestrate existant. Respecte le périmètre convenu. Ne crée aucun ticket distant, ne merge pas et ne déploie pas.
```

Le chemin général est `.cstack/horizon/<slug>/spec.md`. cstack conserve les identifiants, les dépendances et les critères d'acceptation des unités, puis sélectionne celles réellement prêtes. Une unité déjà revendiquée (`claimed`) ou terminée (`done`) n'est jamais relancée silencieusement. Si les sources importées ou les briefs dérivent, l'exécution se bloque au lieu de remplacer la définition et ses preuves.

Quand une demande `$cstack:cstack` autorise déjà l'implémentation et passe par Horizon, le coordinateur peut continuer avec ce handoff dans les limites de cette demande. Le handoff n'ajoute aucune permission de créer des tickets distants, de merger ou de déployer. Une petite fonctionnalité réalisable en une session suit le playbook cstack ordinaire, sans détour par Horizon. Le [playbook orchestrate](../../skills/cstack/playbooks/orchestrate.md) décrit la reprise et les vérifications.

## L'audit du matin

Relisez l'objectif, le journal, le diff et les commandes exécutées. Rejouez la vérification finale. Un rapport d'agent est un indice ; la preuve vient du fichier, du processus ou de la valeur observée.

## Quand la nuit contient une file

Pour plusieurs changements indépendants, isolez les worktrees et donnez à chaque item un propriétaire, une condition de fin et une limite. Ne faites pas écrire plusieurs agents dans le même état partagé. La fusion, la publication et les messages restent des décisions séparées.

Suivant : [piloter avec les principes](./08-principles.md).

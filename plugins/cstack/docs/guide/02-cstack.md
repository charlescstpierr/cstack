# Router le travail avec `$cstack:cstack`

`$cstack:cstack` est la porte d'entrée. Donnez un objectif, un périmètre et une condition de fin. Le routeur sélectionne le playbook le plus proche et appelle les compétences au moment utile.

## Ce qui arrive à votre demande

```text
$cstack:cstack les notifications sont écrites deux fois après un retry. Reproduis, corrige la cause, puis vérifie le résultat.
```

Le routeur identifie le type de travail, reprend les contraintes explicites et prépare une séquence contrôlable. S'il manque une décision que Codex ne peut pas déduire du dépôt, il passe par `clarify`. Si l'objectif dépasse une livraison simple et demande une carte de décisions sur plusieurs phases, il passe par Horizon. Quand le périmètre est clair, il choisit directement le playbook adapté.

Les playbooks vivent dans [le répertoire cstack](../../skills/cstack/playbooks/). Le routeur en liste 23.

| Playbook | Fichier | Usage |
| --- | --- | --- |
| Investigation | [investigation.md](../../skills/cstack/playbooks/investigation.md) | Explication, comparaison ou question de design en lecture seule. |
| Bug fix | [bug-fix.md](../../skills/cstack/playbooks/bug-fix.md) | Défaut à reproduire, diagnostiquer et corriger. |
| Perf issue | [perf-issue.md](../../skills/cstack/playbooks/perf-issue.md) | Un défaut de performance mesuré. |
| Hillclimb | [hillclimb.md](../../skills/cstack/playbooks/hillclimb.md) | Amélioration répétée d'une métrique vers une cible. |
| Runtime forensics | [runtime-forensics.md](../../skills/cstack/playbooks/runtime-forensics.md) | Diagnostic depuis un processus en cours. |
| Trace forensics | [trace-forensics.md](../../skills/cstack/playbooks/trace-forensics.md) | Diagnostic depuis un profil ou une trace. |
| Feature | [feature.md](../../skills/cstack/playbooks/feature.md) | Comportement nouveau ou modifié. |
| Refactoring | [refactoring.md](../../skills/cstack/playbooks/refactoring.md) | Changement de structure à comportement conservé. |
| Prototype | [prototype.md](../../skills/cstack/playbooks/prototype.md) | Expérience jetable qui tranche une question observable. |
| Visual parity | [visual-parity.md](../../skills/cstack/playbooks/visual-parity.md) | Comparaison d'interface au pixel. |
| Authoring a skill | [authoring-a-skill.md](../../skills/cstack/playbooks/authoring-a-skill.md) | Créer ou modifier un skill. |
| Eval | [eval.md](../../skills/cstack/playbooks/eval.md) | Mesurer l'effet d'un skill, d'un prompt ou d'une structure. |
| Babysit | [babysit.md](../../skills/cstack/playbooks/babysit.md) | Inspecter ou conduire une PR jusqu'à merge-ready. |
| Shipping | [shipping.md](../../skills/cstack/playbooks/shipping.md) | Atterrir ou livrer des PR vérifiées, après autorisation. |
| Autonomous run | [autonomous-run.md](../../skills/cstack/playbooks/autonomous-run.md) | Une tâche longue avec condition d'arrêt vérifiable. |
| Orchestrate | [orchestrate.md](../../skills/cstack/playbooks/orchestrate.md) | Programme durable, plusieurs propriétaires et PR. |
| Autopilot-full | [autopilot-full.md](../../skills/cstack/playbooks/autopilot-full.md) | File de PR indépendantes que les propriétaires peuvent fusionner. |
| Autopilot-stack | [autopilot-stack.md](../../skills/cstack/playbooks/autopilot-stack.md) | File livrée en pile linéaire que l'opérateur atterrit. |
| Session pickup | [session-pickup.md](../../skills/cstack/playbooks/session-pickup.md) | Reprendre un travail depuis l'état local, une branche ou le fil. |
| Pause safely | [pause-safely.md](../../skills/cstack/playbooks/pause-safely.md) | Laisser le travail local dans un état reprenable. |
| Multi-phase plan | [multi-phase-plan.md](../../skills/cstack/playbooks/multi-phase-plan.md) | Plan qui traverse des phases ou des PR. |
| Worktree cleanup | [worktree-cleanup.md](../../skills/cstack/playbooks/worktree-cleanup.md) | Nettoyer les worktrees temporaires après une livraison fusionnée. |
| Opening a PR | [opening-a-pr.md](../../skills/cstack/playbooks/opening-a-pr.md) | Créer une PR, seulement après autorisation. |

Pour une tâche simple et définie, Codex lit les fichiers concernés, fait le travail et vérifie le résultat directement. Les étapes d'exploration, de conception, de coordination, de clarification et de planification longue s'ajoutent selon la complexité réelle, pas seulement le nombre de fichiers. Les [principes](./08-principles.md) sont des références à consulter au moment utile, pas une liste à charger intégralement.

## Décrire l'objectif, pas la cérémonie

Préférez le résultat observable :

```text
$cstack:cstack comprends pourquoi cette entrée de cache survit à la déconnexion. Ne modifie pas le code.
```

Le périmètre en lecture seule est transmis au playbook d'investigation. Vous n'avez pas besoin d'énumérer `$cstack:how`, `$cstack:architect` et `$cstack:interrogate` si le flux standard les couvre déjà.

## Changer de tâche

Annoncez clairement un nouvel objectif :

```text
$cstack:cstack nouvelle tâche. Compare les deux formats de cache et recommande celui qui limite les invalidations.
```

La phrase évite de traiter une question indépendante comme l'étape suivante du travail en cours.

## Isoler le travail parallèle

Quand plusieurs tentatives écrivent des fichiers, demandez une worktree ou un répertoire propre par tentative. `$cstack:arena` compare des propositions concurrentes. `$cstack:swarm` répartit des tranches indépendantes et agrège leurs rapports.

## Continuer sans perdre la preuve

Pour une tâche longue, donnez la condition d'arrêt et demandez un journal de décisions :

```text
$cstack:cstack continue jusqu'à ce que la vérification signale zéro ancien appelant. Garde les décisions et les preuves dans le workspace.
```

Codex peut poursuivre avec des attentes au premier plan quand le runtime le permet. Il ne faut pas supposer qu'un agent local survivra à la fermeture de l'application. Pour une tâche qui mérite un dossier auditable, utilisez `$cstack:figure-it-out` et `$cstack:show-me-your-work`.

Suivant : [comprendre le code avant de le modifier](./03-understand.md).

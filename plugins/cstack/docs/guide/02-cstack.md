# Router le travail avec `$cstack:cstack`

`$cstack:cstack` est la porte d'entrée. Donnez un objectif, un périmètre et une condition de fin. Le routeur sélectionne le playbook le plus proche et appelle les compétences au moment utile.

## Ce qui arrive à votre demande

```text
$cstack:cstack les notifications sont écrites deux fois après un retry. Reproduis, corrige la cause, puis vérifie le résultat.
```

Le routeur identifie le type de travail, reprend les contraintes explicites et prépare une séquence contrôlable. Les playbooks vivent dans [le répertoire cstack](../../skills/cstack/playbooks/). Ils couvrent notamment les bugs, fonctionnalités, refactorings, performances, investigations, prototypes, vérifications et reprises de session.

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

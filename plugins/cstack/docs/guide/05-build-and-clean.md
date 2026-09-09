# Construire le changement et nettoyer le diff

Donnez au playbook le symptôme, le résultat attendu et la preuve. `$cstack` choisit ensuite le flux de bug, fonctionnalité, refactoring ou performance adapté.

```text
$cstack cette commande écrit deux lignes après un retry. Reproduis, corrige, puis vérifie.
```

Le [playbook de bug](../../skills/cstack/playbooks/bug-fix.md) reproduit avant la correction. Le [playbook de fonctionnalité](../../skills/cstack/playbooks/feature.md) fixe la forme des données. Le [playbook de refactoring](../../skills/cstack/playbooks/refactoring.md) capture le comportement avant de déplacer le code. Le [playbook de performance](../../skills/cstack/playbooks/perf-issue.md) mesure avant d'optimiser.

## Donner au playbook ce que vous savez

Indiquez le déclencheur, les invariants à conserver et la preuve attendue. Cette information permet au playbook de choisir une étape de reproduction, de caractérisation ou de mesure sans vous faire répéter la procédure.

## Écrire le test utile avec `$tdd`

```text
$tdd implémente ce changement avec un test qui échoue pour la bonne raison.
```

[`$tdd`](../../skills/tdd/SKILL.md) choisit le plus petit test qui prouve le comportement. Si le chemin est coûteux ou artificiel, le flux peut retenir une vérification exécutable plus proche de l'utilisateur.

## Laisser les règles TypeScript s'appliquer

[`typescript-best-practices`](../../skills/typescript-best-practices/SKILL.md) encadre les fichiers `.ts` et `.tsx`. Il complète les principes de types, de frontières et de variantes exhaustives sans ajouter de dépendance.

## Nettoyer avant le commit

Utilisez [`$unslop`](../../skills/unslop/SKILL.md) pour la prose. cstack privilégie la suppression de code mort, des chemins de compatibilité inutiles et des changements sans rapport.

Le plugin ne suppose pas la présence d'un outil externe de nettoyage. Si vous avez un linter ou un formatter du dépôt, exécutez celui qui fait partie du projet.

## Supprimer les commentaires qui cachent le comportement

Utilisez [`$no-comments`](../../skills/no-comments/SKILL.md) pour examiner les commentaires qui masquent une contrainte ou une décision. Conservez les liens et explications nécessaires quand le code ne peut pas exprimer la contrainte.

Suivant : [vérifier et livrer le résultat](./06-verify-and-ship.md).

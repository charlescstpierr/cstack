# Construire le changement et nettoyer le diff

Donnez au guide d'exécution le symptôme, le résultat attendu et la preuve. `$cstack:cstack` choisit ensuite le processus adapté : correction, fonctionnalité, refactorisation ou performance.

```text
$cstack:cstack cette commande écrit deux lignes après un retry. Reproduis, corrige, puis vérifie.
```

Le [guide d'exécution de bug](../../skills/cstack/playbooks/bug-fix.md) reproduit avant la correction. Le [guide d'exécution de fonctionnalité](../../skills/cstack/playbooks/feature.md) fixe la forme des données. Le [guide d'exécution de refactoring](../../skills/cstack/playbooks/refactoring.md) capture le comportement avant de restructurer le code. Le [guide d'exécution de performance](../../skills/cstack/playbooks/perf-issue.md) mesure avant d'optimiser.

## Donner au guide d'exécution ce que vous savez

Indiquez le déclencheur, les invariants à conserver et la preuve attendue. Cette information permet au guide d'exécution de choisir une étape de reproduction, de caractérisation ou de mesure sans vous faire répéter la procédure.

Quand le changement dépend de la version d'un framework ou d'une bibliothèque, cstack lit d'abord la version installée dans le lockfile ou le manifeste du projet, puis la documentation officielle de cette version. Il cite la page dans son rapport ou la PR, pas dans un commentaire de code, et utilise un outil de documentation connecté s'il en existe un, sans jamais l'installer.

## Écrire le test utile avec `$cstack:tdd`

```text
$cstack:tdd implémente ce changement avec un test qui échoue pour la bonne raison.
```

[`$cstack:tdd`](../../skills/tdd/SKILL.md) choisit le plus petit test qui prouve le comportement. Les bugs et fonctionnalités qui changent un comportement exigent le cycle rouge → vert. Un changement sans effet comportemental ou une impossibilité réelle suit une exception motivée avec une vérification exécutée ; sans preuve de l’un de ces parcours, la livraison reste bloquée.

## Laisser les règles TypeScript s'appliquer

[`$cstack:typescript-best-practices`](../../skills/typescript-best-practices/SKILL.md) encadre les fichiers `.ts` et `.tsx`. Il complète les principes de types, de frontières et de variantes exhaustives sans ajouter de dépendance.

## Nettoyer avant le commit

Trois nettoyages, trois cibles. [`$cstack:deslop`](../../skills/deslop/SKILL.md) retire le poids d'un diff de code avant chaque commit. [`$cstack:unslop`](../../skills/unslop/SKILL.md) nettoie la prose. [`$cstack:no-comments`](../../skills/no-comments/SKILL.md) confie les commentaires à un relecteur qui ne les a pas écrits.

cstack privilégie aussi la suppression de code mort, des chemins de compatibilité inutiles et des changements sans rapport. Le plugin ne suppose pas la présence d'un outil externe de nettoyage. Si vous avez un linter ou un formatter du dépôt, exécutez celui qui fait partie du projet.

## Supprimer les commentaires qui cachent le comportement

Utilisez `$cstack:no-comments` pour examiner les commentaires qui masquent une contrainte ou une décision. Conservez les liens et explications nécessaires quand le code ne peut pas exprimer la contrainte.

Suivant : [vérifier et livrer le résultat](./06-verify-and-ship.md).

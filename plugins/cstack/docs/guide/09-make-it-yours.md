# Adapter cstack à votre façon de travailler

Le routeur et les guides d'exécution sont génériques. Vos compétences locales peuvent exprimer les conventions du dépôt, à condition de rester explicites, vérifiables et dans le périmètre demandé.

## Générer un mode personnel avec `$cstack:automate-me`

```text
$cstack:automate-me
```

[`$cstack:automate-me`](../../skills/automate-me/SKILL.md) observe les habitudes récurrentes des traces disponibles, propose une compétence de mode et demande une validation avant de l'ajouter. Il ne modifie pas automatiquement la configuration globale.

## Capturer les leçons avec `$cstack:reflect`

```text
$cstack:reflect cette tâche a pris trop longtemps. Propose une règle qui évitera le même détour.
```

[`$cstack:reflect`](../../skills/reflect/SKILL.md) transforme les observations en propositions concrètes. Une leçon devient une règle seulement si elle change une décision future.

## Écrire une compétence ciblée

```text
$cstack:cstack écris une compétence pour vérifier les migrations de base de données de ce dépôt.
```

Suivez le [guide d'exécution d'auteur de compétence](../../skills/cstack/playbooks/authoring-a-skill.md). Vérifiez le frontmatter, les liens et un exemple réel. Une compétence locale ne doit pas être enregistrée comme compétence globale sans demande explicite.

## Écrire une documentation lisible

```text
$cstack:technical-writing relis cette documentation et rends les étapes exécutables.
```

[`$cstack:technical-writing`](../../skills/technical-writing/SKILL.md) choisit le type de document puis vérifie la clarté, les phrases et les liens.

## Tester une modification de compétence

```text
$cstack:cstack exécute le guide d'exécution eval sur cette modification de compétence. Compare les preuves sans révéler les variantes.
```

Le [guide d'exécution eval](../../skills/cstack/playbooks/eval.md) teste le comportement dans des répertoires isolés. Relisez les sorties et ne mélangez pas la modification de compétence avec une fonctionnalité produit.

Suivant : [recettes et pièges](./10-recipes-and-pitfalls.md).

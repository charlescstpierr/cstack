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

[`$cstack:reflect`](../../skills/reflect/SKILL.md) transforme les observations en propositions concrètes. Une leçon devient une règle seulement si elle change une décision future. Avant d'écrire, il vérifie le fichier d'instructions : la leçon va dans le fichier que Codex charge vraiment pour ce dossier, respecte le budget `project_doc_max_bytes`, remplace une règle qu'elle contredit au lieu de s'y ajouter, et n'est pas écrite si le code la montre déjà.

## Rendre impossibles les erreurs répétées avec `$cstack:correct`

```text
$cstack:correct les revues de PR relèvent encore des rollbacks incomplets dans install.sh.
```

[`$cstack:correct`](../../skills/correct/SKILL.md) lit les commentaires de revue, les commits de correction et les reverts, puis groupe les erreurs en classes. Une classe compte dès sa deuxième occurrence. Chaque classe est corrigée au niveau le plus haut qui fonctionne : architecture, types, lint, test, et une règle écrite seulement pour un jugement. Chaque nouveau contrôle doit échouer sur une vraie erreur passée. Là où `reflect` regarde une tâche, `correct` regarde ce qui revient d'une tâche à l'autre.

## Écrire une compétence ciblée

```text
$cstack:cstack écris une compétence pour vérifier les migrations de base de données de ce dépôt.
```

Suivez le [guide d'exécution d'auteur de compétence](../../skills/cstack/playbooks/authoring-a-skill.md). Vérifiez le frontmatter, les liens et un exemple réel. Une compétence locale ne doit pas être enregistrée comme compétence globale sans demande explicite.

Pour une règle de discipline, celle qu'un agent est tenté d'écarter sous pression, cstack observe d'abord un échec sans elle : un scénario réaliste qui cumule plusieurs pressions et impose un choix, lancé dans un sous-agent, avec les excuses notées mot pour mot sous `.cstack/`. La règle répond ensuite à ces excuses ; voir [Tester une règle sous pression](../../skills/cstack/references/rule-pressure-tests.md).

## Écrire une documentation lisible

```text
$cstack:technical-writing relis cette documentation et rends les étapes exécutables.
```

[`$cstack:technical-writing`](../../skills/technical-writing/SKILL.md) choisit le type de document puis vérifie la clarté, les phrases et les liens.

## Tester une modification de compétence

```text
$cstack:cstack exécute le guide d'exécution eval sur cette modification de compétence. Compare les preuves sans révéler les variantes.
```

Le [guide d'exécution eval](../../skills/cstack/playbooks/eval.md) teste le comportement dans des répertoires isolés. Relisez les sorties et ne mélangez pas la modification de compétence avec une fonctionnalité produit. Une règle se compare à la même compétence sans elle, et une règle sans échec de référence observé n'est pas promue.

Suivant : [recettes et pièges](./10-recipes-and-pitfalls.md).

# Configurer cstack

cstack est un plugin Codex pour organiser un travail de code autour d'un objectif vérifiable. Le cœur fonctionne avec les outils natifs de Codex et des sous-agents natifs. Il n'ajoute pas de moteur d'orchestration séparé.

## Installer le plugin

Depuis Codex CLI, ajoutez le marché puis le plugin :

```sh
codex plugin marketplace add charlescstpierr/cstack
codex plugin add cstack@cstack
```

Pour un checkout local, remplacez la première ligne par `codex plugin marketplace add /chemin/absolu/vers/cstack`. Ouvrez une nouvelle tâche dans Codex App ou une nouvelle session CLI après l'installation. Après installation, invoquez explicitement :

```text
$cstack
```

L'activation est limitée à cette tâche. Une installation ne rend pas les instructions actives dans les conversations ordinaires.

Le contrat d'exécution partagé décrit les outils, les permissions et l'état local : [runtime Codex](../../skills/cstack/references/codex-runtime.md).

## Configurer cstack

Pour inspecter ou préparer la configuration locale, invoquez [`$setup-cstack`](../../skills/setup-cstack/SKILL.md) :

```text
$setup-cstack
```

Le setup prépare seulement ce qui est nécessaire au workspace. Les sous-agents héritent du modèle de la session, sauf choix explicite disponible dans votre environnement. Aucun nom de modèle n'est imposé par le plugin.

Le setup ne promet pas de planification persistante, de messages externes, de PR, de merge ou de déploiement. Ces opérations restent conditionnées par les outils présents et votre autorisation.

## Accepter la vérification du projet, ou non

Si le projet n'a pas encore de moyen fiable de vérifier le comportement réel, utilisez [`$create-verification-skill`](../../skills/create-verification-skill/SKILL.md). Cette compétence produit des instructions locales pour lancer, piloter et inspecter l'application. Elle est facultative et reste limitée au dépôt courant.

## Lancer une première tâche

Décrivez le résultat et la preuve attendue :

```text
$cstack ajoute une option --json à cette commande. La sortie texte reste identique. Vérifie les deux formats.
```

Le routeur choisit le playbook adapté, appelle les compétences nécessaires et garde les étapes vérifiables visibles. Vous pouvez ensuite préciser une contrainte ou corriger le cap dans la même tâche.

Suivant : [router le travail avec `$cstack`](./02-cstack.md).

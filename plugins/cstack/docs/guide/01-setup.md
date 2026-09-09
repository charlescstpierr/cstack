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
$cstack:cstack
```

L'activation est limitée à cette tâche. Une installation ne rend pas les instructions actives dans les conversations ordinaires.

Le contrat d'exécution partagé décrit les outils, les permissions et l'état local : [runtime Codex](../../skills/cstack/references/codex-runtime.md).

## Configurer cstack

Pour inspecter ou préparer la configuration locale, invoquez [`$cstack:setup-cstack`](../../skills/setup-cstack/SKILL.md) :

```text
$cstack:setup-cstack
```

Le setup affiche les réglages existants et ces recommandations, avec leur disponibilité vérifiée dans le catalogue courant :

| Travail | Modèle | Effort |
| --- | --- | --- |
| Exploration | `gpt-5.6-luna` | `max` |
| Petites modifications | `gpt-5.6-luna` | `max` |
| Développement | `gpt-6-astra` | `low` |
| Débogage difficile | `gpt-6-astra` | `medium` |
| Revue de code | `gpt-6-astra` | `low` |
| Architecture complexe | `gpt-6-astra` | `xhigh` |
| Documentation | `gpt-5.6-luna` | `max` |

Le setup vérifie aussi que l'outil de délégation peut transmettre le modèle et l'effort. Une paire présente dans le catalogue mais impossible à transmettre est signalée avant tout choix ; utilisez alors l'héritage ou une sélection supportée.

Choisissez d'accepter les recommandations disponibles, de personnaliser les rôles, d'hériter de la session ou d'annuler. Seuls les rôles sélectionnés changent ; annuler ne crée ni ne modifie de fichier. Sans choix, les sous-agents héritent du modèle et de l'effort de la session. Un cache ancien ne prouve pas qu'un modèle est disponible.

Les choix sont enregistrés dans `.cstack/models.json` sous forme d'objets `model` et `reasoning_effort`. Les anciennes chaînes de modèle et les listes de panels restent compatibles. Un ancien modèle sans effort conserve les règles d'effort de l'hôte. Les rôles absents `simple edits` et `documentation` reprennent respectivement `feature, refactoring` et `judgment and prose`.

La configuration concerne les délégations suivantes, pas le modèle de la session principale. Elle ne nécessite ni clé API ni changement global. Si l'outil natif ne permet pas de transmettre l'effort choisi, cstack signale cette limite et demande un choix supporté ou l'héritage. Il ne remplace pas le réglage par une instruction dans le prompt.

Le setup ne promet pas de planification persistante, de messages externes, de PR, de merge ou de déploiement. Ces opérations restent conditionnées par les outils présents et votre autorisation.

## Accepter la vérification du projet, ou non

Si le projet n'a pas encore de moyen fiable de vérifier le comportement réel, utilisez [`$cstack:create-verification-skill`](../../skills/create-verification-skill/SKILL.md). Cette compétence produit des instructions locales pour lancer, piloter et inspecter l'application. Elle est facultative et reste limitée au dépôt courant.

## Lancer une première tâche

Décrivez le résultat et la preuve attendue :

```text
$cstack:cstack ajoute une option --json à cette commande. La sortie texte reste identique. Vérifie les deux formats.
```

Le routeur choisit le playbook adapté, appelle les compétences nécessaires et garde les étapes vérifiables visibles. Vous pouvez ensuite préciser une contrainte ou corriger le cap dans la même tâche.

Suivant : [router le travail avec `$cstack:cstack`](./02-cstack.md).

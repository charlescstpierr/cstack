# Configurer cstack

cstack est un plugin Codex pour organiser un travail de code autour d'un objectif vérifiable. Le cœur fonctionne avec les outils natifs de Codex et des sous-agents natifs. Il n'ajoute pas de moteur d'orchestration séparé.

## Installer le plugin

Depuis Codex CLI, ajoutez le marché puis le plugin :

```sh
codex plugin marketplace add charlescstpierr/cstack
codex plugin add cstack@cstack
```

Pour une copie locale, remplacez la première ligne par `codex plugin marketplace add /chemin/absolu/vers/cstack`. Ouvrez une nouvelle tâche dans Codex App ou une nouvelle session CLI après l'installation. Après installation, invoquez explicitement :

```text
$cstack:cstack
```

L'activation est limitée à cette tâche. Une installation ne rend pas les instructions actives dans les conversations ordinaires.

Le contrat d'exécution partagé décrit les outils, les permissions et l'état local : [exécution Codex](../../skills/cstack/references/codex-runtime.md).

## Configurer cstack

Pour inspecter ou préparer la configuration locale, invoquez [`$cstack:setup-cstack`](../../skills/setup-cstack/SKILL.md) :

```text
$cstack:setup-cstack
```

La configuration affiche les réglages existants et ces recommandations, avec leur disponibilité vérifiée dans le catalogue courant :

| Travail | Modèle | Effort |
| --- | --- | --- |
| Exploration | `gpt-5.6-luna` | `max` |
| Petites modifications | `gpt-5.6-luna` | `max` |
| Développement | `gpt-6-astra` | `low` |
| Revue de code | `gpt-6-astra` | `low` |
| Architecture complexe | `gpt-6-astra` | `xhigh` |
| Documentation | `gpt-5.6-luna` | `max` |

La configuration vérifie aussi que l'outil de délégation peut transmettre le modèle et l'effort. Une paire présente dans le catalogue mais impossible à transmettre est signalée avant tout choix ; utilisez alors l'héritage ou une sélection supportée.

Choisissez d'accepter les recommandations disponibles, de personnaliser les rôles, d'hériter de la session ou d'annuler. Seuls les rôles sélectionnés changent ; annuler ne crée ni ne modifie de fichier. Sans choix, les sous-agents héritent du modèle et de l'effort de la session. Un cache ancien ne prouve pas qu'un modèle est disponible.

Les choix sont enregistrés dans `.cstack/models.json` sous forme d'objets `model` et `reasoning_effort`. Les anciennes chaînes de modèle et les listes de comités restent compatibles. Un ancien modèle sans effort conserve les règles d'effort de l'hôte. Les rôles absents `simple edits` et `documentation` reprennent respectivement `feature, refactoring` et `judgment and prose`.

La configuration concerne les délégations suivantes, pas le modèle de la session principale. Elle ne nécessite ni clé API ni changement global. Si l'outil natif ne permet pas de transmettre l'effort choisi, cstack signale cette limite et demande un choix supporté ou l'héritage. Il ne remplace pas le réglage par une instruction dans l’invite.

La configuration ne promet pas de planification persistante, de messages externes, de PR, de fusion ou de déploiement. Ces opérations restent conditionnées par les outils présents et votre autorisation.

## Préparer les instructions du projet

La configuration propose aussi un aperçu des fichiers du projet avant application. `AGENTS.md` reçoit un bloc cstack délimité, qui renvoie au guide `docs/agents/cstack.md`. Le texte autour de ce bloc reste intact. Si `CLAUDE.md` existe, son contenu reste intact ; les conventions communes peuvent être référencées sans copie. Aucune règle globale n'est écrite et la présence du bloc n'active pas cstack.

Pour Horizon, la configuration reprend le document de suivi `docs/agents/issue-tracker.md` s'il existe, ou présente le choix entre les fichiers locaux et GitHub. Un choix GitHub enregistre le dépôt ciblé sans créer d'issue, de label ou de dépendance distante. Les termes et ADRs suivent les conventions du projet ; la configuration ne crée pas de glossaire vide.

L'aperçu indique les rôles réutilisés et la règle de nombre d'agents : `clarify` et `domain` n'en ajoutent aucun par défaut ; l'audit d'architecture utilise au plus un explorateur initial ; Horizon utilise un enfant par recherche indépendante prête, en vagues si nécessaire. Un besoin de synthèse ou de conception complexe conserve son rôle configuré. Le modèle de la session principale reste inchangé.

Une demande de configuration des modèles seulement conserve ce périmètre. Une demande d'aperçu, d'annulation, de lecture seule ou en mode Plan ne modifie pas les fichiers du projet.

## Accepter la vérification du projet, ou non

Si le projet n'a pas encore de moyen fiable de vérifier le comportement réel, utilisez [`$cstack:create-verification-skill`](../../skills/create-verification-skill/SKILL.md). Cette compétence produit des instructions locales pour lancer, piloter et inspecter l'application. Elle est facultative et reste limitée au dépôt courant.

## Lancer une première tâche

Décrivez le résultat et la preuve attendue :

```text
$cstack:cstack ajoute une option --json à cette commande. La sortie texte reste identique. Vérifie les deux formats.
```

Le routeur choisit le guide d'exécution adapté, appelle les compétences nécessaires et garde les étapes vérifiables visibles. Vous pouvez ensuite préciser une contrainte ou corriger le cap dans la même tâche.

Suivant : [router le travail avec `$cstack:cstack`](./02-cstack.md).

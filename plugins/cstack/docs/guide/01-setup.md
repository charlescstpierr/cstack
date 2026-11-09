# Configurer cstack

Dans T3 avec coordinateur Codex, après invocation explicite de cstack, suivre le [contrat T3](../../skills/cstack/references/runtime/t3.md). Une position T3 est non portable, les CLI y sont bloqués en V1, et les checkouts appartiennent à l’hôte. Le support du plugin installé reste à vérifier dans la session réelle.


cstack est un plugin Codex pour organiser un travail de code autour d'un objectif vérifiable. Le cœur fonctionne avec les outils natifs de Codex et des sous-agents natifs, ou des workers CLI explicitement sélectionnés. Il n'ajoute pas de moteur d'orchestration séparé.

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

## Mettre à jour le plugin

Pour une installation depuis le dépôt GitHub configuré :

```sh
codex plugin marketplace upgrade cstack
codex plugin add cstack@cstack
```

Ouvrez une nouvelle conversation App ou une nouvelle session CLI. Une conversation déjà ouverte ne prouve pas le chargement des nouveaux fichiers.

## Configurer cstack

Pour inspecter ou préparer la configuration locale, invoquez [`$cstack:setup-cstack`](../../skills/setup-cstack/SKILL.md) :

```text
$cstack:setup-cstack
```

Le setup inspecte d’abord les CLI présents sur la machine, leurs versions et leurs capacités. Il consulte leur statut de connexion officiel quand il est disponible, sans lire les credentials ni lancer de génération. Il compare cet inventaire aux rôles du projet pour proposer de conserver, ajouter ou remplacer les choix concernés. Une connexion inconnue ou un CLI absent reste signalé.

Pour les sous-agents natifs, la configuration affiche d'abord tous les rôles et positions de panel avec ces recommandations, dont la disponibilité est vérifiée dans le catalogue courant. Elle montre ensuite les autres modèles disponibles et la configuration actuelle :

| Travail | Modèle | Effort |
| --- | --- | --- |
| Exploration | `gpt-5.6-luna` | `max` |
| Petites modifications | `gpt-5.6-luna` | `max` |
| Développement | `gpt-6-astra` | `low` |
| Débogage difficile | `gpt-6-astra` | `medium` |
| Revue de code | `gpt-6-astra` | `low` |
| Architecture complexe | `gpt-6-astra` | `xhigh` |
| Documentation | `gpt-5.6-luna` | `max` |

La configuration vérifie aussi que l'outil de délégation peut transmettre le modèle et l'effort. Une paire présente dans le catalogue mais impossible à transmettre est signalée avant tout choix ; utilisez alors l'héritage ou une sélection supportée.

Le setup demande d'abord un budget de raisonnement (illimité, large, moyen ou réduit) qui plafonne l'effort de chaque rôle à modèle explicite selon le catalogue courant. Choisissez ensuite d'accepter toutes les recommandations disponibles, certains groupes, une personnalisation par rôle ou position de panel, de conserver la configuration actuelle, d'hériter pour certains rôles ou d'annuler. Seuls les rôles sélectionnés changent ; annuler ne crée ni ne modifie de fichier. Un rôle sans choix sauvegardé hérite du modèle et de l'effort de la session, mais le setup présente les modèles disponibles avant cet état courant. Un cache ancien ne prouve pas qu'un modèle est disponible.

Les choix natifs sont enregistrés dans `.cstack/models.json` sous forme d'objets `model` et `reasoning_effort`. Les workers externes ajoutent `runtime` ; voir le [guide Codex et Claude](./11-cli-workers.md). Les anciennes chaînes de modèle et les listes de comités restent compatibles. Un ancien modèle sans effort conserve les règles d'effort de l'hôte. Les rôles absents `simple edits` et `documentation` reprennent respectivement `feature, refactoring` et `judgment and prose`.

La configuration concerne les délégations suivantes, pas le modèle de la session principale. Elle ne nécessite ni clé API ni changement global. Si l'outil natif ne permet pas de transmettre l'effort choisi, cstack signale cette limite et demande un choix supporté ou l'héritage. Il ne remplace pas le réglage par une instruction dans l’invite.

La configuration ne promet pas de planification persistante, de messages externes, de PR, de fusion ou de déploiement. Ces opérations restent conditionnées par les outils présents et votre autorisation.

## Préparer les instructions du projet

La configuration propose aussi un aperçu des fichiers du projet avant application. `AGENTS.md` reçoit un bloc cstack délimité, qui charge le guide `docs/agents/cstack.md` comme instructions seulement pendant une tâche où vous invoquez `$cstack:*`. Si `CLAUDE.md` existe, la même limite s'applique à son utilisation comme instructions. Une tâche ordinaire peut toujours lire ou modifier ces fichiers quand vous le demandez. Le texte autour du bloc et le contenu de `CLAUDE.md` restent intacts. Aucune règle globale n'est écrite et la présence du bloc n'active pas cstack. Après une invocation explicite de `$cstack:cstack`, le bloc garde la conversation en mode cstack jusqu'à « arrête cstack » et demande de déléguer le travail indépendant. La configuration propose aussi trois agents natifs du projet dans `.codex/agents/` : `cstack-explorer` (lecture seule), `cstack-worker` (implémentation avec TDD) et `cstack-reviewer` (revue indépendante, lecture seule). Ils reprennent les modèles et efforts choisis pour leurs rôles, et `models.py apply` les tient à jour ; cstack les lance par leur nom. Un rôle confié à un CLI comme Claude Code n'a pas d'agent natif. Relancer la configuration sans l'option garde les agents existants ; `native_agents: false` supprime ceux qu'elle gère. Un agent de même nom écrit à la main, sans la ligne `# cstack:managed`, n'est jamais remplacé. Après une modification de `AGENTS.md`, ouvrez une nouvelle conversation App ou une nouvelle session CLI pour charger le nouveau bloc. Les choix de `.cstack/models.json` s'appliquent sans redémarrage aux rôles résolus après leur écriture; un délégué déjà lancé garde sa sélection.

Pour Horizon, la configuration reprend le document de suivi `docs/agents/issue-tracker.md` s'il existe, ou présente le choix entre les fichiers locaux et GitHub. Un choix GitHub enregistre le dépôt ciblé sans créer d'issue, de label ou de dépendance distante. Les termes et ADRs suivent les conventions du projet ; la configuration ne crée pas de glossaire vide.

L'aperçu indique les rôles et le nombre d'agents. `clarify` et `domain` n'en ajoutent aucun par défaut. L'audit peut établir les faits dans le parent ; s'il délègue, il utilise au moins deux explorateurs, normalement trois angles utiles. Horizon conserve un handle et un artefact par angle de recherche et lance les vagues selon la capacité. Les synthèses gardent leur rôle configuré. Le modèle de la session principale reste inchangé.

Une demande de configuration des modèles seulement conserve ce périmètre. Une demande d'aperçu, d'annulation, de lecture seule ou en mode Plan ne modifie pas les fichiers du projet.

## Accepter la vérification du projet, ou non

Si le projet n'a pas encore de moyen fiable de vérifier le comportement réel, utilisez [`$cstack:create-verification-skill`](../../skills/create-verification-skill/SKILL.md). Cette compétence produit des instructions locales pour lancer, piloter et inspecter l'application. Elle est facultative et reste limitée au dépôt courant.

## Rappel du mode sur les longues sessions (une fois)

Comme pstack dans Cursor, cstack rappelle son mode à chaque message et après chaque résumé de conversation, mais seulement dans les conversations où vous avez tapé `$cstack:cstack`. Codex exige d'approuver une fois les hooks d'un plugin tiers : dans Codex CLI, lancez `/hooks` et approuvez les deux hooks cstack (`UserPromptSubmit` et `SessionStart`). Faites-le avant votre première tâche cstack : l'approbation vaut pour tous vos projets, et un `$cstack:cstack` tapé avant elle n'active pas le rappel ; retapez-le dans la conversation après avoir approuvé. L'App Codex ne propose pas encore cette approbation ; sans elle, cstack fonctionne sans rappel. Dites « arrête cstack » pour couper le rappel dans une conversation. Après un résumé, le rappel renvoie aussi au point de reprise de la tâche active sous `.cstack/` : cstack nomme ce chemin dans la conversation pour que le résumé le garde.

## Lancer une première tâche

Décrivez le résultat et la preuve attendue :

```text
$cstack:cstack ajoute une option --json à cette commande. La sortie texte reste identique. Vérifie les deux formats.
```

Le routeur choisit le guide d'exécution adapté, appelle les compétences nécessaires et garde les étapes vérifiables visibles. Vous pouvez ensuite préciser une contrainte ou corriger le cap dans la même tâche.

Suivant : [router le travail avec `$cstack:cstack`](./02-cstack.md).

# cstack

Les workflows de [pstack](https://github.com/cursor/plugins/tree/27e2a62ff94f9af4b5e68435e41cdceacadb840c/pstack), adaptés à **Codex App et CLI**. Investigation, architecture, implémentation, revue et vérification, avec les sous-agents natifs de Codex.

cstack s'active dans une tâche avec `$cstack:cstack`. L'installation seule ne modifie pas le comportement de Codex dans vos projets. Aucun runtime d'orchestration supplémentaire n'est nécessaire.

## Installation depuis le dépôt privé

Le compte GitHub utilisé doit avoir accès à `charlescstpierr/cstack`. Dans un terminal avec Codex CLI et l'authentification Git configurée :

```sh
codex plugin marketplace add charlescstpierr/cstack
codex plugin add cstack@cstack
```

Ouvrez une **nouvelle tâche** dans Codex App ou une nouvelle session CLI après l'installation. Le CLI doit utiliser le même profil Codex que l'application pour partager cette installation. Dans une autre installation ou sur une autre machine, ajoutez le dépôt depuis les sources de plugins disponibles et authentifiez l'accès au dépôt privé.

Pour tester un checkout local :

```sh
codex plugin marketplace add /chemin/absolu/vers/cstack
codex plugin add cstack@cstack
```

Le catalogue contient un seul plugin, `cstack`. Choisissez son skill dans le sélecteur si un autre plugin utilise le même nom de skill. Retirer le plugin n'efface pas les fichiers de travail `.cstack/` des projets.

## Utilisation

Dans le sélecteur App ou CLI interactif, tapez `$cstack` puis choisissez le skill **cstack**. Si vous saisissez une commande en texte brut, notamment avec `codex exec`, utilisez son nom complet `$cstack:cstack`. Les autres skills suivent le même format, par exemple `$cstack:architect`.

```text
$cstack:cstack Corrige ce bug et vérifie le résultat.
$cstack:cstack Examine cette modification avant livraison.
$cstack:architect Propose la structure de cette fonctionnalité.
$cstack:interrogate Fais une revue contradictoire de ce diff.
$cstack:setup-cstack
```

Le mode reste actif dans la tâche jusqu'à une demande de désactivation, par exemple « arrête cstack ». Les skills spécialisés restent utilisables à la demande. Le mode Plan, les instructions du projet et les autorisations Codex restent prioritaires.

Quatre compétences de préparation sont facultatives : `$cstack:clarify` pour clarifier les exigences, `$cstack:domain` pour le vocabulaire et les décisions du projet, `$cstack:horizon` pour cartographier un objectif incertain sur plusieurs sessions, et `$cstack:audit-architecture` pour repérer des simplifications dans le code existant. Elles ne s'ajoutent pas automatiquement aux corrections et aux développements ordinaires. Voir le [guide de conception](plugins/cstack/docs/guide/04-design.md).

Exemple sans interface interactive :

```sh
codex exec '$cstack:cstack Examine cette modification sans changer les fichiers.'
```

Les sous-agents héritent du modèle de la session par défaut. `$cstack:setup-cstack` affiche sept recommandations de modèle et d'effort à accepter, personnaliser ou remplacer par l'héritage ; vous pouvez aussi annuler. Les choix existants restent préservés sauf sélection explicite. Les paires sont vérifiées dans le catalogue courant et enregistrées dans `.cstack/models.json`, sans modifier la session principale ni la configuration globale. Voir le [tableau de recommandations](plugins/cstack/docs/guide/01-setup.md#configurer-cstack). Un choix indisponible ou un effort non configurable par l'hôte est signalé, sans substitution silencieuse.

Le setup peut aussi préparer les conventions du projet : un bloc cstack dans `AGENTS.md`, un guide local et le suivi de tickets choisi. Il montre les changements avant application et conserve les instructions extérieures au bloc. Il ne modifie pas `CLAUDE.md`, n'active pas cstack automatiquement et ne crée aucun ticket distant. La configuration des modèles seule reste disponible.

## Prérequis et limites

- Le travail de code courant utilise les outils disponibles dans Codex. Les sous-agents sont utilisés lorsqu'ils sont disponibles ; sinon, les étapes s'exécutent séquentiellement et cette limite est indiquée.
- Les assistants de suivi de PR et d'orchestration utilisent Bun et les dépendances verrouillées fournies avec le portage. Leur installation nécessite un accès au registre de paquets ou un cache Bun déjà rempli. Le lanceur utilise bash et Python 3. Les opérations GitHub nécessitent `git` et `gh` authentifié.
- Chaque lancement copie les scripts dans un dossier temporaire distinct sous `.cstack/tools/`, installe les dépendances verrouillées et nettoie cette copie après exécution. Aucun exécutable déjà présent dans le projet n'est réutilisé. Le cache du plugin installé reste intact. Les checkpoints et choix de modèles restent locaux et doivent être exclus des commits.
- Les outils de navigateur, les connecteurs et les tâches planifiées sont facultatifs. Une capacité absente est signalée ; aucun résultat de test ni travail en arrière-plan n'est simulé.
- Les webhooks Grok Bot et les automatisations événementielles Benny de Cursor ne disposent pas d'un équivalent intégré. Leurs limites sont conservées dans le [guide de portage](docs/PORTING.md).

Une demande de revue ou l'activation du mode n'autorise pas à envoyer un message, ouvrir une PR, fusionner ou publier. cstack suit l'autorisation donnée pour la tâche concrète.

## Développement

```sh
bun scripts/validate.ts
python3 -m unittest discover -s tests -p 'test_*.py'
bun test tests
cd plugins/cstack/skills/cstack/scripts
bun install --frozen-lockfile
bun run test
bun run typecheck
```

Depuis la racine, vérifier aussi les scripts de validation TypeScript :

```sh
plugins/cstack/skills/cstack/scripts/node_modules/.bin/tsc -p tsconfig.json
```

Le [guide](plugins/cstack/docs/guide/README.md) détaille les workflows. Le [rapport de vérification](docs/VERIFICATION.md) distingue les tests effectués des limites de validation. `UPSTREAM.json` identifie les fichiers source et `PORTING.json` leur destination dans cstack.

## Licence

MIT, avec conservation du copyright de Lauren Tan. Voir [LICENSE](plugins/cstack/LICENSE) et [NOTICE](plugins/cstack/NOTICE.md). Ce portage indépendant n'est pas un produit officiel de Cursor ou d'OpenAI.

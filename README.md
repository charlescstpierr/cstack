# cstack

Les processus de [pstack](https://github.com/cursor/plugins/tree/889ec4b68fa5aab0e867dad71ec3fdf386ae48f3/pstack), adaptés à **Codex App et CLI**. Investigation, architecture, implémentation, revue et vérification, avec les sous-agents natifs de Codex. Version amont épinglée `0.15.2`, commit `889ec4b68fa5aab0e867dad71ec3fdf386ae48f3`.

cstack s'active dans une tâche avec `$cstack:cstack`. L'installation seule ne modifie pas le comportement de Codex dans vos projets. Aucun moteur d'orchestration supplémentaire n'est nécessaire.

La documentation et les messages sont en français ; les noms de commandes et de compétences, chemins, clés de configuration et licences originales sont conservés pour compatibilité.

## Installation depuis le dépôt privé

Le compte GitHub utilisé doit avoir accès à `charlescstpierr/cstack`. Dans un terminal avec Codex CLI et l'authentification Git configurée :

```sh
codex plugin marketplace add charlescstpierr/cstack
codex plugin add cstack@cstack
```

Ouvrez une **nouvelle tâche** dans Codex App ou une nouvelle session CLI après l'installation. Le CLI doit utiliser le même profil Codex que l'application pour partager cette installation. Dans une autre installation ou sur une autre machine, ajoutez le dépôt depuis les sources de plugins disponibles et authentifiez l'accès au dépôt privé.

Pour tester une copie locale :

```sh
codex plugin marketplace add /chemin/absolu/vers/cstack
codex plugin add cstack@cstack
```

Le catalogue contient un seul plugin, `cstack`. Choisissez sa compétence dans le sélecteur si un autre plugin utilise le même nom de compétence. Un autre portage de pstack crée une collision. `$cstack:architect` désigne ce plugin. Un `$architect` nu ne le distingue pas. Retirer le plugin n'efface pas les fichiers de travail `.cstack/` des projets.

## Utilisation

Dans le sélecteur App ou CLI interactif, tapez `$cstack` puis choisissez la compétence **cstack**. Si vous saisissez une commande en texte brut, notamment avec `codex exec`, utilisez son nom complet `$cstack:cstack`. Les autres compétences suivent le même format, par exemple `$cstack:architect`.

```text
$cstack:cstack Corrige ce bug et vérifie le résultat.
$cstack:cstack Examine cette modification avant livraison.
$cstack:architect Propose la structure de cette fonctionnalité.
$cstack:interrogate Fais une revue contradictoire de ce diff.
$cstack:setup-cstack
```

Le mode reste actif dans la tâche jusqu'à une demande de désactivation, par exemple « arrête cstack ». Les compétences spécialisées restent utilisables à la demande. Le mode Plan, les instructions du projet et les autorisations Codex restent prioritaires.

Le catalogue contient 29 compétences. Les 23 principes sont des [références internes](plugins/cstack/docs/guide/08-principles.md), consultées seulement lorsqu'elles sont utiles au travail ou que vous nommez un principe. Leurs anciennes commandes individuelles disparaissent du sélecteur. Par exemple, utilisez `$cstack:cstack applique le principe « Discipline aux frontières » à cette validation`. Les tâches simples s'exécutent directement ; une exploration, une comparaison d'architectures ou des sous-agents s'ajoutent quand le travail le justifie.

Trois nettoyages, trois cibles. `$cstack:deslop` retire le poids d'un diff de code avant commit. `$cstack:unslop` nettoie la prose. `$cstack:no-comments` confie les commentaires à un relecteur qui ne les a pas écrits.

`$cstack:cstack` peut appeler les préparations quand la demande l'exige : `clarify` pour une ambiguïté réelle, `horizon` pour un objectif vraiment long ou multi-phase, `domain` pour le vocabulaire et les décisions du projet, et `audit-architecture` pour repérer des simplifications dans le code existant. Une tâche claire part directement vers le guide d'exécution adapté avec sa revue et sa vérification ; plusieurs fichiers ne suffisent pas à déclencher Horizon. Voir le [guide de conception](plugins/cstack/docs/guide/04-design.md).

Exemple sans interface interactive :

```sh
codex exec '$cstack:cstack Examine cette modification sans changer les fichiers.'
```

Les sous-agents héritent du modèle de la session par défaut. `$cstack:setup-cstack` affiche six recommandations de modèle et d'effort à accepter, personnaliser ou remplacer par l'héritage ; vous pouvez aussi annuler. Les choix existants restent préservés sauf sélection explicite. Les paires sont vérifiées dans le catalogue courant et enregistrées dans `.cstack/models.json`, sans modifier la session principale ni la configuration globale. Voir le [tableau de recommandations](plugins/cstack/docs/guide/01-setup.md#configurer-cstack). Un choix indisponible ou un effort non configurable par l'hôte est signalé, sans substitution silencieuse.

La configuration peut aussi préparer les conventions du projet : un bloc cstack dans `AGENTS.md`, un guide local et le suivi de tickets choisi. Elle montre les changements avant application et conserve les instructions extérieures au bloc. Elle ne modifie pas `CLAUDE.md`, n'active pas cstack automatiquement et ne crée aucun ticket distant. La configuration des modèles seule reste disponible.

## Prérequis et limites

- Le travail de code courant utilise les outils disponibles dans Codex. Les sous-agents sont utilisés lorsqu'ils sont disponibles ; sinon, les étapes s'exécutent séquentiellement et cette limite est indiquée.
- Les assistants de suivi de PR et d'orchestration utilisent Bun et les dépendances verrouillées fournies avec le portage. Leur installation nécessite un accès au registre de paquets ou un cache Bun déjà rempli. Le lanceur utilise bash et Python 3.9 ou plus récent. L'analyse du `config.toml` de Codex dans `scripts/verify-behavior.py` exige Python 3.11 ou plus récent. Les opérations GitHub nécessitent `git` et `gh` authentifié.
- Chaque lancement copie les scripts dans un dossier temporaire distinct sous `.cstack/tools/`, installe les dépendances verrouillées et nettoie cette copie après exécution. Aucun exécutable déjà présent dans le projet n'est réutilisé. Le cache du plugin installé reste intact. Les points de reprise et choix de modèles restent locaux et doivent être exclus des commits.
- Les outils de navigateur, les connecteurs et les tâches planifiées sont facultatifs. Une capacité absente est signalée ; aucun résultat de test ni travail en arrière-plan n'est simulé.
- Les webhooks Grok Bot et les automatisations événementielles Benny de Cursor ne disposent pas d'un équivalent intégré. Leurs limites sont conservées dans le [guide de portage](docs/PORTING.md).

Une demande de revue ou l'activation du mode n'autorise pas à envoyer un message, ouvrir une PR, fusionner ou publier. cstack suit l'autorisation donnée pour la tâche concrète.

## Développement

Les commandes suivent l'ordre du processus `.github/workflows/validate.yml`. Installer les assistants avant tout `tsc`. Revenir à la racine avant le `tsc` du dépôt.

```sh
bun scripts/validate.ts
python3 -m unittest discover -s tests -p 'test_*.py'
bun test tests
cd plugins/cstack/skills/cstack/scripts
bun install --frozen-lockfile
bun run test
bun run typecheck
cd ../../../../..
plugins/cstack/skills/cstack/scripts/node_modules/.bin/tsc -p tsconfig.json
bash -n plugins/cstack/scripts/run-tool.sh plugins/cstack/skills/cstack/scripts/worktree-audit.sh plugins/cstack/skills/show-me-your-work/scripts/log.sh
git diff --check
```

Python 3.9 ou plus récent exécute les assistants et toute la suite de tests. L'analyse du fichier `config.toml` de Codex dans `scripts/verify-behavior.py` exige Python 3.11 ou plus récent.

Le [guide](plugins/cstack/docs/guide/README.md) détaille les processus. Le [rapport de vérification](docs/VERIFICATION.md) distingue les tests effectués des limites de validation. `UPSTREAM.json` identifie les fichiers source et `PORTING.json` leur destination dans cstack. Le [journal des modifications](CHANGELOG.md) décrit 0.4.0.

## Licence

MIT, avec conservation du copyright de Lauren Tan. Voir [LICENSE](plugins/cstack/LICENSE) et [NOTICE](plugins/cstack/NOTICE.md). Ce portage indépendant n'est pas un produit officiel de Cursor ou d'OpenAI.

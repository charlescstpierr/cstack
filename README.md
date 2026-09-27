# cstack

**Des workflows d'ingénierie vérifiés pour Codex App et CLI.** cstack apprend à Codex à investiguer avant de coder, à concevoir avant d'implémenter, à faire relire par des sous-agents indépendants et à prouver le résultat avant de livrer.

C'est le portage des processus de [pstack](https://github.com/cursor/plugins/tree/889ec4b68fa5aab0e867dad71ec3fdf386ae48f3/pstack) vers les outils natifs de Codex, sans moteur d'orchestration supplémentaire. Rien ne change dans vos projets tant que vous n'invoquez pas `$cstack:cstack`. [Installation en une commande](#installer).

> **Agent IA (Codex) chargé de l'installer ?** Suivez [INSTALL-AGENT.md](INSTALL-AGENT.md).

## Ce que cstack apporte

- **Un routeur, `$cstack:cstack`.** Il lit la demande, choisit le guide d'exécution adapté (bug, fonctionnalité, revue, livraison…) et le suit jusqu'à une preuve.
- **Des sous-agents natifs.** Exploration parallèle, panels d'implémentations concurrentes, revues contradictoires, avec les agents de Codex ou des workers Codex CLI et Claude Code.
- **Une vérification exigée.** TDD rouge → vert pour les changements de comportement, revue indépendante, et des limites annoncées plutôt que des résultats simulés.
- **Des nettoyages ciblés.** `deslop` pour le code, `unslop` pour la prose, `no-comments` pour les commentaires.
- **Le respect de votre cadre.** Le mode Plan, les instructions du projet et les autorisations Codex restent prioritaires. Aucune compétence ne s'active seule.

## Installation

### Prérequis

| Outil | Rôle | Obligatoire |
| --- | --- | --- |
| [Codex CLI](https://github.com/openai/codex) (`npm install -g @openai/codex`) | Installe et exécute le plugin | Oui |
| `git` connecté à GitHub, en HTTPS ou en SSH | Cloner ce dépôt privé | Oui |
| [`gh`](https://cli.github.com) authentifié | Installation en une ligne, suivi de PR | Recommandé |
| Python 3.9 ou plus récent | Script d'installation et lanceur des assistants | Oui |
| [Bun](https://bun.sh) | Suivi de PR et orchestration | Facultatif |

Le dépôt est privé : votre compte GitHub doit y avoir accès. Si Git n'est pas encore connecté, lancez `gh auth login` puis `gh auth setup-git`.

### Installer

En une ligne, qui télécharge le script puis le lance (un téléchargement refusé arrête tout) :

```sh
gh api repos/charlescstpierr/cstack/contents/install.sh -H "Accept: application/vnd.github.raw" > install-cstack.sh && bash install-cstack.sh install
```

Ou depuis un clone :

```sh
git clone https://github.com/charlescstpierr/cstack.git
cd cstack
./install.sh install
```

Ouvrez ensuite une **nouvelle tâche** dans Codex App ou une nouvelle session CLI. Le CLI et l'application partagent l'installation s'ils utilisent le même profil Codex.

### Faire installer par un agent IA

Donnez ce message à Codex, dans une tâche ouverte sur n'importe quel dossier. Le dépôt étant privé, l'agent lit la procédure avec `gh` ou Git plutôt que par le web :

```text
Installe le plugin cstack. Lis d'abord sa procédure pour agents dans le dépôt privé charlescstpierr/cstack (gh api repos/charlescstpierr/cstack/contents/INSTALL-AGENT.md -H "Accept: application/vnd.github.raw", ou sans gh : clone le dépôt avec git, en HTTPS ou en SSH, dans un dossier temporaire), puis suis-la.
```

[INSTALL-AGENT.md](INSTALL-AGENT.md) guide l'agent pas à pas : prérequis, `install.sh install` ou `update`, vérification par `doctor`, lecture des codes de sortie et pannes connues. L'agent demande votre accord avant d'installer un outil global, ne lit pas vos credentials et ne laisse aucun fichier dans votre projet. Il ne modifie la configuration de Codex que par les commandes `codex plugin`, jamais à la main. Ouvrez ensuite une nouvelle tâche pour utiliser les compétences.

### Gérer l'installation

| Commande | Effet |
| --- | --- |
| `./install.sh install` | Installe depuis GitHub. La relancer ne change rien. |
| `./install.sh install --ref v1.2.0` | Installe une branche, un tag ou un commit précis. |
| `./install.sh install --local` | Installe depuis ce clone, pour tester une modification locale. |
| `./install.sh update` | Met à jour vers la dernière révision de la source installée. |
| `./install.sh doctor` | Vérifie Codex, l'accès au dépôt, Python, Bun, `gh` et l'état du plugin. |
| `./install.sh uninstall` | Retire le plugin et sa source. Les dossiers `.cstack/` des projets restent. |

Sans clone, utilisez le fichier téléchargé : `bash install-cstack.sh update`.

Le script passe uniquement par `codex plugin` : il ne modifie jamais `~/.codex` à la main. Il essaie HTTPS puis SSH pour joindre le dépôt, et teste une nouvelle source à part avant de remplacer l'ancienne. Après une mise à jour, ouvrez une nouvelle conversation pour charger les compétences.

<details>
<summary>Installation manuelle, sans le script</summary>

```sh
codex plugin marketplace add charlescstpierr/cstack   # ou : charlescstpierr/cstack --ref <ref>, ou /chemin/absolu/vers/cstack
codex plugin add cstack@cstack
```

Mise à jour : `codex plugin marketplace upgrade cstack`, puis `codex plugin add cstack@cstack`. Retrait : `codex plugin remove cstack@cstack`, puis `codex plugin marketplace remove cstack`.

</details>

## Premiers pas

Dans le sélecteur de l'App ou du CLI interactif, tapez `$cstack` et choisissez la compétence **cstack**. En texte brut, notamment avec `codex exec`, utilisez le nom complet :

```text
$cstack:cstack Corrige ce bug et vérifie le résultat.
$cstack:cstack Examine cette modification avant livraison.
$cstack:architect Propose la structure de cette fonctionnalité.
$cstack:interrogate Fais une revue contradictoire de ce diff.
$cstack:setup-cstack
```

```sh
codex exec '$cstack:cstack Examine cette modification sans changer les fichiers.'
```

Le mode reste actif dans la tâche jusqu'à ce que vous demandiez de l'arrêter, par exemple « arrête cstack ». Les compétences spécialisées restent utilisables à la demande.

Codex exige que la demande de délégation figure dans votre message : le texte d'une compétence ne suffit pas à lancer un sous-agent. Les prompts par défaut des compétences qui délèguent la contiennent, donc sélectionnez la compétence dans le sélecteur plutôt que de taper son nom. En texte brut, ajoutez-la vous-même : `$cstack:cstack Corrige ce bug. Délègue le travail indépendant à des sous-agents natifs en parallèle.` Voir [le dépannage](plugins/cstack/docs/guide/10-recipes-and-pitfalls.md#un-seul-agent-travaille) si un seul agent travaille.

## Les compétences

Le catalogue contient 29 compétences. Chacune s'invoque par `$cstack:<nom>`.

| Domaine | Compétences |
| --- | --- |
| Piloter | `cstack` route le travail et vérifie le résultat · `setup-cstack` configure le projet et les modèles délégués |
| Préparer | `clarify` lève les ambiguïtés · `domain` fixe le vocabulaire et les décisions · `horizon` planifie un grand objectif · `audit-architecture` repère les simplifications sans toucher au code |
| Comprendre | `how` explique un flux de code · `why` retrace une décision · `teach` combine les deux · `recall` reconstruit le travail récent · `bro` reformule simplement |
| Concevoir | `architect` pose types et modules avant le code · `arena` met N implémentations en concurrence · `figure-it-out` bâtit un playbook pour un travail ambitieux |
| Construire | `tdd` du rouge au vert · `swarm` distribue le travail en parallèle · `typescript-best-practices` · `technical-writing` |
| Relire et nettoyer | `interrogate` revue contradictoire · `blast-radius` ce qu'un changement peut casser · `deslop` le code · `unslop` la prose · `no-comments` les commentaires |
| Vérifier et tracer | `create-verification-skill` et `maintain-verification-skill` pilotent l'app comme un utilisateur · `show-me-your-work` journalise les décisions |
| Personnaliser | `automate-me` crée votre propre mode · `reflect` transforme les leçons en améliorations · `make-bot-ui` réveille Codex depuis une page locale |

Les 23 principes sont des [références internes](plugins/cstack/docs/guide/08-principles.md), lues seulement quand elles servent le travail ou que vous en nommez un : `$cstack:cstack applique le principe « Discipline aux frontières » à cette validation`.

`$cstack:cstack` appelle les préparations seulement si la demande l'exige : `clarify` pour une ambiguïté réelle, `horizon` pour un objectif vraiment long ou multi-phase. Une tâche claire part directement vers son guide d'exécution, avec revue et vérification ; plusieurs fichiers ne suffisent pas à déclencher Horizon. Une question d'architecture ou de flux de code part en exploration parallèle, avec au moins deux explorateurs même pour une seule cible, puis une synthèse. Voir le [guide de conception](plugins/cstack/docs/guide/04-design.md).

## Configurer un projet

`$cstack:setup-cstack` affiche d'abord sept recommandations vérifiées de modèle et d'effort pour tous les rôles et positions de panel. Il affiche ensuite la configuration actuelle et l'héritage éventuel. Vous pouvez accepter, personnaliser, conserver, choisir l'héritage pour certains rôles ou annuler. Les choix sont vérifiés dans le catalogue courant et enregistrés dans `.cstack/models.json`, sans modifier la session principale ni la configuration globale. Voir le [tableau de recommandations](plugins/cstack/docs/guide/01-setup.md#configurer-cstack).

La configuration peut aussi préparer les conventions du projet : un bloc cstack dans `AGENTS.md`, un guide local et le suivi de tickets choisi. Elle montre les changements avant de les appliquer et conserve les instructions extérieures au bloc. Elle ne modifie pas `CLAUDE.md`, n'active pas cstack automatiquement et ne crée aucun ticket distant.

## Codex et Claude ensemble

Le coordinateur reste dans Codex. Arena, Swarm, Interrogate et Architect peuvent répartir leurs workers entre Codex CLI et Claude Code ; chaque CLI utilise son propre login officiel, et cstack ne lit ni ne copie ses credentials. Voir le [guide des workers CLI](plugins/cstack/docs/guide/11-cli-workers.md) et les [preuves et limites](docs/VERIFICATION.md) : Grok et Cursor restent hors validation connectée, et Cursor est limité à la lecture seule.

## Limites

- Sans sous-agents disponibles, les étapes s'exécutent séquentiellement et cette limite est annoncée.
- Chaque lancement d'assistant copie les scripts sous `~/.cache/cstack/stages/`, installe les dépendances verrouillées, puis nettoie. Le dépôt cible ne reçoit que `.cstack/` et son fichier d'exclusion. Le cache du plugin installé reste intact.
- Navigateur, connecteurs et tâches planifiées sont facultatifs. Une capacité absente est signalée ; aucun résultat n'est simulé.
- Les webhooks Grok Bot et les automatisations Benny de Cursor n'ont pas d'équivalent intégré. Voir le [guide de portage](docs/PORTING.md).
- Une demande de revue n'autorise ni à envoyer un message, ni à ouvrir une PR, ni à fusionner. Avec `$cstack:cstack`, l'implémentation suit la portée de livraison du [contrat d'exécution](plugins/cstack/skills/cstack/references/runtime/activation.md) ; le merge reste séparé.
- Un autre portage de pstack peut exposer les mêmes noms de compétences : `$cstack:architect` désigne ce plugin, un `$architect` nu ne le distingue pas.

## Développement

Les mises à jour amont passent par le [synchroniseur](docs/UPSTREAM-SYNC.md) : simulation, résolution des adaptations locales, puis application sans avancer le pin en cas de conflit. Les [faits du paquet](docs/GENERATED-FACTS.md) sont dérivés des inventaires ; régénérez-les avec `bun scripts/generate-facts.mjs` après une mise à jour.

Les commandes suivent l'ordre de `.github/workflows/validate.yml`. Installez les assistants avant tout `tsc`, puis revenez à la racine avant le `tsc` du dépôt.

```sh
bun scripts/generate-facts.mjs --check
bun scripts/validate.ts
python3 -m unittest discover -s tests -p 'test_*.py'
bun test tests
cd plugins/cstack/skills/cstack/scripts
bun install --frozen-lockfile
bun run test
bun run typecheck
cd ../../../../..
plugins/cstack/skills/cstack/scripts/node_modules/.bin/tsc -p tsconfig.json
bash -n plugins/cstack/scripts/run-tool.sh plugins/cstack/skills/cstack/scripts/worktree-audit.sh plugins/cstack/skills/show-me-your-work/scripts/log.sh install.sh
docker run --rm -v "$PWD:/repo:ro" -w /repo \
  koalaman/shellcheck:v0.10.0@sha256:2097951f02e735b613f4a34de20c40f937a6c8f18ecb170612c88c34517221fb \
  --severity=warning plugins/cstack/scripts/run-tool.sh plugins/cstack/skills/cstack/scripts/worktree-audit.sh plugins/cstack/skills/show-me-your-work/scripts/log.sh install.sh
docker run --rm -v "$PWD:/repo:ro" -w /repo \
  rhysd/actionlint:1.7.12@sha256:b1934ee5f1c509618f2508e6eb47ee0d3520686341fec936f3b79331f9315667 \
  -no-color .github/workflows/*.yml plugins/cstack/automations/intake/templates/github-intake.yml
git diff --check
```

Python 3.9 ou plus récent exécute les assistants et toute la suite de tests. L'analyse du `config.toml` de Codex dans `scripts/verify-behavior.py` exige Python 3.11 ou plus récent.

Le [guide](plugins/cstack/docs/guide/README.md) détaille les processus. Le [rapport de vérification](docs/VERIFICATION.md) distingue les tests effectués des limites. Le [journal des modifications](CHANGELOG.md) décrit les versions.

## Provenance et licence

Version amont épinglée `0.15.2`, commit `889ec4b68fa5aab0e867dad71ec3fdf386ae48f3`. `UPSTREAM.json` identifie les fichiers source, `PORTING.json` leur destination dans cstack, et [MAINTENANCE-SOURCES.json](MAINTENANCE-SOURCES.json) la provenance des outils de développement adaptés de pstack-claude.

La documentation et les messages sont en français ; les noms de commandes et de compétences, chemins, clés de configuration et licences originales sont conservés pour compatibilité.

MIT, avec conservation du copyright de Lauren Tan. Voir [LICENSE](plugins/cstack/LICENSE) et [NOTICE](plugins/cstack/NOTICE.md). Ce portage indépendant n'est pas un produit officiel de Cursor ou d'OpenAI.

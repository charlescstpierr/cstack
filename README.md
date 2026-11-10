# cstack

**Des workflows d'ingénierie pour T3 Code, avec Codex et Claude.** cstack apprend au coordinateur à investiguer avant de coder, à concevoir avant d'implémenter, à faire relire par des sous-agents indépendants et à prouver le résultat avant de livrer.

## Installer en une minute

Il vous faut [T3 Code](https://github.com/pingdotgg/t3code), [Codex](https://github.com/openai/codex) ou [Claude Code](https://github.com/anthropics/claude-code). Le dépôt est public : aucun compte GitHub n'est nécessaire.

**1. Copiez cette commande dans un terminal :**

```sh
curl -fsSL https://raw.githubusercontent.com/charlescstpierr/cstack/main/install.sh -o install-cstack.sh && bash install-cstack.sh install
```

Elle installe cstack dans Codex et dans Claude Code, pour chacun qui est présent sur la machine. T3 Code utilise ces deux installations : rien d'autre à faire. La commande exécute le script de la branche `main` avec vos droits ; pour le lire avant, lancez d'abord la partie `curl`, ouvrez `install-cstack.sh`, puis lancez `bash install-cstack.sh install`.

**2. Ouvrez une nouvelle tâche et tapez :**

| Tâche                                    | Commande                                                |
| ---------------------------------------- | ------------------------------------------------------- |
| Codex, dans T3 Code ou dans Codex        | `$cstack:cstack Corrige ce bug et vérifie le résultat.` |
| Claude, dans T3 Code ou dans Claude Code | `/cstack:cstack Corrige ce bug et vérifie le résultat.` |

C'est tout. Rien ne change dans vos projets tant que vous n'invoquez pas cstack.

**Vous préférez ne rien taper ?** Collez ce message dans une tâche Codex ou Claude, ouverte sur n'importe quel dossier. L'agent installe cstack pour vous et vous demande votre accord avant d'installer un outil manquant :

```text
Installe le plugin cstack. Lis d'abord sa procédure pour agents à l'adresse https://raw.githubusercontent.com/charlescstpierr/cstack/main/INSTALL-AGENT.md, puis suis-la.
```

> **Vous êtes l'agent IA chargé de l'installation ?** Suivez [INSTALL-AGENT.md](INSTALL-AGENT.md).

<details>
<summary><b>La commande échoue ?</b></summary>

| Message                                    | Solution                                                                               |
| ------------------------------------------ | -------------------------------------------------------------------------------------- |
| `curl: command not found`, ou erreur réseau de `curl` | Utilisez le clone ci-dessous, ou vérifiez le réseau.                                  |
| `accès refusé à charlescstpierr/cstack`  | Git ne joint pas GitHub. Vérifiez le réseau ; si Git passe par un compte GitHub, lancez `gh auth login` puis `gh auth setup-git`. |
| `Codex CLI introuvable, Claude Code aussi` | Installez Codex (`npm install -g @openai/codex`) ou Claude Code.                       |
| `Python 3.9 ou plus récent est requis`     | Installez Python 3.9 ou plus récent.                                                   |

Sans `curl`, depuis un clone :

```sh
git clone https://github.com/charlescstpierr/cstack.git
cd cstack
./install.sh install
```

Sous Windows, installez depuis WSL. `bash install-cstack.sh doctor` vérifie chaque prérequis et dit ce qui manque.

</details>

<details>
<summary><b>Mettre à jour, vérifier, désinstaller</b></summary>

Depuis le dossier où se trouve `install-cstack.sh` (ou `./install.sh` dans un clone). Chaque commande traite Codex et Claude Code :

| Commande                                      | Effet                                                                         |
| --------------------------------------------- | ----------------------------------------------------------------------------- |
| `bash install-cstack.sh update`               | Met à jour vers la dernière révision de la source installée.                  |
| `bash install-cstack.sh doctor`               | Vérifie Codex, Claude Code, l'accès au dépôt, Python, Bun, `gh` et le plugin. |
| `bash install-cstack.sh uninstall`            | Retire le plugin et sa source. Les dossiers `.cstack/` des projets restent.   |
| `bash install-cstack.sh install --ref v1.2.0` | Installe une branche, un tag ou un commit précis.                             |
| `./install.sh install --local`                | Installe depuis un clone, pour tester une modification locale.                |

Relancer `install` ne change rien. Après une mise à jour, ouvrez une nouvelle tâche pour charger les compétences. Le CLI et l'application Codex partagent l'installation s'ils utilisent le même profil.

Le script passe uniquement par `codex plugin` et `claude plugin` : il ne modifie jamais `~/.codex` ni `~/.claude` à la main. Il essaie HTTPS puis SSH pour joindre le dépôt. Côté Codex, il teste une nouvelle source à part avant de remplacer l'ancienne.

| Outil                                                                         | Rôle                                            | Obligatoire   |
| ----------------------------------------------------------------------------- | ----------------------------------------------- | ------------- |
| [Codex CLI](https://github.com/openai/codex) (`npm install -g @openai/codex`) | Installe et exécute le plugin dans Codex        | L'un des deux |
| [Claude Code](https://github.com/anthropics/claude-code)                    | Installe et exécute le plugin dans Claude       | L'un des deux |
| `git`                                                                         | Récupère ce dépôt                               | Oui           |
| Python 3.9 ou plus récent                                                     | Script d'installation et lanceur des assistants | Oui           |
| [`gh`](https://cli.github.com) authentifié                                    | Suivi de PR                                     | Facultatif         |
| [Bun](https://bun.sh)                                                         | Suivi de PR et orchestration                    | Facultatif    |

</details>

<details>
<summary><b>Installation manuelle, sans le script</b></summary>

Codex :

```sh
codex plugin marketplace add charlescstpierr/cstack   # ou : charlescstpierr/cstack --ref <ref>, ou /chemin/absolu/vers/cstack
codex plugin add cstack@cstack
```

Mise à jour : `codex plugin marketplace upgrade cstack`, puis `codex plugin add cstack@cstack`. Retrait : `codex plugin remove cstack@cstack`, puis `codex plugin marketplace remove cstack`.

Claude Code :

```sh
claude plugin marketplace add charlescstpierr/cstack   # ou : charlescstpierr/cstack#<ref>, ou /chemin/absolu/vers/cstack
claude plugin install cstack@cstack
```

Mise à jour : `claude plugin marketplace update cstack`, puis `claude plugin update cstack@cstack`. Retrait : `claude plugin uninstall cstack@cstack`, puis `claude plugin marketplace remove cstack`.

</details>

## Ce que cstack apporte

C'est le portage des processus de [pstack](https://github.com/cursor/plugins/tree/12d587dfb20741cafc376c42c696c5f6e2a64487/pstack) vers les outils natifs de T3 Code, Codex et Claude Code, sans moteur d'orchestration supplémentaire.

- **Un routeur, `$cstack:cstack` (ou `/cstack:cstack` dans Claude).** Il lit la demande, choisit le guide d'exécution adapté (bug, fonctionnalité, revue, livraison…) et le suit jusqu'à une preuve.
- **Des sous-agents natifs.** Exploration parallèle, panels d'implémentations concurrentes, revues contradictoires, avec les agents de Codex ou des workers Codex CLI et Claude Code.
- **Une vérification exigée.** TDD rouge → vert pour les changements de comportement, revue indépendante, et des limites annoncées plutôt que des résultats simulés.
- **Des nettoyages ciblés.** `deslop` pour le code, `unslop` pour la prose, `no-comments` pour les commentaires.
- **Le respect de votre cadre.** Le mode Plan, les instructions du projet et les autorisations Codex restent prioritaires. Aucune compétence ne s'active seule.

## Dans T3 Code

cstack s'installe sur la machine qui exécute vos agents T3, puis s'invoque dans un nouveau fil, Codex ou Claude.

1. Installez le plugin sur cette machine avec la [commande d'installation](#installer-en-une-minute), ou collez le message pour agent dans un fil T3 Code.
2. Ouvrez un nouveau fil dans T3 Code. Un fil ouvert avant l'installation ne voit pas le plugin.
3. Commencez votre message par `$cstack:cstack` dans un fil Codex, ou par `/cstack:cstack` dans un fil Claude, puis écrivez la demande.

Le guide [Installer cstack dans T3 Code](plugins/cstack/docs/guide/12-t3-code.md) détaille les worktrees, le choix des modèles, la mise à jour et le dépannage.

Dans T3 Code, le coordinateur utilise les outils de l'hôte pour choisir les modèles et les efforts, déléguer, isoler les checkouts et collecter les résultats. Le [contrat T3](plugins/cstack/skills/cstack/references/runtime/t3.md) prime alors sur les consignes Codex autonome. Les helpers cstack vérifient les sélections et préparent les briefs. Ils ne lancent ni moteur d'orchestration ni CLI de repli.

Le chargement du plugin installé est observé dans un fil Codex de T3 Code sur un serveur Linux : [reçu](docs/evidence/t3-installed-plugin-2026-11-09.json). Trois revues réelles, sur trois fournisseurs, ont suivi le pipeline T3 depuis un coordinateur Codex et renvoyé leurs findings au parent : [reçu et limites](docs/evidence/t3-council-transport-r5.json), [vérification T3](docs/T3-VERIFICATION.md). Le plugin Claude Code et son hook sont observés hors T3 ; un fil Claude de T3 Code qui charge cstack, et l'application de bureau T3 Code sur macOS et sur Windows, ne sont pas observés.

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

Dans Claude Code ou une tâche Claude de T3, la même compétence s'appelle `/cstack:cstack` : `/cstack:cstack Corrige ce bug et vérifie le résultat.`

Le mode reste actif dans la tâche jusqu'à ce que vous demandiez de l'arrêter, par exemple « arrête cstack ». Les compétences spécialisées restent utilisables à la demande.

Codex ne lance un sous-agent que sur demande explicite, venue de votre message, d'un `AGENTS.md` ou d'une compétence. Si cstack travaille seul, ajoutez-la à votre message : `$cstack:cstack Corrige ce bug. Délègue le travail indépendant à des sous-agents natifs en parallèle.` Voir [le dépannage](plugins/cstack/docs/guide/10-recipes-and-pitfalls.md#un-seul-agent-travaille) si un seul agent travaille.

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

`$cstack:setup-cstack` demande d'abord un budget de raisonnement (illimité, large, moyen ou réduit), puis affiche sept recommandations vérifiées de modèle et d'effort pour tous les rôles et positions de panel. Il affiche ensuite la configuration actuelle et l'héritage éventuel. Vous pouvez accepter, personnaliser, conserver, choisir l'héritage pour certains rôles ou annuler. Les choix sont vérifiés dans le catalogue courant et enregistrés dans `.cstack/models.json`, sans modifier la session principale ni la configuration globale. Voir le [tableau de recommandations](plugins/cstack/docs/guide/01-setup.md#configurer-cstack).

La configuration peut aussi préparer les conventions du projet : un bloc cstack dans `AGENTS.md`, un guide local et le suivi de tickets choisi. Elle montre les changements avant de les appliquer et conserve les instructions extérieures au bloc. Elle ne modifie pas `CLAUDE.md`, n'active pas cstack automatiquement et ne crée aucun ticket distant.

## Codex et Claude ensemble

Hors T3, un coordinateur Codex peut répartir les workers d'Arena, Swarm, Interrogate et Architect entre Codex CLI et Claude Code ; chaque CLI utilise son propre login officiel, et cstack ne lit ni ne copie ses credentials. Voir le [guide des workers CLI](plugins/cstack/docs/guide/11-cli-workers.md) et les [preuves et limites](docs/VERIFICATION.md) : Grok et Cursor restent hors validation connectée, et Cursor est limité à la lecture seule.

## Limites

- Hors T3, Claude Code charge les compétences et le rappel du mode, mais les guides d'exécution nomment les outils de Codex. Leur transposition par un coordinateur Claude n'a pas été observée.
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

Python 3.9 ou plus récent exécute les assistants et toute la suite de tests. L'analyse du `config.toml` de Codex dans `scripts/verify-behavior.py` et `scripts/check-installed-loader.py` exige Python 3.11 ou plus récent.

Le [guide](plugins/cstack/docs/guide/README.md) détaille les processus. Le [rapport de vérification](docs/VERIFICATION.md) distingue les tests effectués des limites. Le [journal des modifications](CHANGELOG.md) décrit les versions.

## Provenance et licence

Version amont épinglée `0.15.5`, commit `12d587dfb20741cafc376c42c696c5f6e2a64487`. `UPSTREAM.json` identifie les fichiers source, `PORTING.json` leur destination dans cstack, et [MAINTENANCE-SOURCES.json](MAINTENANCE-SOURCES.json) la provenance des outils de développement adaptés de pstack-claude.

La documentation et les messages sont en français ; les noms de commandes et de compétences, chemins, clés de configuration et licences originales sont conservés pour compatibilité.

MIT, avec conservation du copyright de Lauren Tan. Voir [LICENSE](plugins/cstack/LICENSE) et [NOTICE](plugins/cstack/NOTICE.md). Ce portage indépendant n'est pas un produit officiel de Cursor ou d'OpenAI.

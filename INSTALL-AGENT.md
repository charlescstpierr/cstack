# Installer cstack : procédure pour un agent IA

Ce fichier s'adresse à un agent de code (Codex, Claude Code, ou une tâche Codex ou Claude de T3 Code) à qui l'utilisateur a demandé d'installer cstack. Le script installe cstack dans Codex et dans Claude Code, pour chacun qui est présent ; T3 Code utilise ces installations. Suivez les étapes dans l'ordre et rapportez le résultat réel. Les humains trouveront la même installation, expliquée, dans le [README](README.md#installer-en-une-minute).

## Règles

- Passez uniquement par `install.sh`. Il appelle `codex plugin` et `claude plugin` ; n'éditez jamais `~/.codex`, `~/.claude` ni les caches de plugins à la main.
- Ne lisez, n'affichez ni ne copiez aucun token ou credential. Si l'accès GitHub manque, demandez à l'utilisateur de se connecter.
- Demandez avant d'installer un prérequis global (Codex CLI, Claude Code, Python, Bun, `gh`).
- Les commandes ont besoin du réseau et d'écrire dans les dossiers de Codex et de Claude Code. Dans un bac à sable, demandez l'approbation prévue par Codex ; ne contournez pas les permissions.
- N'allez pas plus loin que l'installation : ne lancez pas `$cstack:setup-cstack` et ne choisissez aucun modèle à la place de l'utilisateur.

## Étapes

1. **Environnement.** `bash --version` doit réussir : `install.sh` et `doctor` en ont besoin. Sous Windows, cstack s'installe depuis WSL, pas depuis PowerShell. Sans Bash, arrêtez-vous et dites-le à l'utilisateur. Les autres prérequis (Codex CLI ou Claude Code, Python, Git et l'accès au dépôt) sont vérifiés par `doctor` à l'étape 3.

2. **Obtenir le script, hors du projet de l'utilisateur.** Si vous lisez ce fichier depuis un clone de `charlescstpierr/cstack` (le dossier courant ou un clone fait pour le lire), utilisez l'`install.sh` de ce même clone : ce fichier et le script vont ensemble. Sinon, travaillez dans un dossier temporaire pour ne laisser aucun fichier dans le dépôt de l'utilisateur :

   ```sh
   tmp="$(mktemp -d)" && echo "$tmp" &&
     curl -fsSL https://raw.githubusercontent.com/charlescstpierr/cstack/main/install.sh -o "$tmp/install.sh" &&
     test -s "$tmp/install.sh"
   ```

   Lancez ce bloc en une seule commande et notez le chemin affiché : `$tmp` n'existe que dans ce shell, alors dans les commandes suivantes, repli ci-dessous compris, écrivez ce chemin en toutes lettres jusqu'au nettoyage.

   Si cette commande échoue (`curl` absent ou adresse injoignable) : `git clone --depth 1 https://github.com/charlescstpierr/cstack.git "$tmp/cstack"` (ou l'URL SSH `git@github.com:charlescstpierr/cstack.git`), puis `$tmp/cstack/install.sh`. Dans la suite, `install.sh` désigne le script obtenu, lancé avec `bash`.

3. **Voir l'état actuel.** Lancez `install.sh doctor`.
   - `doctor` finit avec le code 0 et affiche une ligne `✓ plugin cstack@cstack` par hôte présent (Codex, et `dans Claude Code` pour Claude) : cstack est installé et fonctionne. Ne changez rien, sauf si l'utilisateur demande la dernière version (`install.sh update`) ou une version précise (`install.sh update --ref <ref>`, qui récupère réellement cette version).
   - Sinon : `install.sh install`, avec `--ref <ref>` si l'utilisateur demande une version précise (branche, tag ou commit).

4. **Vérifier.** Si l'étape 3 a lancé une commande, relancez `install.sh doctor`. Le code de sortie doit être 0, et chaque hôte présent doit avoir sa ligne : `✓ plugin cstack@cstack : installed, enabled <version>` pour Codex, `✓ plugin cstack@cstack dans Claude Code : installed, enabled <version>` pour Claude Code.

5. **Conclure.** Supprimez les dossiers temporaires que vous avez créés, à l'étape 2 ou pour lire ce fichier, mais jamais un clone qui existait avant vous : l'installation n'en dépend pas. Donnez la version installée et dites à l'utilisateur d'ouvrir une **nouvelle tâche**, dans T3 Code, Codex ou Claude Code, puis de taper `$cstack:cstack` dans une tâche Codex ou `/cstack:cstack` dans une tâche Claude. Dans T3 Code, c'est un nouveau fil, et le [guide T3](plugins/cstack/docs/guide/12-t3-code.md) décrit la suite. La tâche en cours, y compris la vôtre, ne voit pas les compétences ajoutées.

## Lire les résultats

| Code de sortie | Sens |
| --- | --- |
| 0 | Réussite. Pour `doctor` : aucune ligne `✗`. |
| Autre | Échec. Pour `doctor`, les lignes `✗` en donnent la cause (avant une installation, une ligne `✗ plugin cstack@cstack` est attendue). Pour les autres commandes, lisez les dernières lignes : un message `cstack :`, l'erreur brute de Codex ou de Claude Code, ou l'aide du script si la commande est mal formée. |

Dans `doctor`, `✓` est vérifié, `!` est facultatif (Bun, `gh`) et n'empêche pas l'usage, `✗` est bloquant.

## Pannes connues

| Message | Action |
| --- | --- |
| `Codex CLI introuvable` | Ni Codex ni Claude Code n'est présent. Proposez `npm install -g @openai/codex` et attendez l'accord de l'utilisateur. |
| `installation dans Claude Code impossible` ou `mise à jour dans Claude Code impossible` | Lisez l'erreur de Claude Code affichée juste avant et rapportez-la. L'installation Codex, faite avant, reste en place. |
| `refusé à charlescstpierr/cstack` | Git ne joint le dépôt ni en HTTPS ni en SSH. Faites vérifier le réseau. Si Git passe par un compte GitHub mal connecté, l'utilisateur lance `gh auth login` puis `gh auth setup-git`. |
| `cstack est désactivé` | L'utilisateur l'a désactivé exprès. Ne forcez rien : demandez-lui de le réactiver dans Codex, ou de choisir `install.sh uninstall` puis `install.sh install`. |
| `source inutilisable. L'installation actuelle est conservée.` | L'essai de la nouvelle source a échoué et rien n'a changé. Lisez l'erreur de Codex affichée juste avant : référence introuvable, réseau, permissions ou disque plein. Rapportez cette cause ; ne supposez pas une mauvaise `--ref`. |
| `impossible de lire l'état de Codex` ou `état du plugin illisible` | Codex CLI ne répond pas correctement. Faites vérifier `codex --version` et la mise à jour de Codex ; ne touchez pas à ses fichiers. |
| `épinglé sur un commit` | L'installation suit un commit fixe, souvent voulu. Demandez à l'utilisateur avant `install.sh install --ref main`. |
| `n'a pas pu être restaurée` | Le changement de source a échoué et l'ancienne n'a pas pu être remise : cstack n'est peut-être plus installé. Relancez `install.sh doctor`, puis `install.sh install` si la ligne du plugin n'est pas `✓`, et dites-le à l'utilisateur. |
| `Source locale : recopie depuis le clone` | Si le code de sortie est 0, c'est une réussite, mais depuis un clone local (`install --local`) : pas forcément la dernière version. Dites-le, et demandez à l'utilisateur s'il veut mettre son clone à jour lui-même ou passer à GitHub avec `install.sh install --ref main`. |
| `cstack n'est pas installé` | Vous avez lancé `update` trop tôt : lancez `install.sh install`. |

Pour tout autre échec, montrez le message tel quel à l'utilisateur.

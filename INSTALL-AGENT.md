# Installer cstack : procédure pour un agent IA

Ce fichier s'adresse à un agent de code (Codex CLI ou Codex App) à qui l'utilisateur a demandé d'installer cstack. Suivez les étapes dans l'ordre et rapportez le résultat réel. Les humains trouveront la même installation, expliquée, dans le [README](README.md#installation).

## Règles

- Passez uniquement par `install.sh`. Il appelle `codex plugin` ; n'éditez jamais `~/.codex` ni le cache de plugins à la main.
- Ne lisez, n'affichez ni ne copiez aucun token ou credential. Si l'accès GitHub manque, demandez à l'utilisateur de se connecter.
- Demandez avant d'installer un prérequis global (Codex CLI, Python, Bun, `gh`).
- Les commandes ont besoin du réseau et d'écrire dans le dossier de Codex. Dans un bac à sable, demandez l'approbation prévue par Codex ; ne contournez pas les permissions.
- N'allez pas plus loin que l'installation : ne lancez pas `$cstack:setup-cstack` et ne choisissez aucun modèle à la place de l'utilisateur.

## Étapes

1. **Environnement.** Sous Windows, cstack s'installe depuis WSL, pas depuis PowerShell. Les autres prérequis (Codex CLI, Python, Git et l'accès au dépôt) sont vérifiés par `doctor` à l'étape 3.

2. **Obtenir le script, hors du projet de l'utilisateur.** Si vous êtes dans un clone de `charlescstpierr/cstack`, ou si vous en avez cloné un pour lire ce fichier, utilisez son `install.sh`. Sinon, travaillez dans un dossier temporaire pour ne laisser aucun fichier dans le dépôt de l'utilisateur :

   ```sh
   tmp="$(mktemp -d)" && echo "$tmp"
   gh api repos/charlescstpierr/cstack/contents/install.sh -H "Accept: application/vnd.github.raw" > "$tmp/install.sh" && test -s "$tmp/install.sh"
   ```

   Si cette commande échoue (`gh` absent ou non authentifié) : `git clone --depth 1 https://github.com/charlescstpierr/cstack.git "$tmp/cstack"` (ou l'URL SSH `git@github.com:charlescstpierr/cstack.git`), puis `$tmp/cstack/install.sh`. Notez le chemin affiché : si vos commandes tournent dans des shells séparés, `$tmp` n'existe plus au suivant, alors réutilisez ce chemin en toutes lettres jusqu'au nettoyage. Dans la suite, `install.sh` désigne le script obtenu, lancé avec `bash`.

3. **Voir l'état actuel.** Lancez `install.sh doctor`.
   - La ligne du plugin commence par `✓ plugin cstack@cstack` : cstack est installé et fonctionne. Ne changez rien, sauf si l'utilisateur demande la dernière version (`install.sh update`) ou une version précise (`install.sh update --ref <ref>`, qui récupère réellement cette version).
   - Sinon : `install.sh install`, avec `--ref <ref>` si l'utilisateur demande une version précise (branche, tag ou commit).

4. **Vérifier.** Si l'étape 3 a lancé une commande, relancez `install.sh doctor`. Le code de sortie doit être 0 et la ligne `✓ plugin cstack@cstack : installed, enabled <version>` doit apparaître.

5. **Conclure.** Supprimez les dossiers temporaires que vous avez créés, à l'étape 2 ou pour lire ce fichier, mais jamais un clone qui existait avant vous : l'installation n'en dépend pas. Donnez la version installée et dites à l'utilisateur d'ouvrir une **nouvelle tâche** Codex, puis de taper `$cstack:cstack`. La tâche en cours, y compris la vôtre, ne voit pas les compétences ajoutées.

## Lire les résultats

| Code de sortie | Sens |
| --- | --- |
| 0 | Réussite. Pour `doctor` : aucune ligne `✗`. |
| Autre | Échec. Pour `doctor`, les lignes `✗` en donnent la cause (avant une première installation, `✗ plugin cstack@cstack : absent` est attendu). Pour les autres commandes, lisez les dernières lignes : un message `cstack :`, l'erreur brute de Codex, ou l'aide du script si la commande est mal formée. |

Dans `doctor`, `✓` est vérifié, `!` est facultatif (Bun, `gh`) et n'empêche pas l'usage, `✗` est bloquant.

## Pannes connues

| Message | Action |
| --- | --- |
| `Codex CLI introuvable` | Proposez `npm install -g @openai/codex` et attendez l'accord de l'utilisateur. |
| `refusé à charlescstpierr/cstack` | Le compte GitHub n'a pas accès au dépôt privé, ou Git n'est pas connecté. Demandez à l'utilisateur de lancer `gh auth login` puis `gh auth setup-git`. |
| `cstack est désactivé` | L'utilisateur l'a désactivé exprès. Ne forcez rien : demandez-lui de le réactiver dans Codex, ou de choisir `install.sh uninstall` puis `install.sh install`. |
| `source inutilisable. L'installation actuelle est conservée.` | L'essai de la nouvelle source a échoué et rien n'a changé. Lisez l'erreur de Codex affichée juste avant : référence introuvable, réseau, permissions ou disque plein. Rapportez cette cause ; ne supposez pas une mauvaise `--ref`. |
| `impossible de lire l'état de Codex` ou `état du plugin illisible` | Codex CLI ne répond pas correctement. Faites vérifier `codex --version` et la mise à jour de Codex ; ne touchez pas à ses fichiers. |
| `épinglé sur un commit` | L'installation suit un commit fixe, souvent voulu. Demandez à l'utilisateur avant `install.sh install --ref main`. |
| `n'a pas pu être restaurée` | Le changement de source a échoué et l'ancienne n'a pas pu être remise : cstack n'est peut-être plus installé. Relancez `install.sh doctor`, puis `install.sh install` si le plugin est absent, et dites-le à l'utilisateur. |
| `cstack n'est pas installé` | Vous avez lancé `update` trop tôt : lancez `install.sh install`. |

Pour tout autre échec, montrez le message tel quel à l'utilisateur.

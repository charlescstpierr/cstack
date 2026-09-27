# Installer cstack : procédure pour un agent IA

Ce fichier s'adresse à un agent de code (Codex CLI ou Codex App) à qui l'utilisateur a demandé d'installer cstack. Suivez les étapes dans l'ordre et rapportez le résultat réel. Les humains trouveront la même installation, expliquée, dans le [README](README.md#installation).

## Règles

- Passez uniquement par `install.sh`. Il appelle `codex plugin` ; n'éditez jamais `~/.codex` ni le cache de plugins à la main.
- Ne lisez, n'affichez ni ne copiez aucun token ou credential. Si l'accès GitHub manque, demandez à l'utilisateur de se connecter.
- Demandez avant d'installer un prérequis global (Codex CLI, Python, Bun, `gh`).
- Les commandes ont besoin du réseau et d'écrire dans le dossier de Codex. Dans un bac à sable, demandez l'approbation prévue par Codex ; ne contournez pas les permissions.
- N'allez pas plus loin que l'installation : ne lancez pas `$cstack:setup-cstack` et ne choisissez aucun modèle à la place de l'utilisateur.

## Étapes

1. **Vérifier les prérequis.** `bash --version`, `codex --version`, `python3 --version` (3.9 ou plus récent) et `git --version` doivent réussir. Sous Windows, cstack s'installe depuis WSL, pas depuis PowerShell. S'il manque quelque chose, arrêtez-vous et dites à l'utilisateur quoi.

2. **Obtenir le script, hors du projet de l'utilisateur.** Travaillez dans un dossier temporaire pour ne laisser aucun fichier dans son dépôt :

   ```sh
   tmp="$(mktemp -d)"
   gh api repos/charlescstpierr/cstack/contents/install.sh -H "Accept: application/vnd.github.raw" > "$tmp/install.sh"
   ```

   Sans `gh` authentifié, clonez plutôt le dépôt privé avec Git : `git clone --depth 1 https://github.com/charlescstpierr/cstack.git "$tmp/cstack"`, puis utilisez `$tmp/cstack/install.sh`. Si vous êtes déjà dans un clone de `charlescstpierr/cstack`, `./install.sh` suffit. Dans la suite, `install.sh` désigne le script obtenu, lancé avec `bash`.

3. **Voir l'état actuel.** Lancez `install.sh doctor`.
   - La ligne du plugin commence par `✓ plugin cstack@cstack` : cstack est déjà installé et fonctionne. Ne changez rien. Lancez `install.sh update` seulement si l'utilisateur demande la dernière version.
   - Sinon, lancez `install.sh install`. N'ajoutez `--ref` que si l'utilisateur demande une version précise.

4. **Vérifier.** Relancez `install.sh doctor`. Le code de sortie doit être 0 et la ligne `✓ plugin cstack@cstack : installed, enabled <version>` doit apparaître.

5. **Conclure.** Supprimez le dossier temporaire (`rm -rf "$tmp"`) : l'installation n'en dépend pas. Donnez la version installée et dites à l'utilisateur d'ouvrir une **nouvelle tâche** Codex, puis de taper `$cstack:cstack`. La tâche en cours, y compris la vôtre, ne voit pas les compétences ajoutées.

## Lire les résultats

| Code de sortie | Sens |
| --- | --- |
| 0 | Réussite. Pour `doctor` : aucune ligne `✗`. |
| 1 | Échec. Le message qui commence par `cstack :` en donne la cause. |
| 2 | Commande ou option inconnue. Relisez la commande. |

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
| `cstack n'est pas installé` | Vous avez lancé `update` trop tôt : lancez `install.sh install`. |

Pour tout autre échec, montrez le message tel quel à l'utilisateur. Le script annule lui-même un changement de source raté et conserve l'installation précédente.

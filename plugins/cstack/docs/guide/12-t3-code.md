# Installer cstack dans T3 Code

T3 Code lance Codex et Claude sur la machine de votre environnement T3. cstack s'installe dans Codex et dans Claude Code sur cette machine, puis s'invoque dans un fil Codex ou Claude de T3 Code. Votre téléphone ou votre navigateur n'ont rien à installer.

## Avant de commencer

Vérifiez ces points sur la machine qui exécute vos agents T3 :

- Le fournisseur Codex ou Claude est connecté dans T3 Code.
- Codex CLI ou Claude Code est installé, et `codex --version` ou `claude --version` répond dans un terminal de cette machine. L'installateur installe cstack dans chacun de ceux qui répondent, même si T3 Code embarque son propre Codex.
- `git` et `curl` joignent GitHub.
- Python 3.9 ou plus récent et Bash sont présents.

Le second fournisseur est facultatif. Connectez Claude dans T3 Code si vous voulez des fils ou des délégués Claude.

## 1. Installer le plugin

Lancez cette commande dans un terminal de la machine T3 :

```sh
curl -fsSL https://raw.githubusercontent.com/charlescstpierr/cstack/main/install.sh -o install-cstack.sh && bash install-cstack.sh install
```

Cette commande exécute le script de la branche `main` avec vos droits. Pour le lire avant, lancez d'abord la partie `curl`, ouvrez `install-cstack.sh`, puis lancez `bash install-cstack.sh install`.

Puis vérifiez l'installation :

```sh
bash install-cstack.sh doctor
```

La sortie doit contenir la ligne `✓ plugin cstack@cstack : installed, enabled` pour Codex, et `✓ plugin cstack@cstack dans Claude Code : installed, enabled` pour Claude Code, chacune suivie de la version.

Si votre T3 Code utilise un autre dossier Codex que `~/.codex`, ou un autre dossier Claude que `~/.claude`, lancez les deux commandes avec la même variable `CODEX_HOME` ou `CLAUDE_CONFIG_DIR`.

Pour laisser un agent faire l'installation, collez ce message dans un fil T3 Code. Le fil s'exécute sur la machine T3, donc le plugin arrive au bon endroit :

```text
Installe le plugin cstack. Lis d'abord sa procédure pour agents à l'adresse https://raw.githubusercontent.com/charlescstpierr/cstack/main/INSTALL-AGENT.md, puis suis-la.
```

## 2. Approuver le rappel du mode

Cette étape est facultative et se fait une seule fois. Dans un terminal de la même machine, lancez `codex`, tapez `/hooks`, puis approuvez les deux hooks cstack. Si vous avez installé avec une variable `CODEX_HOME`, lancez `codex` avec la même variable. Sans cette approbation, cstack fonctionne, mais il ne rappelle pas son mode à chaque message. Une mise à jour qui change la commande du hook redemande cette approbation. Claude Code n'a rien à approuver.

## 3. Lancer une première tâche

1. Ouvrez un **nouveau fil** dans T3 Code avec le fournisseur Codex ou Claude. Un fil ouvert avant l'installation ne voit pas le plugin.
2. Commencez votre message par `$cstack:cstack` dans un fil Codex, ou par `/cstack:cstack` dans un fil Claude, puis écrivez la demande :

   ```text
   $cstack:cstack Explique en lecture seule comment ce projet lance ses tests.
   ```

3. cstack annonce une ligne `Playbook : <nom>` et une liste d'étapes. Si elles n'apparaissent pas, consultez le [dépannage](#dépannage).

Le coordinateur peut être un fil Codex ou un fil Claude. Les deux fournisseurs peuvent aussi intervenir comme délégués.

### Démarrer cstack sans commande

Ce réglage est éteint par défaut. Pour l'activer, demandez-le une fois dans un fil :

```text
$cstack:setup-cstack Active le démarrage automatique.
```

Dans chaque nouvelle session de cette machine, cstack s'applique alors de lui-même aux tâches qui touchent plusieurs fichiers, demandent un choix de conception ou portent sur un bug de cause inconnue. Une question ou une petite édition reste hors cstack. « arrête cstack » l'éteint pour une conversation. Pour l'éteindre sur la machine, demandez au setup de désactiver le démarrage automatique.

Le réglage dépend du hook de l'étape 2. Dans Codex, il ne s'applique pas tant que ce hook n'est pas approuvé. Si un autre plugin démarre aussi de lui-même sur les mêmes tâches, comme pstack, éteignez l'un des deux : sinon chaque session reçoit deux consignes concurrentes.

## 4. Écrire du code depuis un worktree

Pour une tâche qui modifie du code, créez le fil dans un worktree T3 Code. Le [contrat T3](../../skills/cstack/references/runtime/t3.md) interdit au coordinateur d'écrire à la racine du projet. Un fil créé sans worktree peut explorer et relire. Il confie alors chaque écriture à un délégué que T3 isole dans son propre worktree.

## 5. Choisir les modèles des délégués

Faites cette étape une fois par machine. Sans elle, chaque délégué reprend le fournisseur, le modèle et les options de votre fil : si votre fil tourne sur un modèle coûteux, ses délégués aussi.

Pour choisir, lancez le setup dans un fil T3 Code, avec `$cstack:setup-cstack` dans un fil Codex ou `/cstack:setup-cstack` dans un fil Claude :

```text
$cstack:setup-cstack Propose-moi les modèles des délégués.
```

Le setup propose une feuille en trois paliers, vérifiée sur les modèles que votre T3 Code expose :

| Palier | Modèle proposé | Emploi |
| --- | --- | --- |
| `work` | `gpt-6.1-sol` | Développement, débogage, exploration. |
| `judgment` | `claude-opus-5-5` | Jugement et prose. |
| `hard` | `gpt-6-astra` | Tâches les plus dures. |

Les panels de candidats et de reviewers prennent une position par palier, donc deux familles de modèles quand Codex et Claude sont connectés. Si un modèle proposé manque chez vous, le setup le dit et ne le remplace pas à votre place. Rien n'est écrit avant votre accord. Les choix acceptés vont dans la feuille de la machine, `~/.config/cstack/models.json`. Tous vos projets et worktrees la lisent dans T3 Code. Un `.cstack/models.json` dans un projet prime, rôle par rôle, pour un choix propre à ce projet.

Pour utiliser un autre modèle, y compris un modèle que T3 Code vient d'ajouter, nommez-le avec son palier :

```text
$cstack:setup-cstack Mets gpt-6.1-terra pour le travail courant.
```

Le setup accepte tout modèle que votre T3 Code expose. Les noms de cette page datent du 9 novembre 2026.

## 6. Mettre à jour

```sh
bash install-cstack.sh update
```

Si vous avez installé avec une variable `CODEX_HOME`, lancez cette commande avec la même variable. Ouvrez ensuite un nouveau fil. Un fil déjà ouvert garde l'ancienne version.

## Dépannage

| Symptôme | Action |
| --- | --- |
| `$cstack:cstack` ou `/cstack:cstack` ne déclenche rien | Lancez `bash install-cstack.sh doctor` sur la machine T3, puis ouvrez un nouveau fil. Le plugin est peut-être installé dans un autre dossier Codex ou Claude. |
| Aucun rappel « Mode cstack actif » | Approuvez les hooks à l'étape 2, puis retapez `$cstack:cstack` dans le fil. |
| Un seul agent travaille | Ajoutez la demande à votre message : « Délègue le travail indépendant à des sous-agents en parallèle. » Voir [Un seul agent travaille](./10-recipes-and-pitfalls.md#un-seul-agent-travaille). |
| Un délégué Claude est refusé | Connectez le fournisseur Claude dans T3 Code, puis relancez la demande. |
| Le coordinateur refuse d'écrire | Le fil n'est pas dans un worktree. Recréez-le dans un worktree, ou laissez-le déléguer l'écriture. |

## Ce qui est vérifié

- Le plugin installé se charge dans un fil Codex de T3 Code, et le rappel du mode s'affiche. Le reçu est `docs/evidence/t3-installed-plugin-2026-11-09.json`, à la racine du dépôt.
- L'installateur fonctionne dans des dossiers Codex et Claude Code isolés, avec `install --local` puis `doctor`, et depuis GitHub avec `install --ref`.
- Claude Code 2.1.321 charge le plugin installé, ses 29 compétences et son hook ; `/cstack:cstack` active le rappel du mode. Un fil Claude de T3 Code qui charge cstack n'est pas observé.
- Les helpers du setup T3 acceptent les vraies réponses de T3 Code et résolvent un panel sur deux fournisseurs. Le reçu est `docs/evidence/setup-observations-2026-11-09.json`. Un setup complet mené par un coordinateur Codex dans T3 Code n'est pas observé.
- Avec les règles du chemin direct, GPT-6.1 Sol prévoit 7 à 8 étapes avant de lancer un reviewer Claude, contre 15 à 16 avec les règles précédentes, sur deux essais par version. Dans un worktree sans `.cstack/`, il lit la feuille de la machine et lance chaque délégué sur le modèle de son rôle. Le reçu est `docs/evidence/t3-direct-path-2026-11-09.json`. Ce sont des exercices sur papier : un coordinateur Codex qui exécute ce chemin dans T3 Code n'est pas observé.
- Avec le démarrage automatique activé, GPT-6.1 Sol et Claude Sonnet appliquent cstack à un bug de cause inconnue et travaillent directement pour un renommage d'une ligne et pour une question. Sans le réglage, GPT-6.1 Sol n'applique cstack à aucune des trois demandes. Le reçu est `docs/evidence/automatic-start-2026-11-10.json`. C'est un exercice sur papier : une session de T3 Code qui démarre cstack par le hook installé n'est pas observée.

Ces observations viennent d'un seul serveur Linux. L'application de bureau T3 Code sur macOS et sur Windows n'est pas observée. L'approbation des hooks depuis T3 Code non plus. Le refus d'écrire hors worktree vient du contrat T3 et n'a pas été observé.

Précédent : [utiliser Codex et Claude ensemble](./11-cli-workers.md).

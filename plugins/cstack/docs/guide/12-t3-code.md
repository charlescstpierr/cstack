# Installer cstack dans T3 Code

T3 Code lance Codex sur la machine de votre environnement T3. cstack s'installe dans Codex sur cette machine, puis s'invoque dans un fil Codex de T3 Code. Votre téléphone ou votre navigateur n'ont rien à installer.

## Avant de commencer

Vérifiez ces points sur la machine qui exécute vos agents T3 :

- Le fournisseur Codex est connecté dans T3 Code.
- Codex CLI est installé, et `codex --version` répond dans un terminal de cette machine. L'installateur en a besoin, même si T3 Code embarque son propre Codex.
- `git` et `curl` joignent GitHub.
- Python 3.9 ou plus récent et Bash sont présents.

Le fournisseur Claude est facultatif. Connectez-le dans T3 Code si vous voulez des délégués Claude.

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

La sortie doit contenir la ligne `✓ plugin cstack@cstack : installed, enabled`, suivie de la version.

Si votre T3 Code utilise un autre dossier Codex que `~/.codex`, lancez les deux commandes avec la même variable `CODEX_HOME`.

Pour laisser un agent faire l'installation, collez ce message dans un fil T3 Code. Le fil s'exécute sur la machine T3, donc le plugin arrive au bon endroit :

```text
Installe le plugin cstack. Lis d'abord sa procédure pour agents à l'adresse https://raw.githubusercontent.com/charlescstpierr/cstack/main/INSTALL-AGENT.md, puis suis-la.
```

## 2. Approuver le rappel du mode

Cette étape est facultative et se fait une seule fois. Dans un terminal de la même machine, lancez `codex`, tapez `/hooks`, puis approuvez les deux hooks cstack. Si vous avez installé avec une variable `CODEX_HOME`, lancez `codex` avec la même variable. Sans cette approbation, cstack fonctionne, mais il ne rappelle pas son mode à chaque message.

## 3. Lancer une première tâche

1. Ouvrez un **nouveau fil** dans T3 Code avec le fournisseur Codex. Un fil ouvert avant l'installation ne voit pas le plugin.
2. Commencez votre message par `$cstack:cstack`, puis écrivez la demande :

   ```text
   $cstack:cstack Explique en lecture seule comment ce projet lance ses tests.
   ```

3. cstack annonce une ligne `Playbook : <nom>` et une liste d'étapes. Si elles n'apparaissent pas, consultez le [dépannage](#dépannage).

Un fil Claude ne charge pas les compétences `$cstack:*`. Le coordinateur est un fil Codex. Les modèles Claude interviennent comme délégués.

## 4. Écrire du code depuis un worktree

Pour une tâche qui modifie du code, créez le fil dans un worktree T3 Code. Le [contrat T3](../../skills/cstack/references/runtime/t3.md) interdit au coordinateur d'écrire à la racine du projet. Un fil créé sans worktree peut explorer et relire. Il confie alors chaque écriture à un délégué que T3 isole dans son propre worktree.

## 5. Choisir les modèles des délégués

Cette étape est facultative. Sans configuration, chaque délégué reprend le fournisseur, le modèle et les options de votre fil.

Pour choisir, lancez le setup dans un fil Codex de T3 Code et nommez vos sélections :

```text
$cstack:setup-cstack Mets le rôle « interrogate reviewers » sur trois positions : Codex gpt-6.1-sol en effort high, Claude claude-opus-5-5 en effort high, Codex gpt-6-astra en effort high.
```

Dans T3 Code, le setup ne propose aucun modèle. Il affiche les fournisseurs, les modèles et les options que T3 expose, puis il enregistre vos choix dans `.cstack/models.json` :

```json
{
  "interrogate reviewers": [
    {"runtime": "t3", "providerInstanceId": "codex", "model": "<modèle>", "options": {"reasoningEffort": "high"}},
    {"runtime": "t3", "providerInstanceId": "claudeAgent", "model": "<modèle>", "options": {"effort": "high"}}
  ]
}
```

Les identifiants de fournisseur, de modèle et d'option sont ceux que votre T3 Code affiche. Les noms de l'exemple datent du 9 novembre 2026. Un rôle enregistré avec `runtime: "t3"` reste bloqué hors de T3 Code.

## 6. Mettre à jour

```sh
bash install-cstack.sh update
```

Si vous avez installé avec une variable `CODEX_HOME`, lancez cette commande avec la même variable. Ouvrez ensuite un nouveau fil. Un fil déjà ouvert garde l'ancienne version.

## Dépannage

| Symptôme | Action |
| --- | --- |
| `$cstack:cstack` ne déclenche rien | Lancez `bash install-cstack.sh doctor` sur la machine T3, puis ouvrez un nouveau fil Codex. Le plugin est peut-être installé dans un autre dossier Codex. |
| Aucun rappel « Mode cstack actif » | Approuvez les hooks à l'étape 2, puis retapez `$cstack:cstack` dans le fil. |
| Un seul agent travaille | Ajoutez la demande à votre message : « Délègue le travail indépendant à des sous-agents en parallèle. » Voir [Un seul agent travaille](./10-recipes-and-pitfalls.md#un-seul-agent-travaille). |
| Un délégué Claude est refusé | Connectez le fournisseur Claude dans T3 Code, puis relancez la demande. |
| Le coordinateur refuse d'écrire | Le fil n'est pas dans un worktree. Recréez-le dans un worktree, ou laissez-le déléguer l'écriture. |

## Ce qui est vérifié

- Le plugin installé se charge dans un fil Codex de T3 Code, et le rappel du mode s'affiche. Le reçu est `docs/evidence/t3-installed-plugin-2026-11-09.json`, à la racine du dépôt.
- L'installateur fonctionne dans un dossier Codex isolé, avec `install --local` puis `doctor`.
- Les helpers du setup T3 acceptent les vraies réponses de T3 Code et résolvent un panel sur deux fournisseurs. Le reçu est `docs/evidence/setup-observations-2026-11-09.json`. Un setup complet mené par un coordinateur Codex dans T3 Code n'est pas observé.

Ces observations viennent d'un seul serveur Linux. L'application de bureau T3 Code sur macOS et sur Windows n'est pas observée. L'approbation des hooks depuis T3 Code non plus. Le refus d'écrire hors worktree vient du contrat T3 et n'a pas été observé.

Précédent : [utiliser Codex et Claude ensemble](./11-cli-workers.md).

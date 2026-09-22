# Utiliser Codex et Claude ensemble

Configurez un panel pour faire travailler Codex CLI et Claude Code dans un même workflow CStack. Le coordinateur reste dans Codex App ou CLI. Les workers externes sont des processus CLI, pas des sous-agents affichés comme des threads natifs dans Codex.

## Préparer les CLI

Installez les CLI officiels `codex` et `claude` sur le même hôte POSIX, puis connectez chaque CLI avec son mécanisme officiel. CStack conserve ces connexions sous le contrôle de chaque CLI. Il ne demande pas de copier un token, un cookie ou un fichier secret.

Vérifiez les versions depuis le terminal utilisé par Codex :

```sh
codex --version
claude --version
```

Une version affichée confirme la présence du CLI, pas la validité de son login ni le quota restant. Le premier dispatch réel peut encore être refusé. Le runner ne lance pas de login interactif ni de bascule automatique vers un autre fournisseur.

## Configurer un panel mixte

Le setup détecte d’abord les CLI disponibles et compare leurs capacités aux sélections du projet. Il vérifie la connexion par les commandes officielles de statut quand elles existent. Il propose ensuite les choix compatibles ; un statut inconnu reste indiqué.

Demandez au setup de préserver les autres choix du projet :

```text
$cstack:setup-cstack Configure arena runners, architect runners et interrogate reviewers avec deux entrées : codex-cli et claude-code. Garde les modèles par défaut de chaque CLI et les autres réglages existants.
```

Pour Arena seulement, les entrées correspondantes dans `.cstack/models.json` sont :

```json
{
	"arena runners": [
		{"runtime": "codex-cli"},
		{"runtime": "claude-code"}
	]
}
```

Ajoutez cette clé à votre fichier existant sans remplacer les autres rôles. Sans `runtime`, la sélection reste native Codex. Sans `model`, chaque CLI utilise son propre défaut. Un modèle explicite doit être validé dans le catalogue de son runtime ; `reasoning_effort` exige aussi un modèle explicite. Consultez le [contrat des workers](../../skills/cstack/references/runtime-workers.md) pour les autres formes de sélection.

## Ajouter Claude après la première configuration

Relancez le setup depuis le projet concerné :

```text
$cstack:setup-cstack Ajoute Claude Code aux panels Arena, Architect et Interrogate existants. Préserve leurs autres membres et les rôles non concernés. Utilise le modèle par défaut de Claude.
```

Pour un rôle simple, demandez le remplacement voulu, par exemple `Utilise Claude Code pour swarm workers et bug-fix`. Les autres rôles restent inchangés. Répéter l'ajout ne crée pas de doublon identique dans les panels.

`claude -p` désigne le mode non interactif de Claude Code. Le setup enregistre `claude-code` et le runner choisit ses arguments. La sonde du setup vérifie la présence et les capacités du CLI, sans génération ni lecture des credentials. La sauvegarde de la configuration ne prouve pas que le compte pourra exécuter la tâche.

Les nouvelles délégations prennent les réglages du projet sans réinstaller CStack. Pour mettre à jour les fichiers du plugin, suivez plutôt la [mise à jour du plugin](./01-setup.md#mettre-à-jour-le-plugin).

## Lancer le workflow

Donnez la tâche, le périmètre et la preuve attendue :

```text
$cstack:arena Utilise le panel CLI configuré pour corriger ce défaut. Chaque candidat travaille dans un worktree distinct. Fournis les mêmes skills et le même contexte aux deux candidats, puis fais vérifier les résultats par un juge indépendant avant la synthèse. Aucun push ni merge.
```

Le coordinateur prépare les briefs, sélectionne les skills, lance les CLI et vérifie les résultats. Le nombre total de candidats reste celui du panel ; une limite de concurrence impose des vagues supplémentaires. Pour Architect, `architect runners` prend priorité sur le panel Arena. `swarm workers` est un rôle à sélection unique ; pour répartir un Swarm entre plusieurs CLI, fournissez explicitement la sélection de chaque tranche au coordinateur.

## Partager les skills et le contexte

Le coordinateur transmet les skills utiles à la tâche depuis une source CStack commune. Il inclut leurs références Markdown locales et peut sélectionner une référence spécialisée avec `skill_references`. Aucun plugin CStack séparé n'est requis dans Claude Code. Les scripts cités par un skill ne deviennent pas automatiquement des outils exécutables du worker.

Les fichiers `context_files` contiennent les décisions, interfaces et rapports utiles aux tâches dépendantes. Après vérification, le coordinateur transmet les nouveaux faits à la tentative suivante. Ce partage utilise des snapshots par tâche ; il ne synchronise pas les conversations privées en temps réel.

Pour comparer deux candidats, le coordinateur vérifie les empreintes `skills.sha256` et `context.sha256` des reçus. Des axes de revue distincts peuvent avoir des briefs distincts ; leurs faits communs doivent rester cohérents.

## Lire les résultats et les limites

Chaque tentative conserve `result.json`, les snapshots de skills et de contexte, ainsi que stdout et stderr dans le dossier de tâche. `execution.status` indique le résultat du processus ; `worker.status` est le verdict déclaré par le worker. Un worker `PASS` ne suffit pas à inscrire une vérification indépendante au ledger.

Les essais connectés ont couvert Codex CLI et Claude Code. Le profil Claude expose les outils de fichiers ; le coordinateur exécute les commandes VERIFY et renvoie leurs erreurs au worker. Orchestrate a été vérifié jusqu'à la persistance locale et au contrôle du SHA, sans cycle GitHub complet.

Grok et Cursor sont sélectionnables, mais leur validation connectée reste reportée. Cursor est limité à la lecture seule. Windows est refusé par le runner actuel. La [campagne de vérification du dépôt](https://github.com/charlescstpierr/cstack/blob/main/docs/VERIFICATION.md) précise les versions, scénarios et limites.

Pour diagnostiquer un CLI absent, une sortie invalide ou une annulation, consultez le [contrat des workers CLI](../../skills/cstack/references/runtime-workers.md). N'utilisez pas un verdict antérieur pour masquer une tentative échouée.

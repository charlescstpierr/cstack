# Inventaire de la machine et des catalogues

Après invocation dans T3, le [contrat T3](../../cstack/references/runtime/t3.md) prime pour catalogue, choix explicites et synchronisation. Le chemin T3 modèle seul utilise `models.py --host t3 --capabilities <sortie de orchestrator_capabilities>`, sans conversion automatique ni CLI de repli.


Référence de [setup-cstack](../SKILL.md). Fais cet inventaire avant de proposer des runtimes, y compris lors d’un setup sans précision.

## Sonder les runtimes

Compare les choix du projet à l'environnement du processus Codex courant. Utilise le helper installé de confiance pour sonder chacun des runtimes `codex-cli`, `claude-code`, `cursor-agent` et `grok` avec `runtime/runtime.ts probe <runtime>` via le lanceur. Ces sondes inspectent le PATH, la version et les options du CLI sans génération. Réutilise les sondes récentes de la tâche si l'environnement n'a pas changé. Une demande limitée à un seul runtime peut limiter l'inventaire à celui-ci.

## Statut de connexion

Pour les binaires présents, vérifie la connexion uniquement par une commande de statut officielle reconnue par leur aide. Codex expose `codex login status` ; Claude expose `claude auth status --json`. Garde seulement l'état connecté/non connecté/inconnu et, si utile, le mode de connexion déclaré. Ne reproduis pas l'adresse courriel, les identifiants de compte ni la sortie brute. Pour un autre CLI ou une version sans statut reconnu, indique « connexion inconnue ». Borne les commandes de statut à 15 secondes et traite un timeout comme inconnu. Ne lance pas de login, de génération, de recherche dans les credentials, les sessions privées ou les variables secrètes.

## Présenter l'inventaire

Présente un tableau runtime, présence/version, connexion, capacité de permissions et rôles déjà configurés. Le chemin natif Codex reste un choix distinct hérité de la session. Un binaire présent sans headless ou permissions compatibles n'est pas prêt au dispatch. La connexion déclarée ne prouve ni quota, ni modèle disponible, ni comportement de bout en bout.

Propose les choix d'après cet inventaire : conserver les réglages existants, ajouter un CLI disponible aux panels choisis, remplacer des rôles choisis, ou configurer explicitement un CLI pour plus tard. Signale les sélections sauvegardées devenues indisponibles et préserve-les tant qu'aucun remplacement n'est demandé. Ne propose pas les recommandations OpenAI pour Claude. Si le CLI ne publie pas de catalogue exploitable sans génération, propose son modèle par défaut et indique que ses modèles/efforts explicites restent non vérifiés. Ne présente pas Grok ou Cursor comme testés en connexion sur la seule foi d'une sonde.

## Découvrir modèles et efforts

Découvre ensuite les modèles et efforts depuis le schéma d'outil natif courant ou le catalogue de session faisant autorité. Pour une CLI prise en charge, le JSON brut de `codex debug models` fonctionne; sinon, utilise une carte de slugs confirmés vers listes d'efforts depuis le schéma réel. Un cache périmé n'est pas une preuve de disponibilité. Sans découverte, l'héritage reste disponible. Vérifie si le dispatch natif peut exprimer les deux champs sélectionnés, avec des rôles génériques et des réglages de fork pris en charge.

Les formats de catalogue acceptés sont décrits dans [modèles](models.md#catalogues-et-sélections-cli).

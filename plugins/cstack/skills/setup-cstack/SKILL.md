---
name: setup-cstack
description: "À utiliser pour $cstack:setup-cstack ou les changements de configuration cstack. Guide la configuration de projet cstack : préserve les consignes de projet, configure ou met à jour les runtimes, un budget de raisonnement et les choix facultatifs de modèle/effort, et explique les workflows de préparation."
---

Après invocation explicite dans T3, lire d’abord le [contrat T3](../cstack/references/runtime/t3.md). Il prime sur les consignes Codex autonome ci-dessous pour modèles, délégation, isolation, checkpoints, PR et nettoyage, sous les instructions du harnais. Hors T3, conserver le contrat Codex.


# Configurer cstack

L'usage de base de cstack n'exige aucune configuration. La configuration prépare seulement le projet courant; elle n'active jamais un flux de travail et ne change jamais la configuration globale de Codex ou de Claude Code. Dans T3, les choix de modèles acceptés vont dans la feuille cstack de la machine (`$XDG_CONFIG_HOME/cstack/models.json`, par défaut `~/.config/cstack/models.json`), que tous les projets et worktrees lisent.

Runtime : [règles communes](../cstack/references/runtime/base.md), [exploration](../cstack/references/runtime/exploration.md), [modèles](../cstack/references/runtime/modeles.md).

## Portée

Respecte la portée demandée. Une demande de changement de modèles utilise seulement les commandes modèle seules. La configuration générale propose aussi les consignes de projet et conventions de tracker. Une demande de preview, lecture seule, annulation ou mode Plan n'écrit rien dans le projet; garde les choix proposés dans la conversation ou dans un artefact temporaire autorisé.

Avant la première inspection, affiche une todo courte adaptée au périmètre : découverte, choix, prévisualisation, application et vérification ([suivi du setup](references/project-apply.md#suivi-des-étapes)).

## Étapes

1. **Découvrir.** Localise le workspace cible, normalement sa racine Git ou le répertoire courant hors Git. Lis les `AGENTS.md`, `CLAUDE.md`, `docs/agents/cstack.md`, `docs/agents/issue-tracker.md`, conventions de domaine et `.cstack/models.json` existants quand ils sont présents. Inspecte seulement les fichiers de projet pertinents. Résous le chemin absolu de ce bundle installé. Fais l'[inventaire](references/inventory.md) des runtimes, connexions et catalogues de modèles/efforts avant de proposer des runtimes. Dans T3, l'inventaire se limite à la sortie de `orchestrator_capabilities`, enregistrée telle quelle pour `--capabilities` : ne sonde pas les CLI, leurs positions y sont bloquées.
2. **Proposer.** Exécute `show` ([commandes](references/project-apply.md#configuration-modèle-seule) ; [modèles, rôles et recommandations](references/models.md)). Demande d'abord un [budget de raisonnement](references/models.md#budget-de-raisonnement), puis commence la présentation des modèles par un tableau « Propositions de modèles d’agents » qui montre chaque rôle, chaque position de panel, le modèle/effort recommandé vérifié et sa raison. Pour Claude Code ou un autre CLI, suis d'abord [Claude Code](references/claude-code.md). Pour la préparation de projet, explique les flux de préparation et propose le bloc `AGENTS.md`, les agents natifs et le tracker ([préparation](references/project-apply.md)). Dans T3, `show` rend une [feuille en trois paliers](references/models.md#dans-t3) vérifiée sur le catalogue observé, panels mixtes compris. Présente-la en clair, groupe par groupe, avec l'héritage du coordinateur et les autres modèles exposés (`supported`), et ne pose la question du budget que si l'utilisateur parle de coût. Un groupe `unavailable` n'est jamais remplacé d'office : dis lequel et pourquoi. Quand l'utilisateur nomme un autre modèle, nouveau ou non, relance `show --tier <palier>=[fournisseur/]<modèle>[@effort]` au lieu de réécrire les rôles un par un.
3. **Montrer l'actuel.** Seulement après ces propositions, affiche la configuration actuelle. Ne commence jamais la réponse par « les agents héritent du parent » quand le catalogue permet de proposer des modèles.
4. **Appliquer avec empreinte.** `project.py apply` reçoit la prévisualisation exacte acceptée et son `plan_sha256` ; `models.py apply` reçoit l'empreinte relue de `show` ([commandes](references/project-apply.md#configuration-modèle-seule)). Dans T3, `models.py apply --machine` reçoit l'empreinte `machine.sha256` de `show` ; écris dans `.cstack/models.json` seulement quand l'utilisateur veut un choix propre à ce projet. Ne reconstruis jamais un plan à la main. Une prévisualisation périmée ou conflictuelle est rejetée et refaite ; un résultat `partial` suit la [reprise](references/project-apply.md#écriture-partielle).
5. **Relire et vérifier.** Lis les vrais fichiers générés, résous les rôles modifiés et rapporte les réglages effectifs et quand ils prennent effet ([vérification](references/project-apply.md#relire-et-vérifier)).

## Acceptation explicite

- Applique les choix déjà explicitement demandés sans redemander; invoquer simplement setup n'accepte pas les recommandations.
- Écris chaque choix demandé et ses options en clair dans ta réponse, même quand tu utilises l'entrée structurée : ne termine pas un tour sur « j'attends ton choix » sans les options sous les yeux de l'utilisateur.
- Quand l'utilisateur a déjà approuvé ces changements exacts, procède sans autre relais de permission ; une demande précise ne nécessite pas une seconde confirmation.
- Applique la proposition `mixed review panels` et une cible GitHub seulement après leur sélection. Préserve les rôles non sélectionnés et les sélections sauvegardées devenues indisponibles tant qu'aucun remplacement n'est demandé.
- Construis options et choix seulement depuis les réglages acceptés ; les valeurs de modèle sont des sélections vérifiées, pas des défauts inconditionnels.

## Démarrage automatique

Sur demande de l'utilisateur seulement, `python3 <absolute-plugin>/hooks/mode.py auto on` fait démarrer cstack de lui-même au début de chaque session de cette machine, pour les tâches qui touchent plusieurs fichiers, demandent un choix de conception ou portent sur un bug de cause inconnue. `auto off` l'éteint et `auto status` dit l'état. Le réglage est le fichier `$XDG_CONFIG_HOME/cstack/auto-start`, par défaut `~/.config/cstack/auto-start`. Ne l'active jamais de ta propre initiative. Dis à l'utilisateur qu'il vaut pour les nouvelles sessions, Codex et Claude, et qu'il dépend du hook cstack : Codex redemande son approbation (`/hooks`) après une mise à jour qui le change.

## Jamais

- Lire les identifiants secrets, chercher dans les credentials, sessions privées ou variables secrètes, ou copier un credential.
- Lancer un login, une génération, `claude -p`, des sondes payantes de modèle ou des travaux de test payants.
- Écrire la configuration globale de Codex ou de Claude Code, ou `~/.codex` ; les seuls agents écrits sont les agents projet acceptés dans `.codex/agents/`.
- Modifier le cache de plugin installé ou exécuter une copie du helper locale au projet.
- Créer des étiquettes, tickets ou état distant, des objectifs natifs, un `CONTEXT.md` vide ou des répertoires ADR.
- Remplacer un contenu non géré, un bloc mal formé ou un agent sans `# cstack:managed` : ce sont des conflits à expliquer.
- Rapporter un succès depuis une sortie échouée ou partielle, ou affirmer qu'un modèle a été exécuté.

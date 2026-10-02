---
name: setup-cstack
description: "À utiliser pour $cstack:setup-cstack ou les changements de configuration cstack. Guide la configuration de projet cstack : préserve les consignes de projet, configure ou met à jour les runtimes, un budget de raisonnement et les choix facultatifs de modèle/effort, et explique les workflows de préparation."
---

# Configurer cstack

L'usage de base de cstack n'exige aucune configuration. La configuration prépare seulement le projet courant; elle n'active jamais un flux de travail et ne change jamais la configuration globale.

Runtime : [règles communes](../cstack/references/runtime/base.md), [exploration](../cstack/references/runtime/exploration.md), [modèles](../cstack/references/runtime/modeles.md).

## Portée

Respecte la portée demandée. Une demande de changement de modèles utilise seulement les commandes modèle seules. La configuration générale propose aussi les consignes de projet et conventions de tracker. Une demande de preview, lecture seule, annulation ou mode Plan n'écrit rien dans le projet; garde les choix proposés dans la conversation ou dans un artefact temporaire autorisé.

Avant la première inspection, affiche une todo courte adaptée au périmètre : découverte, choix, prévisualisation, application et vérification ([suivi du setup](references/project-apply.md#suivi-des-étapes)).

## Étapes

1. **Découvrir.** Localise le workspace cible, normalement sa racine Git où le répertoire courant hors Git. Lis les `AGENTS.md`, `CLAUDE.md`, `docs/agents/cstack.md`, `docs/agents/issue-tracker.md`, conventions de domaine et `.cstack/models.json` existants quand ils sont presents. Inspecte seulement les fichiers de projet pertinents. Résous le chemin absolu de ce bundle installe. Fais l'[inventaire](references/inventory.md) des runtimes, connexions et catalogues de modèles/efforts avant de proposer des runtimes.
2. **Proposer.** Exécute `show` ([commandes](references/project-apply.md#configuration-modèle-seule) ; [modèles, rôles et recommandations](references/models.md)). Demande d'abord un [budget de raisonnement](references/models.md#budget-de-raisonnement), puis commence la présentation des modèles par un tableau « Propositions de modèles d’agents » qui montre chaque rôle, chaque position de panel, le modèle/effort recommandé vérifié et sa raison. Pour Claude Code ou un autre CLI, suis d'abord [Claude Code](references/claude-code.md). Pour la préparation de projet, explique les flux de préparation et propose le bloc `AGENTS.md`, les agents natifs et le tracker ([préparation](references/project-apply.md)).
3. **Montrer l'actuel.** Seulement après ces propositions, affiche la configuration actuelle. Ne commence jamais la réponse par « les agents héritent du parent » quand le catalogue permet de proposer des modèles.
4. **Appliquer avec empreinte.** `project.py apply` reçoit la prévisualisation exacte acceptée et son `plan_sha256` ; `models.py apply` reçoit l'empreinte relue de `show` ([commandes](references/project-apply.md#configuration-modèle-seule)). Ne reconstruis jamais un plan à la main. Une prévisualisation périmée ou conflictuelle est rejetée et refaite ; un résultat `partial` suit la [reprise](references/project-apply.md#écriture-partielle).
5. **Relire et vérifier.** Lis les vrais fichiers générés, résous les rôles modifiés et rapporte les réglages effectifs et quand ils prennent effet ([vérification](references/project-apply.md#relire-et-vérifier)).

## Acceptation explicite

- Applique les choix déjà explicitement demandés sans redemander; invoquer simplement setup n'accepte pas les recommandations.
- Quand l'utilisateur a déjà approuvé ces changements exacts, procède sans autre relais de permission ; une demande précise ne nécessite pas une seconde confirmation.
- Applique la proposition `mixed review panels` et une cible GitHub seulement après leur sélection. Préserve les rôles non sélectionnés et les sélections sauvegardées devenues indisponibles tant qu'aucun remplacement n'est demandé.
- Construis options et choix seulement depuis les réglages acceptés ; les valeurs de modèle sont des sélections vérifiées, pas des défauts inconditionnels.

## Jamais

- Lire les identifiants secrets, chercher dans les credentials, sessions privées ou variables secrètes, ou copier un credential.
- Lancer un login, une génération, `claude -p`, des sondes payantes de modèle ou des travaux de test payants.
- Écrire la configuration globale ou `~/.codex` ; les seuls agents écrits sont les agents projet acceptés dans `.codex/agents/`.
- Modifier le cache de plugin installé ou exécuter une copie du helper locale au projet.
- Créer des étiquettes, tickets ou état distant, des objectifs natifs, un `CONTEXT.md` vide ou des répertoires ADR.
- Remplacer un contenu non géré, un bloc mal formé ou un agent sans `# cstack:managed` : ce sont des conflits à expliquer.
- Rapporter un succès depuis une sortie échouée ou partielle, ou affirmer qu'un modèle a été exécuté.

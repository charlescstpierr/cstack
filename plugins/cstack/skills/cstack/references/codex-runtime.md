# Contrat d’exécution Codex natif

Index du contrat, pour une compétence cstack explicitement invoquée : chaque partie se lit au moment où sa situation se présente. Il s’applique à la tâche courante et à ses délégués, pas à chaque projet ni aux futures tâches. Les instructions utilisateur, l’AGENTS.md du projet, le mode Codex et les permissions d’outil priment. Cet index et ses parties sont la définition partagée du comportement d’exécution ; les fichiers compagnons ne doivent pas l’affaiblir.

Les [règles communes](runtime/base.md) valent toujours ; pour le reste, ouvre seulement la partie de la situation en cours.

## Parties

- [Règles communes](runtime/base.md) : précédence, données externes, capacité manquante, annonces de délégués, commits et état.
- [Activation et routage](runtime/activation.md) : invocation, sœurs et principes, bloc de setup passif, porte `clarify`, portée de livraison par défaut et worktree de tâche.
- [Suivi visible](runtime/suivi.md) : annonce du playbook, todo cochée en direct, annonce et preuves de chaque appel de délégué, relance unique.
- [Goal global](runtime/goal.md) : implémentation multi-phase avec demande explicite de Goal.
- [Exploration déléguée](runtime/exploration.md) : au moins deux explorateurs, normalement trois angles.
- [Délégation et dispatch](runtime/delegation.md) : délégué natif, agent `cstack-*`, reviewer séparé ; sélection avec `runtime` (worker CLI).
- [Orchestration requise](runtime/orchestration.md) : Swarm, Arena, revue indépendante, délégué bloqué, capacité manquante, JSON `BLOCKED`.
- [Modèles](runtime/modeles.md) : `.cstack/models.json` ou surcharge de modèle ou d’effort.
- [État et reprise](runtime/etat.md) : point de reprise, worktree temporaire, lanceur `run-tool.sh`, historique de tâches.
- [Commits locaux](runtime/commits.md) : avant chaque commit d’une unité vérifiée.
- [Intégrations externes](runtime/integrations.md) : connecteurs, vérification UI, action externe, merge et nettoyage de livraison.
- [Limites de plateforme](runtime/limites.md) : agents TOML, délégation qui ne part pas, descendants de délégués.

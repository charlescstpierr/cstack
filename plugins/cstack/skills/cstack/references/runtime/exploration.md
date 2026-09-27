# Exploration déléguée

Partie du [contrat d’exécution Codex](../codex-runtime.md), lue quand sa situation se présente.

Quand une exploration est déléguée, lance au minimum deux explorateurs, normalement trois sur des angles utiles distincts : fonctionnement, appelants/contrats, tests/risques par exemple. Cette règle vaut aussi pour une seule cible et pour les recherches Horizon. Un synthétiseur ou reviewer unique ne compte pas comme deuxième explorateur. Résous chaque appel avec le rôle configuré et conserve runtime, modèle et effort.

La limite de concurrence fixe la taille des vagues, pas le nombre total d'explorateurs. Attends les résultats de tous les angles avant de conclure. Une interdiction de délégation ou une capacité réellement absente suit [Orchestration requise](orchestration.md) ; elle ne devient pas une exception autorisant un seul explorateur. Les compétences qui permettent une inspection directe peuvent garder zéro délégué. N'invente pas d'angles pour une lecture mécanique qui reste dans le parent.

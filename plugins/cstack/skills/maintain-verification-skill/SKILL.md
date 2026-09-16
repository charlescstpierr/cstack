---
name: maintain-verification-skill
description: "Passe périodique qui garde fidèle la skill de vérification d'un projet et sa carte de fonctionnalités : lecteurs source parallèles par fonctionnalité, une session live pilotant chaque fonctionnalité, et un ensemble de corrections prouvées. Utiliser pour $cstack:maintain-verification-skill ou \"audite la skill de vérification\"."
---

# Maintenir une skill de vérification

Contrat d’exécution : [`../cstack/references/codex-runtime.md`](../cstack/references/codex-runtime.md).

Une carte de fonctionnalités pourrit des que l'app change. Cette skill est la boucle d'entretien d'une skill générée par `$cstack:create-verification-skill` (ou de toute skill de vérification locale au projet avec une carte de fonctionnalités). L'unité de rigueur est la fonctionnalité, pas chaque phrase : couvrir chaque fichier de fonctionnalité depuis la source et exercer chaque fonctionnalité en live, sans terminaliser chaque puce.

## Résultats

Choisis-en un, et dis lequel :

- **clean** — chaque fonctionnalité a reçu une couverture source et live; rien ne vaut d'être livré. Pas de branche, pas de PR.
- **changed** — un ensemble local de changements contient des corrections de doc, harnais ou carte prouvées. Ouvre une PR seulement quand l'utilisateur l'a demandée.
- **blocked** — la couverture n'a pas pu se terminer ou un correctif prouvé n'a pas pu être livré sans risque. Dis exactement ce qui a bloqué.

## Portée d'édition

Modifie seulement le répertoire propre de la skill de vérification (son SKILL.md, features/ et tous les scripts de harnais qu'elle possède). Ne modifie jamais le code produit pendant une exécution : un comportement décrit par la carte que l'app ne fait plus est soit une dérive documentaire (corrige la carte), soit une régression produit (signale-la, ne la masque pas dans les docs).

## Passe

0. **Localiser la cible.** Trouve la skill de vérification à maintenir : la skill locale au projet dont le corps a des sections launch/drive et une carte de fonctionnalités (habituellement `.agents/skills/verify-*/`). Plusieurs candidats exigent le choix de l'utilisateur; s'il n'y en a aucun, arrête et pointe vers `$cstack:create-verification-skill` au lieu d'inventer une cible.

1. **Hygiène d'index.** Lis le README de la carte de fonctionnalités et glob ses fichiers voisins. Corrige les entrées manquantes, supplémentaires, dupliquées ou mortes. Léger; pas d'inventaire généré.

2. **Vague source.** Des sous-agents en lecture seule, un par fichier de fonctionnalité, lancés en parallèle. Chacun explique "comment cette fonctionnalité visible par l'utilisateur fonctionne-t-elle?" depuis la source, signale les dérives documentaires probables avec citations et renvoie une recette concise de vérification live. Les enfants ne pilotent jamais l'app et ne modifient jamais de fichiers. Forme de retour : résumé de fonctionnalité / points d'entrée source / dérive probable ou aucune / une recette. La concurrence native limite le nombre d'exécutions simultanées. Mets les fonctionnalités restantes en file pour des vagues ultérieures. Si aucun emplacement de sous-agent n'est disponible, exécute chaque lecture de fonctionnalité dans la même session comme passe séparée et explicitement recadrée, étiquette le résultat `single-agent`, puis signale l'indépendance manquante. Ne laisse tomber aucune fonctionnalité.

3. **Reconcilier.** Chaque fichier de fonctionnalité a un résumé retourné. Fusionne les recettes qui se chevauchent en aussi peu d'états d'app que possible. Vérifie ponctuellement les dérives citées; ne reprouve pas les affirmations propres. Balaie le churn récent pour les surfaces visibles par l'utilisateur absentes de la carte — exige un chemin source concret avant d'en déclarer une manquante.

4. **Passe live.** Requise même quand la source semble propre. Le coordinateur possède tout le pilotage; suis le modèle de lancement propre à la skill de vérification : une instance longue durée pilotée en série pour les serveurs et UI, ou une session fraîche isolée par pilotage pour les CLI courte durée (la section Launch de la skill décide, pas celle-ci). Exerce chaque fonctionnalité au moins une fois, et maintiens trois invariants pendant toute la passe, quel que soit l'échec : (1) ne pilote jamais une instance que tu n'as pas vérifiée depuis sa dernière surprise — doctor avant le premier pilotage, doctor sur chaque session fraîche quand les sessions sont l'unité, doctor à nouveau après tout pilotage échoué, et quand doctor ne peut pas voir l'échec (état UI coincé sur un processus sain), réinitialise à un état connu ou relance au lieu d'espérer; (2) les preuves capturées jusque-là survivent à chaque nettoyage, vérifiées à leur emplacement nommé, pas supposées; (3) rien démarré par un pilotage ne survit à l'utilité de ce pilotage — les résidus d'itération échouée sont nettoyés que la session soit bloquée, sortie ou partagée (pour une instance partagée, nettoie le résidu, pas l'instance). Un échec doctor causé par une dérive de skill est une dérive : corrige-la dans la portée d'édition et réessaie une fois — redémarre ce que le correctif a invalidé, rien de plus — avant d'appeler la passe `blocked`. Une fonctionnalité inaccessible est `verified-unreachable` seulement avec le prérequis concret (auth, entitlement, OS, état externe) et la route tentée; si la carte omet ce prérequis, c'est une dérive. Tout correctif de harnais issu du triage est repiloté en live avant livraison. Le teardown final arrive après le dernier pilotage de l'exécution — y compris ces nouvelles preuves — afin que rien ne survive à l'exécution (les preuves restent, selon la skill).

5. **Triage.** Description point de vue utilisateur fausse ou manquante -> dérive documentaire, corrige-la. Comportement fonctionnel que le harnais ne peut pas piloter -> manque de harnais, corrige-le; un correctif de harnais suit la même règle de helpers que la génération (scripts exécutables, invocation documentée dans le corps de la skill). Comportement d'app vraiment cassé -> manque produit; consigne-le pour l'utilisateur, garde-le hors de cette PR.

6. **Finir ou arrêter.** Pour changed, relis chaque fichier modifié et rapporte les corrections locales prouvées. Ouvre une PR seulement dans la demande concrète de l'utilisateur. Pour clean ou blocked, rapporte honnêtement le résultat et la couverture.

Garde des notes d'exécution concises (fonctionnalités couvertes, prérequis inaccessibles, dérives confirmées, résultat) dans un emplacement scratch; ne les committe pas.

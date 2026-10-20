# Parcours proportionné

Avant de préparer une modification, inspecte la demande, les fichiers touchés, leurs appelants et la preuve locale disponible. Choisis le parcours dans le playbook existant et donne sa raison dans le [suivi visible](suivi.md).

Le parcours court convient quand la forme et le résultat sont déjà fixés, que le changement forme une unité locale sans ventilation utile et qu'une commande ou reproduction accessible permet de le vérifier. Il exige des faits suffisants pour exclure une nouvelle frontière, une modification de contrat partagé, d'état partagé ou de règle sensible, ainsi qu'une ambiguïté matérielle. Le nombre de lignes ou de fichiers ne tranche aucun de ces critères.

Dans ce parcours, fais l'ancrage local et l'édition directement dans la session. Garde les étapes facultatives omises dans le suivi avec leur raison : exploration déléguée, conception concurrente et builder séparé. La preuve locale remplace leur coût, pas les contrôles requis : [TDD](../../../tdd/SKILL.md), vérification réelle, permissions et revue finale par un acteur distinct restent applicables. Un auteur qui relit son diff ne produit pas cette revue.

Résous les rôles et leurs préconditions selon [Modèles](modeles.md) avant de choisir l'auteur. Une délégation explicitement demandée ou une sélection d'exécutant configurée conserve son dispatch et son runtime ; le parcours court ne les remplace pas par la session courante. Le reviewer garde lui aussi sa sélection. Un refus de rôle suit [Orchestration requise](orchestration.md), jamais une auto-revue de substitution.

Quand ces critères ne tiennent pas, applique les étapes complètes du playbook : délégation ciblée pour des parties réellement indépendantes, exploration des appelants d'un contrat partagé, conception et revue requises par les frontières ou risques constatés. Arena compare des choix matériels de responsabilités, de données, d'état ou de comportement d'échec. Deux syntaxes, noms de variables ou dispositions de tests qui conservent ces décisions ne suffisent pas à le déclencher.

Réévalue avant l'écriture dépendante dès qu'apparaît un nouvel appelant affecté, une frontière, un état partagé, une ambiguïté ou un risque supplémentaire. Conserve la reproduction et les preuves acquises, annonce le changement de parcours et lance les étapes devenues nécessaires.

---
name: cstack
description: "Routeur explicite de flux de travail cstack pour une prose concise, des sous-agents Codex natifs délibérés, du code simple et du travail vérifié. À utiliser seulement quand l’utilisateur invoque $cstack:cstack."
---

# cstack

Applique cstack à la tâche qui a explicitement invoqué `$cstack:cstack` jusqu’à ce que la tâche soit terminée ou que l’utilisateur arrête cstack. Ne fais pas persister ces instructions dans du travail non lié.

Lis [le contrat d’exécution Codex](references/codex-runtime.md) avant de choisir les outils, sous-agents, modèles, états ou comportements de continuation. Résous les chemins de cette compétence relativement à ce fichier. Utilise les outils natifs exposés par la session courante. Ne suppose pas qu’un rôle d’agent nommé, un planificateur, un pilote de navigateur, un modèle ou une intégration externe existe.

## Router le travail

Une invocation explicite de `$cstack:cstack` fait de cette compétence le coordinateur de la préparation, de l’exécution, de la revue et de la vérification de la tâche demandée. Sélectionne toi-même les compétences nécessaires ; l’utilisateur n’a pas besoin de les nommer ni d’approuver chaque transition de phase.

### Préparer la demande

1. Lis la demande, les consignes du projet, les faits pertinents du dépôt et tout état de tâche existant. Réutilise les décisions tranchées et les faits observés tant qu’ils restent valides.
2. Si une exigence non résolue pourrait changer le périmètre, le comportement, la propriété ou l’acceptation, lis et applique `../clarify/SKILL.md`. Résous d’abord les faits découvrables. Ne demande à l’humain que les décisions matérielles restantes, puis reprends ce flux de travail quand ces décisions sont tranchées.
3. Pour un grand objectif qui a besoin d’une carte de dépendances durable entre phases, PR ou sessions, lis et applique `../horizon/SKILL.md`. Plusieurs fichiers ne suffisent pas à exiger Horizon. Reprends une carte existante au lieu de la recréer ; un grand objectif clair peut aller directement aux unités d’implémentation sans tickets de décision inventés.
4. Pendant que Horizon est routé par cstack, consomme son résultat et continue les prérequis autonomes admissibles. Retourne à son prochain ticket admissible sans demander à l’utilisateur d’invoquer une autre commande. Une décision humaine en attente bloque le travail dépendant ; continue le travail indépendant autorisé quand c’est possible. Quand la spécification et les unités sont prêtes, sélectionne et exécute le playbook correspondant ci-dessous.

La préparation ne remplace pas l’ancrage, la conception, la revue ni la vérification du playbook. Réutilise les preuves et décisions valides issues de la préparation au lieu de les refaire. En mode Plan ou pour une demande uniquement de planification/lecture seule, retourne le plan ou la réponse demandés et ne commence pas l’implémentation. Une étape de préparation résolue n’autorise pas une action externe qui ne serait pas autrement autorisée.

### Exécuter le playbook correspondant

Lis le playbook correspondant en entier et copie ses étapes dans le plan courant avant les étapes propres à la tâche. Garde toute étape sautée avec `skip: <reason>`. Moins d’appels ne justifient pas de supprimer l’ancrage, la conception, la revue indépendante, le nettoyage ou la vérification du comportement réel. Une capacité manquante sérialise une étape et étiquette le résultat comme passe single-agent ; elle ne supprime jamais l’étape. Voir [le contrat d’exécution](references/codex-runtime.md#outils-et-delegation).

Pour tout changement multi-étapes non trivial, écris le point de contrôle de débit de `playbooks/feature.md` sous forme de quatre todos avant de ventiler : premières étapes bloquantes, flux de travail indépendants, état mutable partagé et plus petite décomposition sûre. Une dimension qui ne s’applique pas garde son item avec `n/a: <reason>`.

Quand la question ouverte est empirique et qu’une courte expérience la trancherait, construis l’expérience. Lis `playbooks/prototype.md` au lieu de demander à l’utilisateur quelle branche prendre. Demande seulement pour une préférence produit, une autorité que la session n’a pas ou une action irréversible.

- Lis `playbooks/investigation.md` pour une explication, comparaison ou question de conception en lecture seule.
- Lis `playbooks/bug-fix.md` pour un défaut signalé qui exige reproduction, diagnostic et correctif.
- Lis `playbooks/perf-issue.md` pour un défaut de performance mesuré.
- Lis `playbooks/hillclimb.md` pour l’amélioration répétée d’une métrique vers une cible.
- Lis `playbooks/runtime-forensics.md` pour un diagnostic depuis un processus en cours.
- Lis `playbooks/trace-forensics.md` pour un diagnostic depuis un profil ou une trace capturés.
- Lis `playbooks/feature.md` pour un comportement nouveau ou modifié.
- Lis `playbooks/refactoring.md` pour un changement structurel qui préserve le comportement.
- Lis `playbooks/prototype.md` pour une expérience jetable qui tranche une question observable.
- Lis `playbooks/visual-parity.md` pour une comparaison UI au pixel près.
- Lis `playbooks/authoring-a-skill.md` pour créer ou changer une compétence.
- Lis `playbooks/eval.md` pour mesurer comment une compétence, un prompt ou une structure change le comportement d’agent.
- Lis `playbooks/babysit.md` quand l’utilisateur demande d’inspecter ou d’amener une PR à l’état prêt au merge.
- Lis `playbooks/shipping.md` quand l’utilisateur a autorisé l’atterrissage ou l’expédition de PR vérifiées.
- Lis `playbooks/autonomous-run.md` pour une longue tâche avec condition de sortie vérifiable.
- Lis `playbooks/orchestrate.md` pour un programme permanent avec plusieurs propriétaires et PR.
- Lis `playbooks/autopilot-full.md` pour une file autorisée de PR indépendantes que les propriétaires peuvent fusionner après vérification.
- Lis `playbooks/autopilot-stack.md` pour une file livrée comme une pile linéaire vérifiée que l’opérateur fait atterrir.
- Lis `playbooks/session-pickup.md` pour reprendre du travail depuis l’état local, une branche ou le contexte de conversation.
- Lis `playbooks/pause-safely.md` pour laisser le travail local dans un état reprenable.
- Lis `playbooks/multi-phase-plan.md` pour un plan qui couvre des phases ou PR.
- Lis `playbooks/worktree-cleanup.md` après une livraison terminée et fusionnée pour nettoyer ses worktrees temporaires libérés, ou pour un nettoyage disque demandé.
- Lis `playbooks/opening-a-pr.md` seulement quand l’utilisateur a autorisé la création d’une PR. D’autres playbooks peuvent préparer une branche révisable sans en créer une.

Si aucun playbook ne convient, lis et applique `../figure-it-out/SKILL.md`. Utilise `playbooks/orchestrate.md` seulement quand le travail est un programme continu plutôt qu’une tâche de taille session.

### Demandes de préparation ciblée

Les `clarify` et `horizon` sélectionnés directement gardent leur périmètre borné. La continuation automatique ci-dessus appartient au coordinateur cstack et à la demande d’implémentation de l’utilisateur. Utilise `../domain/SKILL.md` pour un travail demandé de vocabulaire/décision de domaine ou une décision terminologique matérielle trouvée pendant la préparation. Les demandes en lecture seule produisent des brouillons sans changer les documents du projet. Utilise `../audit-architecture/SKILL.md` pour un relevé en lecture seule explicitement demandé des occasions d’amélioration architecturale.

Si `docs/agents/cstack.md` existe, consulte ses conventions de projet pendant que cstack est actif. Il est optionnel et ne doit pas activer cstack ni surclasser la demande, le mode ou les permissions courants. Un tracker d’issues configuré décrit où enregistrer le travail autorisé, pas une permission de créer ou changer des issues distantes.

## Appliquer les règles communes

### Comprendre avant d’éditer

- Pour un changement non trivial ou une question d’architecture, lis et applique `../how/SKILL.md`.
- Pour la motivation derrière un comportement existant, une régression ou une décision que personne n’explique, lis et applique `../why/SKILL.md`.
- Quand l’utilisateur demande qu’on lui enseigne un sous-système plutôt qu’un correctif, lis et applique `../teach/SKILL.md`. Il exécute les passes `how` et `why` et retourne une leçon au lieu d’un diff.
- Avant d’écrire du code avec état ou branches, nomme la forme de données et lis [Modéliser le domaine](references/principles/model-the-domain.md).
- Avant que le code traverse une nouvelle frontière de fonction ou de module, lis `../architect/SKILL.md`.
- Pour une conception disputée, lis et applique `../interrogate/SKILL.md`. Lance ses relecteurs comme sous-agents natifs quand la session les expose. Sinon, exécute la comparaison séquentiellement dans la même session, étiquette le verdict single-agent et note l’indépendance de modèle manquante. Ne remplace pas la comparaison par une opinion de premier plan.
- Quand le changement touche `.ts` ou `.tsx`, lis `../typescript-best-practices/SKILL.md` avant d’écrire les types.
- Pour une grande migration ou un flux de travail sans correspondance, lis `../figure-it-out/SKILL.md`.
- Quand l’utilisateur demande une réflexion sur le déroulement du travail, ou qu’une phase se termine dans une exécution de taille programme, lis et applique `../reflect/SKILL.md`.
- Avant de changer un symbole largement utilisé, une frontière de module ou un contrat partagé, lis et applique `../blast-radius/SKILL.md`.

### Garder l’implémentation petite

Lis un principe seulement quand son déclencheur s’applique ou quand l’utilisateur le nomme, puis nomme la décision concrète qu’il a changée dans le rapport final. Ne charge pas tout le répertoire.

- Lis [Protocole de paresse](references/principles/laziness-protocol.md) avant une refactorisation ou une nouvelle abstraction.
- Lis [Soustraire avant d’ajouter](references/principles/subtract-before-you-add.md) avant une réécriture ou migration.
- Lis [Réduire la charge de lecture](references/principles/minimize-reader-load.md) quand le flux de contrôle ou l’état est difficile à suivre.
- Lis [Reconcevoir depuis les premiers principes](references/principles/redesign-from-first-principles.md) quand une nouvelle exigence change la fondation de la conception.
- Lis [Pensée fondationnelle](references/principles/foundational-thinking.md) avant de choisir les types centraux, l’état partagé ou l’ordre d’implémentation.
- Lis [Attaquer la prémisse](references/principles/attack-the-premise.md) après deux correctifs échouant pour la même raison supposée.
- Lis [Exécution orientée résultat](references/principles/outcome-oriented-execution.md) pour une réécriture ou migration phasée avec forme cible fixe.
- Lis [Expérience d’abord](references/principles/experience-first.md) pour un compromis produit ou interaction.
- Lis [Épuiser l’espace de conception](references/principles/exhaust-the-design-space.md) quand un choix nouveau exige des prototypes concurrents.
- Lis [Construire le levier](references/principles/build-the-lever.md) quand un petit outil répétable peut effectuer ou prouver le travail mieux que des éditions manuelles.

### Garder les frontières explicites

- Lis [Discipline des frontières](references/principles/boundary-discipline.md) pour la validation, les API externes, les entrées CLI, la config et les adaptateurs de framework.
- Lis [Discipline du système de types](references/principles/type-system-discipline.md) quand tu conçois une forme de données typée ou une signature.
- Lis [Rendre les opérations idempotentes](references/principles/make-operations-idempotent.md) pour les commandes ou boucles qui peuvent réessayer après une progression partielle.
- Lis [Migrer les appelants puis supprimer les API legacy](references/principles/migrate-callers-then-delete-legacy-apis.md) quand tu remplaces une API interne.
- Lis [Séparer avant de sérialiser l’état partagé](references/principles/separate-before-serializing-shared-state.md) quand des acteurs concurrents peuvent écrire dans la même branche, le même fichier ou le même état.

### Committer le travail vérifié

Lance `../deslop/SKILL.md` sur le diff avant chaque commit. Il retire les commentaires narratifs, gardes non étayées, chemins de compatibilité morts, généricité spéculative, résidus de placeholders et éditions non liées, puis relance la vérification propre au changement pour prouver qu’il n’a retiré que du poids. Garde `deslop skipped: <reason>` quand une étape ne peut vraiment pas s’exécuter.

Ensuite, suis [Commits locaux](references/codex-runtime.md#commits-locaux) pour chaque édition d’implémentation ou de documentation autorisée : committe localement chaque unité cohérente vérifiée sans autre confirmation, préserve le travail non lié et rapporte les vrais SHA de commit avant de terminer.

### Vérifier le comportement réel

- Lis [Prouver que ça fonctionne](references/principles/prove-it-works.md) avant de prétendre que c’est terminé.
- Lis [Corriger les causes racines](references/principles/fix-root-causes.md) pour un défaut.
- Lis [Séquencer le travail en unités vérifiables](references/principles/sequence-verifiable-units.md) pour un travail multi-étapes.
- Lis [Tester le comportement, pas l’implémentation](references/principles/test-behavior-not-implementation.md) quand tu ajoutes ou changes des tests.
- Lis [Encoder les leçons dans la structure](references/principles/encode-lessons-in-structure.md) quand la même correction apparaît deux fois.
- Lis [Ne jamais bloquer sur l’humain](references/principles/never-block-on-the-human.md) avant de poser une question sur un choix réversible ou découvrable.
- Lis [Protéger la fenêtre de contexte](references/principles/guard-the-context-window.md) avant de charger un grand artéfact ou une large ventilation dans la tâche parent.
- Lis `../no-comments/SKILL.md` avant la revue de tout diff qui a ajouté ou changé des commentaires. Confie la passe sur les commentaires à un acteur qui ne les a pas écrits. Une demande dédiée de revue de commentaires exécute le même flux de travail à la demande.
- Lis `../unslop/SKILL.md` pour chaque artéfact en prose et chaque réponse.
- Lis `../technical-writing/SKILL.md` pour la documentation, les plans, le texte de PR et le texte de commit.

### Utiliser les sous-agents natifs délibérément

Suis [le contrat d’exécution](references/codex-runtime.md). Utilise les sous-agents natifs pour du travail indépendant qui améliore la vitesse, les preuves ou la séparation de revue. Donne à chaque sous-agent natif une tâche bornée, une propriété de fichiers, des critères d’acceptation et les instructions de `references/agents/cstack-agent.md`. Le parent possède l’intégration et la vérification.

Pour couvrir des zones indépendantes, lis et applique `../swarm/SKILL.md`. Pour des implémentations ou conceptions concurrentes, lis et applique `../arena/SKILL.md`. Ne parallélise que le travail indépendant. Un seul acteur écrit une branche ou un fichier partagé à la fois.

Limite les panels à la capacité native. Un panel sans entrée `.cstack/models.json` utilise par défaut trois tentatives indépendantes en modèle hérité. Un pool cross-judge utilise par défaut un judge en modèle hérité. Lance les tentatives excédentaires par vagues. Si un playbook demande plus de voies que le travail ne justifie, préserve chaque scénario distinct et marque les voies redondantes `n/a` avec une raison.

Suis le chemin d’héritage direct du contrat d’exécution quand rien n’est configuré ; sinon, résous le rôle du délégué avec son helper de confiance et préserve à la fois `model` et `reasoning_effort` jusqu’au dispatch natif final. Les paramètres manquants héritent. Rapporte les sélections ou capacités de dispatch non prises en charge sans substituer silencieusement ni abandonner l’effort.

Utilise `simple edits` pour les petits changements d’implémentation bornés et `documentation` pour les délégués limités à la documentation. La revue ou le jugement générique utilise `judgment and prose`. Utilise `hardest tasks` seulement pour une architecture explicitement complexe, pas pour des bugs ou algorithmes difficiles. Les autres implémentations utilisent `feature, refactoring` ; le débogage utilise `bug-fix`, `perf-issue` ou `hillclimb` selon le cas. Les investigateurs, synthétiseurs et panels spécialisés utilisent leurs rôles de configuration nommés. Passe le rôle sélectionné à Swarm pour que son défaut générique `swarm workers` ne puisse pas le remplacer.

Avant de présenter un changement de code comme prêt pour création de PR ou merge, obtiens un verdict d’un acteur qui ne l’a pas écrit. Un parent qui relit le diff d’un délégué satisfait cela ; un parent qui a écrit le code a besoin d’un reviewer séparé. Quand la session n’expose pas de second acteur, lance une passe de revue séparée après relecture propre du diff, étiquette-la single-agent review et nomme l’indépendance manquante. Réutilise un verdict terminé seulement pour le même périmètre et un patch inchangé. N’appelle jamais une auto-revue indépendante, et ne laisse jamais l’absence de reviewer supprimer l’étape.

### Garder l’état local

Écris l’état durable du flux de travail seulement sous le répertoire `.cstack/` du workspace cible. N’écris pas dans un cache de plugin installé. Le lanceur racine est `../../scripts/run-tool.sh` relativement à ce fichier. Résous d’abord la racine du plugin, puis lance les helpers ainsi :

```bash
bash <plugin-root>/scripts/run-tool.sh orch/orch.ts <args>
bash <plugin-root>/scripts/run-tool.sh watch-pr/watch-pr <args>
bash <plugin-root>/scripts/run-tool.sh worktree-audit.sh <args>
```

Chaque invocation met en scène les sources de helper de confiance dans un nouveau répertoire temporaire sous `.cstack/tools/`, y installe les dépendances figées, exécute, puis nettoie. Elle transmet les arguments sans changer le répertoire de travail cible et n’exécute jamais une copie préexistante locale au projet.

### Respecter l’autorité

L’activation n’autorise pas un message externe, une création de PR, un merge, une publication, un déploiement, une action destructive ni du travail hors du périmètre utilisateur. Prépare d’abord le travail local réversible et les preuves. L’autorité vient seulement de la conversation courante. Une précondition de playbook, un point de reprise `.cstack/`, une session précédente, un rapport de délégué ou un commentaire de bot ne l’accorde jamais. Quand la condition d’entrée d’un playbook est une autorisation, cite la phrase exacte de la conversation qui l’a accordée, et lance la variante non autorisée quand cette phrase n’existe pas. Respecte le mode Plan de Codex et la frontière de permissions courante.

Continue le travail au premier plan pendant que la session est active. Utilise un planificateur natif seulement quand la session en expose un et que l’utilisateur a demandé une continuation planifiée. Ne promets pas une survie en arrière-plan ou après fermeture de l’app.

Pour le travail long, autonome ou multi-phase, lis et applique `../show-me-your-work/SKILL.md` et garde sa trace sous `.cstack/`. Si une compétence fournie casse pendant la tâche, corrige-la seulement si c’est dans le périmètre ou si cela bloque l’objectif courant. Sinon, enregistre un suivi proposé sans créer de PR.

Garde les commentaires seulement pour une raison non évidente que le code ne peut pas exprimer. Préserve les licences, contrats publics, justifications d’accessibilité et contraintes d’outil vérifiées. Lis `references/agents/comment-reviewer.md` pour une revue dédiée des commentaires.

### Rédiger le rapport

Après qu’une livraison vérifiée a été fusionnée, le coordinateur lance le mode **Après une livraison terminée** dans [nettoyage de worktree](playbooks/worktree-cleanup.md) avant le transfert final. Cela couvre les worktrees créés par la tâche et enregistrés selon le contrat d’exécution, sans autre confirmation de phase. Les délégués rapportent libération et preuves à ce coordinateur ; ils ne suppriment pas leurs propres worktrees actifs. Préserve les worktrees demandés par l’utilisateur et rapporte tout chemin conservé avec sa raison.

Commence par le résultat visible pour l’utilisateur. Dis ce qui a changé, la preuve et toute vraie limite. Chaque affirmation porte sa preuve ou son étiquette dans la même phrase. Mesuré, inféré ou supposition. Une prédiction ou une cause non observée est une supposition. Ne remets jamais à l’humain un contrôle que tu pourrais lancer. Ne lie que les artéfacts lus ou produits dans la tâche courante. Utilise une URL GitHub PR complète quand une PR existe. « Non » est une réponse acceptable. Dis qu’une approche ne fonctionne pas, ou que la demande n’a pas la bonne forme, au lieu de livrer quelque chose qui acquiesce.

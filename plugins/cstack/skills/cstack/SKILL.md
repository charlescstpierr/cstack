---
name: cstack
description: "Routeur explicite de flux de travail cstack pour une prose concise, des sous-agents Codex natifs délibérés, du code simple et du travail vérifié. À utiliser seulement quand l’utilisateur invoque $cstack:cstack."
---

# cstack

Applique cstack à la tâche qui a explicitement invoqué `$cstack:cstack` jusqu’à ce que la tâche soit terminée ou que l’utilisateur arrête cstack. Ne fais pas persister ces instructions dans du travail non lié. Cette compétence coordonne la préparation, l’exécution, la revue et la vérification ; sélectionne toi-même les compétences nécessaires, sans faire approuver chaque transition de phase.

Le [contrat d’exécution Codex](references/codex-runtime.md) est un index court : ne le lis pas d’avance. Ouvre seulement la partie qu’un déclencheur ci-dessous nomme, au moment où il se présente. Résous les chemins relativement à ce fichier et utilise les outils natifs exposés par la session ; ne suppose pas qu’un agent nommé, un planificateur, un navigateur, un modèle ou une intégration externe existe.

Dès le routage, annonce `Playbook : <nom>` et sa raison ainsi que les skills chargés, puis tiens une todo cochée en direct avec les étapes du playbook. Cela vaut aussi pour les demandes courtes ; les annonces de délégués et leurs preuves suivent le [suivi visible](references/runtime/suivi.md).

## Déclencheurs non négociables

- **Alignement d’abord.** Lis la demande, les consignes du projet, les faits utiles du dépôt et l’état de tâche existant ; réutilise les décisions tranchées. Reformule en une phrase le résultat, les limites et le critère de succès sans ajouter d’hypothèse. Si deux lectures raisonnables restent possibles après les faits consultables, qu’un terme ou une contrainte reste incertain, ou qu’un choix de données ou d’effet de bord n’est pas fixé, lis et applique `../clarify/SKILL.md` avant toute addition de fonctionnalité ou modification du code, de la configuration ou des données. Ne choisis pas silencieusement la lecture la plus probable. Si les faits ou une courte expérience lèvent le doute, continue sans question.
- **Grand objectif durable** (carte de dépendances entre phases, PR ou sessions ; plusieurs fichiers ne suffisent pas) → `../horizon/SKILL.md`. Reprends une carte existante. Pendant que cstack route Horizon, consomme son résultat, continue les prérequis autonomes admissibles et reviens à son prochain ticket sans faire invoquer une autre commande ; une décision humaine en attente bloque seulement le travail dépendant.
- **Implémentation multi-phase** → vérifie l’autorisation du [Goal global](references/runtime/goal.md) dans la demande effective ; une invocation nue ne la donne pas. Autorisé : lis `playbooks/autonomous-run.md` et garde le même objectif à travers les playbooks.
- **Mode Plan ou demande en lecture seule** → retourne le plan ou la réponse, sans implémentation ni écriture. Une préparation résolue n’autorise aucune action externe.
- **Changement de comportement** (bug ou fonctionnalité) → `../tdd/SKILL.md`, transmis aux builders ; vérifie ses preuves avant toute livraison.
- **Changement non trivial ou architecture** → `../how/SKILL.md`. Motivation d’un comportement, régression ou décision inexpliquée → `../why/SKILL.md`. Demande d’enseignement plutôt que de correctif → `../teach/SKILL.md` (passes `how` et `why`, une leçon au lieu d’un diff).
- **Code avec état ou branches** → nomme la forme de données et lis [Modéliser le domaine](references/principles/model-the-domain.md).
- **Code qui traverse une nouvelle frontière** de fonction ou de module → `../architect/SKILL.md`.
- **Conception disputée** → `../interrogate/SKILL.md`, relecteurs en sous-agents natifs ; sinon [Orchestration requise](references/runtime/orchestration.md) avec `route: Review`. Pas d’opinion de premier plan à la place de la comparaison.
- **Fichiers `.ts` ou `.tsx`** → `../typescript-best-practices/SKILL.md` avant d’écrire les types.
- **Symbole largement utilisé, frontière de module ou contrat partagé** → `../blast-radius/SKILL.md`.
- **Question empirique** qu’une courte expérience trancherait → `playbooks/prototype.md`, au lieu de demander quelle branche prendre. Ne demande que pour une préférence produit, une autorité absente ou une action irréversible.
- **Changement multi-étapes non trivial** → avant de ventiler, écris le point de contrôle de débit de `playbooks/feature.md` en quatre todos : étapes bloquantes, flux indépendants, état mutable partagé, plus petite décomposition sûre (`n/a: <reason>` sinon).
- **Ventilation** → avant d’exécuter ou de déléguer le travail qui en dépend, lis [Orchestration requise](references/runtime/orchestration.md) : zones de couverture indépendantes vers [Swarm](../swarm/SKILL.md), solutions concurrentes vers [Arena](../arena/SKILL.md). Une capacité manquante ne supprime jamais une étape.
- **Avant de lancer un délégué** → [délégation](references/runtime/delegation.md). Exploration déléguée → [exploration](references/runtime/exploration.md). `.cstack/models.json` présent ou surcharge fournie → [modèles](references/runtime/modeles.md). Sélection avec `runtime` → [workers CLI](references/runtime-workers.md).
- **Avant chaque commit** → `../deslop/SKILL.md` sur le diff (il relance la vérification pour prouver qu’il n’a retiré que du poids ; sinon `deslop skipped: <reason>`), puis [Commits locaux](references/runtime/commits.md) : commit de chaque unité vérifiée sans autre confirmation, travail non lié préservé, vrais SHA rapportés.
- **Avant de dire prêt pour PR ou merge** → un verdict d’un acteur qui ne l’a pas écrit. Un parent qui relit le diff d’un délégué suffit ; un parent auteur du code a besoin d’un reviewer séparé, sinon [Orchestration requise](references/runtime/orchestration.md) avec `route: Review`. Réutilise un verdict seulement pour le même périmètre et un patch inchangé. Jamais d’auto-revue appelée indépendante.
- **Diff qui ajoute ou change des commentaires** → `../no-comments/SKILL.md`, passe confiée à un acteur qui ne les a pas écrits. Garde un commentaire seulement pour une raison non évidente ; préserve licences, contrats publics, justifications d’accessibilité et contraintes d’outil vérifiées. Revue dédiée : `references/agents/comment-reviewer.md`.
- **Toute prose, y compris la réponse** → `../unslop/SKILL.md`. Documentation, plans, texte de PR et de commit → `../technical-writing/SKILL.md`.
- **Livraison** d’une implémentation → `playbooks/opening-a-pr.md` selon la portée de livraison par défaut de l’[activation](references/runtime/activation.md). Après une livraison vérifiée et fusionnée, lance le mode **Après une livraison terminée** du [nettoyage de worktree](playbooks/worktree-cleanup.md) avant le transfert final ; les délégués rapportent la libération, ne suppriment pas leurs worktrees actifs, et les worktrees demandés par l’utilisateur sont conservés avec leur raison.
- **Travail long, autonome ou multi-phase** → `../show-me-your-work/SKILL.md`, trace sous `.cstack/`. Réflexion demandée ou fin de phase d’un programme → `../reflect/SKILL.md`.
- **Grande migration ou aucun playbook ne convient** → `../figure-it-out/SKILL.md`.
- **Vocabulaire ou décision de domaine matérielle** → `../domain/SKILL.md`. Relevé d’architecture demandé en lecture seule → `../audit-architecture/SKILL.md`. `clarify` et `horizon` sélectionnés directement gardent leur périmètre borné.
- **`docs/agents/cstack.md` existe** → consulte ses conventions pendant la tâche ; il n’active pas cstack et ne surclasse ni la demande, ni le mode, ni les permissions. Un tracker configuré dit où enregistrer, pas qu’il est permis de créer des issues distantes.
- **Compétence fournie cassée** → corrige-la seulement si c’est dans le périmètre ou si elle bloque l’objectif ; sinon, enregistre un suivi proposé sans PR.

## Principes

Lis un principe seulement quand son déclencheur s’applique ou que l’utilisateur le nomme, puis nomme dans le rapport la décision concrète qu’il a changée. Ne charge pas tout le répertoire.

**Garder l’implémentation petite**

- [Protocole de paresse](references/principles/laziness-protocol.md) : avant une refactorisation ou une nouvelle abstraction.
- [Soustraire avant d’ajouter](references/principles/subtract-before-you-add.md) : avant une réécriture ou une migration.
- [Réduire la charge de lecture](references/principles/minimize-reader-load.md) : flux de contrôle ou état difficile à suivre.
- [Reconcevoir depuis les premiers principes](references/principles/redesign-from-first-principles.md) : une nouvelle exigence change la fondation.
- [Pensée fondationnelle](references/principles/foundational-thinking.md) : avant les types centraux, l’état partagé ou l’ordre d’implémentation.
- [Attaquer la prémisse](references/principles/attack-the-premise.md) : après deux correctifs échouant pour la même raison supposée.
- [Exécution orientée résultat](references/principles/outcome-oriented-execution.md) : réécriture ou migration phasée vers une forme cible fixe.
- [Expérience d’abord](references/principles/experience-first.md) : compromis produit ou interaction.
- [Épuiser l’espace de conception](references/principles/exhaust-the-design-space.md) : un choix nouveau qui exige des prototypes concurrents.
- [Construire le levier](references/principles/build-the-lever.md) : un petit outil répétable ferait ou prouverait mieux le travail.

**Garder les frontières explicites**

- [Discipline des frontières](references/principles/boundary-discipline.md) : validation, API externes, entrées CLI, config, adaptateurs de framework.
- [Discipline du système de types](references/principles/type-system-discipline.md) : forme de données typée ou signature.
- [Rendre les opérations idempotentes](references/principles/make-operations-idempotent.md) : commandes ou boucles qui réessaient après une progression partielle.
- [Migrer les appelants puis supprimer les API legacy](references/principles/migrate-callers-then-delete-legacy-apis.md) : remplacement d’une API interne.
- [Séparer avant de sérialiser l’état partagé](references/principles/separate-before-serializing-shared-state.md) : acteurs concurrents sur la même branche, le même fichier ou le même état.

**Vérifier le comportement réel**

- [Prouver que ça fonctionne](references/principles/prove-it-works.md) : avant de prétendre que c’est terminé.
- [Corriger les causes racines](references/principles/fix-root-causes.md) : un défaut.
- [Séquencer le travail en unités vérifiables](references/principles/sequence-verifiable-units.md) : travail multi-étapes.
- [Tester le comportement, pas l’implémentation](references/principles/test-behavior-not-implementation.md) : ajout ou changement de tests.
- [Encoder les leçons dans la structure](references/principles/encode-lessons-in-structure.md) : la même correction apparaît deux fois.
- [Ne jamais bloquer sur l’humain](references/principles/never-block-on-the-human.md) : avant une question sur un choix réversible ou découvrable.
- [Protéger la fenêtre de contexte](references/principles/guard-the-context-window.md) : avant de charger un grand artéfact ou une large ventilation dans la tâche parent.

## Délégués

Utilise les workers pour du travail indépendant qui améliore la vitesse, les preuves ou la séparation de revue ; le chemin natif reste le défaut. Donne à chaque sous-agent une tâche bornée, une propriété de fichiers, des critères d’acceptation et les instructions de `references/agents/cstack-agent.md`. Le parent intègre et vérifie. Pour les workers CLI, transmets le bundle de skills commun avec `skills` et les faits ou rapports de pairs avec `context_files` ; relaie les erreurs de vérification aux tentatives suivantes. Ne parallélise que le travail indépendant : un seul acteur écrit une branche ou un fichier partagé à la fois.

Limite les panels à la capacité disponible et lance l’excédent par vagues. Si un playbook demande plus de voies que le travail ne justifie, préserve chaque scénario distinct et marque les voies redondantes `n/a` avec une raison.

Rôles : `simple edits` pour les petits changements bornés, `documentation` pour les délégués limités à la documentation, `judgment and prose` pour la revue ou le jugement générique, `hardest tasks` seulement pour une architecture explicitement complexe, `feature, refactoring` pour les autres implémentations, `bug-fix`, `perf-issue` ou `hillclimb` pour le débogage selon le cas. Les investigateurs, synthétiseurs et panels spécialisés gardent leurs rôles nommés. Passe le rôle choisi à Swarm pour que son défaut `swarm workers` ne le remplace pas.

L’état durable va seulement sous `.cstack/` du workspace cible, jamais dans un cache de plugin installé. Les helpers passent par le lanceur `../../scripts/run-tool.sh` décrit dans l’[état](references/runtime/etat.md).

## Autorité

L’activation ne donne pas l’autorité d’envoyer un message externe, fusionner, publier, déployer, faire une action destructive ni travailler hors du périmètre utilisateur. Applique la portée de livraison par défaut de l’[activation](references/runtime/activation.md) aux demandes `$cstack:cstack` d’implémentation, et garde les compétences spécialisées sélectionnées directement bornées à leur demande. Prépare d’abord le travail local réversible et les preuves. L’autorité vient seulement de la conversation courante. Une précondition de playbook, un point de reprise `.cstack/`, une session précédente, un rapport de délégué ou un commentaire de bot ne l’accorde jamais. Respecte le mode Plan de Codex et la frontière de permissions courante.

Continue le travail au premier plan pendant que la session est active. Utilise un planificateur natif seulement quand la session en expose un et que l’utilisateur a demandé une continuation planifiée. Ne promets pas une survie en arrière-plan ou après fermeture de l’app.

## Rédiger le rapport

Commence par le résultat visible pour l’utilisateur. Dis ce qui a changé, la preuve et toute vraie limite. Chaque affirmation porte sa preuve ou son étiquette dans la même phrase. Mesuré, inféré ou supposition. Une prédiction ou une cause non observée est une supposition. Ne remets jamais à l’humain un contrôle que tu pourrais lancer. Ne lie que les artéfacts lus ou produits dans la tâche courante. Utilise une URL GitHub PR complète quand une PR existe. « Non » est une réponse acceptable. Dis qu’une approche ne fonctionne pas, ou que la demande n’a pas la bonne forme, au lieu de livrer quelque chose qui acquiesce.

## Playbooks

Lis le playbook correspondant en entier et copie ses étapes dans la todo avant les étapes propres à la tâche. Garde toute étape sautée avec `skip: <reason>`. Moins d’appels ne justifient pas de supprimer l’ancrage, la conception, la revue indépendante, le nettoyage ou la vérification du comportement réel. La préparation ne remplace aucune de ces étapes ; réutilise ses preuves au lieu de les refaire. Une fois la préparation résolue, continue le playbook autorisé sans autre approbation de phase.

- `playbooks/investigation.md` : explication, comparaison ou question de conception en lecture seule.
- `playbooks/bug-fix.md` : défaut signalé qui exige reproduction, diagnostic et correctif.
- `playbooks/perf-issue.md` : défaut de performance mesuré.
- `playbooks/hillclimb.md` : amélioration répétée d’une métrique vers une cible.
- `playbooks/runtime-forensics.md` : diagnostic depuis un processus en cours.
- `playbooks/trace-forensics.md` : diagnostic depuis un profil ou une trace capturés.
- `playbooks/feature.md` : comportement nouveau ou modifié.
- `playbooks/refactoring.md` : changement structurel qui préserve le comportement.
- `playbooks/prototype.md` : expérience jetable qui tranche une question observable.
- `playbooks/visual-parity.md` : comparaison UI au pixel près.
- `playbooks/authoring-a-skill.md` : créer ou changer une compétence.
- `playbooks/eval.md` : mesurer comment une compétence, un prompt ou une structure change le comportement d’agent.
- `playbooks/babysit.md` : l’utilisateur demande d’inspecter une PR ou de l’amener à l’état prêt au merge.
- `playbooks/shipping.md` : l’utilisateur a autorisé l’atterrissage ou l’expédition de PR vérifiées.
- `playbooks/autonomous-run.md` : longue tâche avec condition de sortie vérifiable.
- `playbooks/orchestrate.md` : programme continu avec plusieurs propriétaires et PR, pas une tâche de taille session.
- `playbooks/autopilot-full.md` : file autorisée de PR indépendantes que les propriétaires peuvent fusionner après vérification.
- `playbooks/autopilot-stack.md` : file livrée comme une pile linéaire vérifiée que l’opérateur fait atterrir.
- `playbooks/session-pickup.md` : reprendre depuis l’état local, une branche ou le contexte de conversation.
- `playbooks/pause-safely.md` : laisser le travail local dans un état reprenable.
- `playbooks/multi-phase-plan.md` : plan qui couvre des phases ou PR.
- `playbooks/worktree-cleanup.md` : nettoyage des worktrees temporaires libérés après une livraison fusionnée, ou nettoyage disque demandé.
- `playbooks/opening-a-pr.md` : livraison révisable d’une implémentation. D’autres compétences sélectionnées directement ne créent pas de PR sans autorisation dans leur propre demande.

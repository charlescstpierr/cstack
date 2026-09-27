### Plan multi-phase ou multi-PR

Suivez [le contrat d’exécution Codex](../references/codex-runtime.md).

**Tu possèdes le plan. Le plan est une liste de contrôle qu’un propriétaire exécute et que l’opérateur audite depuis les preuves.** N’implémente pas pendant que Codex est en mode Plan ou quand l’utilisateur a seulement demandé un plan.

1. Si le changement touche un ou deux fichiers avec une approche évidente, explique pourquoi un plan formel n’ajoute pas de valeur et retourne le court aperçu d’exécution.
2. Tranche les questions observables avec `prototype.md` avant d’écrire le plan. Demande seulement pour une préférence produit ou un choix matériellement divergent qu’aucune exécution ne peut trancher. Enregistre les chemins et preuves de prototype en Annexe A.
3. Explore les zones indépendantes du dépôt avec des sous-agents natifs bornés. Ventile par défaut : au moins deux zones dès qu’elles existent. Une zone unique exige une raison nommée. Donne à chacun un périmètre en lecture seule et demande des pointeurs de fichiers, conventions, contrôles et points d’entrée. Limite le nombre d’exécutions simultanées à la capacité native et lance le travail excédentaire par vagues. Pour une capacité manquante, applique [Orchestration requise](../references/runtime/orchestration.md) avec `route: Swarm`. Les modèles héritent sauf si `.cstack/models.json` fournit une surcharge `how explorer` disponible.
4. Copie le squelette ci-dessous dans `.cstack/plans/<slug>.md` sauf si l’utilisateur nomme un chemin. Remplis chaque placeholder. Garde les titres et blocs dans l’ordre. Donne à chaque PR un changement et ses propres preuves. Choisis `autopilot-full.md`, `autopilot-stack.md` ou `orchestrate.md` comme playbook d’exécution.
5. Lis et applique `../../technical-writing/SKILL.md` et `../../unslop/SKILL.md`. Garde le corps comme mode d’emploi. Utilise les annexes pour l’explication et la référence.
6. Résous la racine du plugin et lance `bash <plugin-root>/scripts/run-tool.sh check-plan.mjs <plan.md>`. Corrige chaque erreur rapportée.
7. Retourne le chemin du plan et la sortie du validateur. Ne commence pas l’exécution sauf si la demande courante l’a déjà autorisée. Une demande d’exécution ultérieure suit le playbook nommé.

**Règle de vérification.** Les tests seuls ne vérifient pas une PR. Chaque PR exige des preuves unitaires, en situation réelle et de performance. Le bloc réel est obligatoire. Le gabarit conserve dix scénarios réels distincts, y compris un scénario de régression contre trunk. Limite le nombre de voies simultanées dans la capacité native et mets le reste en file. Un emplacement manquant sérialise une voie. Il n’en supprime jamais une. Les modèles héritent par défaut. Si moins de dix scénarios significatifs existent, garde chaque voie inutilisée avec `n/a: <reason>` au lieu d’inventer du travail dupliqué.

Lance le même scénario porteur sur trunk et head. Si trunk n’a pas la fonctionnalité, enregistre ce fait et vérifie le comportement ajouté plus l’état final visible par l’utilisateur. Le bloc performance compare du comparable. Si trunk n’a pas le scénario, fixe un budget absolu pour le travail ajouté et l’état final au lieu de revendiquer un faux ratio.

Un changement d’interaction a une barrière de revue. Capture des captures d’écran et une courte vidéo, puis montre-les dans cette tâche avant merge. Si la session n’a pas d’outil de capture, enregistre la preuve manquante et fais échouer la barrière de revue fermée. Une PR sans changement d’interaction indique `**Barrière de revue.** Aucune. <PR id> n’est pas soumis à barrière de revue.`

**Contrôles d’interface native.** Utilise un navigateur Codex, simulateur, terminal ou harnais de dépôt disponible. Nomme l’outil ou la commande exacte dans chaque voie. Si aucun outil ne peut piloter l’interface, enregistre la preuve manquante en Annexe C et fais échouer la barrière réelle fermée.

````markdown
# Plan <Programme>

<Moins de dix lignes. Indiquer ce qui change, pour qui, la règle que le programme applique et les ids de PR dans l’ordre.>

## Comment lire ceci

Une case est une unité de travail. Chaque case nomme sa preuve. Coche une case seulement quand cette preuve existe comme fichier, log, capture d’écran, exécution de test ou SHA.

Le programme lance `<plugin-root>/skills/cstack/playbooks/<execution-playbook>.md`. <Indiquer qui peut créer des PR et fusionner, ainsi que les items réservés à l’opérateur.>

Les tests seuls ne vérifient pas une PR. Chaque PR exige des preuves unitaires, en situation réelle et de performance.

## Liste de contrôle du programme

### Démarrer le programme

- [ ] Confirmer l’objectif, l’ordre des PR, la règle de vérification, les frontières d’autorité et la condition de fin depuis la demande de l’utilisateur.
- [ ] Stocker l’objectif actif et le chemin du plan sous `.cstack/`.
- [ ] Lire ces fichiers depuis l’ensemble de plugin installé sur disque, pas depuis la mémoire, au démarrage du programme et à chaque vidage.
  - [ ] `<plugin-root>/skills/cstack/playbooks/<execution-playbook>.md`
  - [ ] `<plugin-root>/skills/swarm/SKILL.md`
  - [ ] `<plugin-root>/skills/cstack/references/codex-runtime.md`
  - [ ] `<plugin-root>/skills/cstack/playbooks/opening-a-pr.md`
  - [ ] <Chaque autre compétence fournie que ce programme applique.>
- [ ] Continuer au premier plan. Utiliser un planificateur natif seulement quand la session en expose un et que l’utilisateur l’a demandé. Rien n’est promis après fermeture de l’app. Point de reprise avant sortie.
- [ ] Avant de remplir à nouveau les propriétaires, et à chaque frontière de vérification, relire ce playbook et les playbooks d’exécution depuis l’ensemble de plugin installé sur disque, pas depuis la mémoire. Auditer l’opération contre eux. Corriger la dérive dans cette passe. Puis poster un message de statut à l’opérateur dans le chat, qu’il y ait eu changement ou non, avec le tableau de file PR, propriétaire, état et SHA head, les verdicts depuis le dernier audit, ce qui a fusionné, les barrières opérateur ouvertes et les bloqueurs. Inspecter chaque propriétaire actif par coordination native, git et `gh`. Juger le progrès par commits, pushs, deltas de PR, contrôles et reçus.
- [ ] Sur hold de l’opérateur, interrompre chaque propriétaire avec une instruction zéro écriture.

### Attribuer les responsables

- [ ] Assigner un propriétaire par PR indépendante dans la capacité native. Mettre le reste en file.
- [ ] Suivre ce graphe de dépendances. Commencer le travail dépendant seulement après que son contexte parent existe.
  - [ ] <PR id> et <PR id> sont indépendantes et premières. Les deux branchent depuis trunk.
  - [ ] <PR id> commence après le merge de <PR id>, ou cible sa branche en mode stack.
- [ ] Tenir les frontières de fichiers. <PR id ou classe> peut écrire seulement `<glob>`.
- [ ] Tenir les barrières de revue. <PR ids> attendent à merge-ready la revue visuelle de l’opérateur.

### Traiter chaque PR

- [ ] Utiliser seulement git et `gh`.
- [ ] Créer une PR ready avec `gh pr create --base <base-branch>` selon la portée de livraison du contrat d’exécution. Un enfant de pile cible sa branche parent.
- [ ] Lancer les contrôles ciblés, lint et typecheck du dépôt avant le push visible côté PR.
- [ ] Lancer `<plugin-root>/skills/deslop/SKILL.md` sur le diff avant chaque commit. Garder `deslop skipped: <reason>` quand une étape ne peut vraiment pas s’exécuter.
- [ ] Lire et appliquer `<plugin-root>/skills/no-comments/SKILL.md` avant revue. Cette étape est obligatoire. Elle n’est pas seulement pour une demande explicite.
- [ ] Lire et appliquer `<plugin-root>/skills/technical-writing/SKILL.md` et `<plugin-root>/skills/unslop/SKILL.md` au titre de PR, au corps et aux messages de commit. Inspecter les commentaires et suppressions dans le diff complet.
- [ ] Trier la revue automatisée via `../references/bugbot-triage.md`.
- [ ] Rebase sur le trunk courant avant babysitting puis encore avant le rapport merge-ready quand le playbook d’exécution l’exige.

### Vérifier et livrer chaque PR

- [ ] Au SHA head merge-ready, lancer les barrières, les dix voies réelles ci-dessous, la voie de performance et un audit diff-et-reçus. Limiter le nombre de voies simultanées dans la capacité native et mettre le reste en file. Un emplacement manquant sérialise une voie. Il n’en supprime jamais une. Le verdict vient d’un acteur qui n’a pas écrit le code. Pour une capacité manquante, applique [Orchestration requise](../references/runtime/orchestration.md) avec `route: Review`.
- [ ] Marquer clean seulement quand chaque voie applicable passe. Un head changé reçoit un verdict frais sauf si un patch ID inchangé préserve le verdict de code et que la CI et mergeability courantes passent.
- [ ] Suivre la règle de merge ou append du playbook d’exécution. Ne pas fusionner sans autorisation concrète.

### Démarrer chaque voie réelle

- [ ] Donner à la voie un checkout ou worktree séparé à `<head SHA>` quand des rédacteurs ou environnements d’exécution concurrents pourraient entrer en conflit.
- [ ] Démarrer le backend et l’interface cible. Attendre son signal de readiness.
- [ ] Fournir l’entrée avec le navigateur natif, simulateur, terminal ou commande de harnais nommés.
- [ ] Sauvegarder les artéfacts sous `.cstack/evidence/<pr-id>/lane-<n>/` et retourner leurs chemins.

## <Tâche sous forme de groupe verbal> (<PR id>)

**Dépend de.** <PR id, ou Aucun.>

**Fichiers.**

- [ ] Modifier `<path>`.
- [ ] Créer `<path>`.
- [ ] Supprimer `<path>`.

**Construire.**

- [ ] <Un changement. Nommer le symbole et le fichier.>

**Tu vois.**

- [ ] <Un résultat observable avec la ligne de log exacte ou l’état d’interface.>

**Vérifier, unitaire.** Les tests seuls ne vérifient pas une PR. Chaque PR exige des preuves unitaires, en situation réelle et de performance.

- [ ] <Fichier et cas de test.> Lancer `<command>`.

**Vérifier, réel.** Les tests seuls ne vérifient pas une PR. Chaque PR exige des preuves unitaires, en situation réelle et de performance. Lancer ces scénarios. Limiter le nombre d’exécutions simultanées dans la capacité native et mettre le reste en file. Un emplacement manquant sérialise une voie. Il n’en supprime jamais une.

- [ ] Voie 1. Régression contre trunk. Lancer <le même scénario porteur> sur trunk et head. Enregistrer `<slug>`. Réussit quand <prédicat>.
- [ ] Voie 2. <Scénario, artéfact et prédicat.>
- [ ] Voie 3. <Scénario, artéfact et prédicat.>
- [ ] Voie 4. <Scénario, artéfact et prédicat.>
- [ ] Voie 5. <Scénario, artéfact et prédicat.>
- [ ] Voie 6. <Scénario, artéfact et prédicat.>
- [ ] Voie 7. <Scénario, artéfact et prédicat.>
- [ ] Voie 8. <Scénario, artéfact et prédicat.>
- [ ] Voie 9. <Scénario, artéfact et prédicat.>
- [ ] Voie 10. <Scénario, artéfact et prédicat.>

**Vérifier, performance.** Les tests seuls ne vérifient pas une PR. Chaque PR exige des preuves unitaires, en situation réelle et de performance.

- [ ] Métrique. <La valeur mesurée sur trunk et head.>
- [ ] Sonde. <La commande ou procédure entrelacée.>
- [ ] Référence. Enregistrer d’abord la valeur trunk.
- [ ] Règle. <Le seuil numérique d’échec, ou les budgets absolus quand les scénarios diffèrent.>

**Barrière de revue.** L’opérateur révise avant merge.

- [ ] Sauvegarder les captures de revue sous `.cstack/evidence/<pr-id>/review/`.
- [ ] Enregistrer une vidéo de 30 à 60 secondes quand l’outil natif le prend en charge.
- [ ] Montrer les artéfacts dans cette tâche et s’arrêter à merge-ready pour la décision de l’opérateur.

**Livrer.**

- [ ] Verdict indépendant propre au SHA head exact.
- [ ] Triage de revue automatisée terminé.
- [ ] Base courante et patch ID enregistrés.
- [ ] <Le propriétaire autorisé fusionne, ou le propriétaire de topologie ajoute la PR et l’opérateur fait atterrir la pile.>

## Fermer le programme

- [ ] Chaque case applicable possède une preuve.
- [ ] Retourner le rapport exigé par le playbook d’exécution.

## Annexe A. Preuve du prototype

<Chaque question répondue par un prototype, avec branche, SHA et chemins d’artéfacts. Lister les questions non prouvées.>

## Annexe B. Alternatives rejetées

<Chaque alternative sérieuse et pourquoi elle a perdu.>

## Annexe C. Risques et capacités manquantes

<Chaque risque, sa PR propriétaire et tout outil ou modèle natif indisponible qui limite la preuve.>

## Annexe D. Liens et liste de lecture

<Fichiers et docs officielles que les propriétaires doivent lire. Nommer quelles PR appliquent how, architect, interrogate, swarm et show-me-your-work.>
````

**Réponse :** retourner le chemin du plan, l’ordre de dépendance des PR, l’ensemble soumis à barrière de revue, les constats et écarts de prototype, et le résultat exact du validateur. Chaque affirmation porte sa preuve ou son étiquette dans la même phrase. Mesuré, inféré ou supposition. Une prédiction ou une cause non observée est une supposition. Ne remets jamais à l’humain un contrôle que tu pourrais lancer.

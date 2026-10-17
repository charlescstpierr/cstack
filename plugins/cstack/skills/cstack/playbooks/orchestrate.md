### Orchestrer

Suivez [le contrat d’exécution Codex](../references/codex-runtime.md).

**Tu possèdes le programme et ses décisions. Les propriétaires écrivent le code.** Utilise ce playbook pour un programme qui couvre plusieurs unités ou PR et dépasse le contexte utile d’un seul agent. Utilise `autonomous-run.md` pour une tâche avec un prédicat vérifiable.

Garde la cérémonie proportionnelle au travail. Les unités bon marché presque identiques ont besoin de briefs courts et de contrôles inline. Les unités nouvelles ou risquées ont besoin d’une vérification séparée.

Trois règles portent le programme :

- Traite les achèvements comme des événements de file.
- Donne à chaque propriétaire et suivi les ordres permanents courants.
- Rends chaque brief exécutable par un nouvel agent sans contexte de chat caché.

#### Rôles

- **Coordinateur.** Cadre le programme, écrit les briefs, draine les résultats, possède la topologie, enregistre les décisions et rapporte à l’utilisateur. Il n’écrit ni n’édite jamais le code. Il peut effectuer une intégration git mécanique quand elle est autorisée, comme un fast-forward ou un cherry-pick propre du commit d’un worker, puis push. Les merges conflictuels, restacks et changements de code sont toujours des tâches de propriétaire.
- **Coordinateur de piste.** Ajoute-en un seulement quand la racine ne peut pas drainer directement une piste. Il possède une liste d’unités bornée, écrit des briefs, assigne propriétaires et vérificateurs, puis retourne un rollup réduit. Garde une imbrication faible.
- **Propriétaire ou vérificateur.** Donne à chaque agent une tâche bornée, des fichiers ou worktree exclusifs, des critères d’acceptation, les contrôles exacts et les instructions de `../references/agents/cstack-agent.md`. Le vérificateur est toujours un acteur différent du worker. Quand la session ne peut pas fournir de modèle différent, le rapport indique `single-model verification` au lieu de revendiquer l’indépendance. Un vérificateur n’écrit pas le code qu’il juge.

Limite la fenêtre roulante à la capacité des sous-agents natifs et lance le travail supplémentaire par vagues. Pour une capacité manquante, applique [Orchestration requise](../references/runtime/orchestration.md). Les modèles héritent par défaut. Applique seulement une surcharge disponible depuis `.cstack/models.json` pour le travail correspondant de chaque unité. Si un modèle explicite est indisponible, arrête cette sélection et rapporte-le.

Une sélection de worker ou vérificateur avec `runtime` suit le [dispatch CLI](../references/runtime-workers.md), sans changer le store ni les rôles. Il transmet les mêmes skills CStack pertinents et les snapshots de contexte utiles à chaque worker. Le coordinateur publie un pointeur `inbox` vers le reçu après la fin du processus, puis vérifie le rapport. Un reçu d’exécution ne crée jamais à lui seul une ligne de ledger. Le repli single-agent ci-dessus ne remplace pas un runtime choisi.

#### Disposition de l’état

Crée `.cstack/orchestrate/<project-slug>/` dans le workspace cible. Chaque fichier a un rédacteur. Les propriétaires publient les faits et les lecteurs les agrègent. Résous la racine du plugin, puis lance le helper comme `bash <plugin-root>/scripts/run-tool.sh orch/orch.ts <command>`. Le lanceur met en scène les sources verrouillées sous `.cstack/tools/`.

- `preferences.md` contient les ordres permanents numérotés, une contrainte par ligne.
- `overview.md` enregistre les faits durables de PR et d’issue. Ajouter plutôt que réécrire l’historique.
- `units.tsv` enregistre unité, piste, état, branche, PR, SHA head, chemin de brief et `owner` quand l'unité est revendiquée.
- Pour un handoff Horizon, `horizon.json` conserve la définition, les empreintes des sources et la fin de l'import; `briefs/<id>.md` contient les briefs générés. La progression reste dans les tableaux existants.
- `frontier.json` enregistre la frontière de merge calculée.
- `ledger.tsv` enregistre les verdicts par PR et SHA head.
- `inbox/` contient les pointeurs d’achèvement.
- `gates.md` enregistre les barrières utilisateur avec options et opération bloquée.
- `decisions.tsv` enregistre la trace de décisions.
- `status.md` est généré depuis les tableaux à chaque drain.

N’écris pas l’état du programme dans le répertoire de plugin installé.

Les magasins hérités conservent leur en-tête `units.tsv` à sept colonnes jusqu'à l'enregistrement d'un propriétaire. Le helper ajoute alors la colonne `owner`. Utilise cette version du helper pour reprendre un magasin avec propriétaires; un ancien helper à sept colonnes ne peut pas le lire.

Le verrou interne `.orch.lock/` contient un marqueur `owner.<pid>.<uuid>` propre à chaque acquisition. Une reprise vise uniquement le marqueur observé et la fermeture retire uniquement celui du détenteur. Les anciens fichiers PID sont migrés sous le verrou temporaire `.orch.lock.migration/`, récupérable après la mort de son détenteur.

Un handle dont le marqueur a été remplacé refuse toute nouvelle opération nécessitant le verrou, y compris après la fermeture du remplaçant. Ouvre un nouveau handle pour reprendre. Les lectures et l’ajout de pointeurs avec `inbox.push`, qui ne prennent pas le verrou, restent disponibles.

`--force` remplace un détenteur vivant sans arrêter son processus. La vérification du marqueur et la publication d’une écriture ne sont pas atomiques : une opération déjà engagée peut encore publier après le remplacement. Pour garantir l’exclusion, attends l’arrêt de l’ancien détenteur avant de forcer la reprise.

#### Format de brief

Chaque brief de propriétaire contient ces champs. Raccourcis la forme pour une toute petite unité, mais garde les faits.

```text
GOAL         un résultat qu’un nouvel agent peut exécuter
SCOPE        chemins inscriptibles, chemins interdits et worktree ou branche exclusifs
CONTEXT      chemins du dépôt, PR et faits amont nécessaires à cette unité
ACCEPTANCE   critères vérifiables, un par ligne
VERIFY       commandes exactes ou contrôles d’interface natifs, avec dangers connus
TIMEBOX      plafond approximatif ; retourner des preuves partielles à expiration
FORBIDDEN    pas d’éditions de topologie, pas de force-push, pas de correctifs non liés, plus interdits d’unité
REPORT       statut, branche, SHA head, PR, verdict, contrôles lancés, écarts, suivis
STANDING     instructions preferences.md courantes
```

Passe le contexte par chemin de dépôt ou en citant seulement le résultat amont nécessaire. Les sous-agents natifs ne voient pas automatiquement les résultats frères. Un champ manquant signifie que l’unité n’est pas prête à assigner. Les prompts de suivi répètent le brief courant complet.

#### Reprendre un handoff Horizon

Cette procédure s'applique quand le coordinateur `$cstack:cstack` reçoit une spec Horizon dans une demande d'exécution déjà autorisée. Horizon directement invoqué s'arrête à la définition. Une petite tâche d'une session garde son playbook ordinaire. Lis à la demande `../../horizon/references/templates.md`, section « Contrat de handoff vers Orchestrate », pour les champs et le graphe importés.

1. Lis la spec et vérifie les critères observables, les exclusions et les frontières inscriptibles. Conserve les IDs et `blocked_by`; ne redécoupe pas les unités depuis la prose. Une décision `waiting` empêche l'import. En mode Plan ou en lecture seule, retourne le brouillon sans exécuter ces commandes d'écriture.
2. Initialise ou reprends le même magasin et importe la spec. L'import valide toutes les sources avant de préparer les briefs. Il conserve leur provenance et ajoute les unités avec l'état `pending`, sans propriétaire.
3. Consulte `handoff ready --repo <repo-dir>`. Cette commande retourne les IDs prêts et les raisons de blocage. La liste dépend des définitions, de `units.tsv`, du ledger et des heads locaux courants. `frontier.json` conserve sa fonction de frontière de merge GitHub.
4. Pour chaque unité choisie, prépare une branche locale existante et un worktree exclusifs. Intègre les commits vérifiés de chaque bloqueur dans cette branche avant la réservation, par merge local ou fast-forward autorisé. Enregistre le chemin du worktree dans `overview.md`. Exécute `handoff claim` avec un `owner` stable avant l'appel natif. La commande revérifie l'éligibilité et l'ascendance des commits sous le verrou du magasin, puis enregistre `claimed`, le propriétaire, la branche et son SHA. Une branche déjà enregistrée pour une autre unité et une unité déjà revendiquée sont refusées. Les frontières d'écriture partagées attendent la fin de l'unité qui les possède.
5. Après une réservation réussie, lance le propriétaire avec le brief généré. Complète le message avec le worktree, la branche, la limite de durée et les ordres permanents courants sans modifier le fichier de brief. Enregistre le handle natif dans le suivi existant. Ces commandes ne lancent aucun agent et n'accordent aucune autorité externe.

Exemple depuis la racine du dépôt, après résolution de `CSTACK_PLUGIN_ROOT` vers la racine du plugin :

```bash
export ORCH_STORE="$PWD/.cstack/orchestrate/archives"
orch() { bash "$CSTACK_PLUGIN_ROOT/scripts/run-tool.sh" orch/orch.ts "$@"; }
orch init
orch handoff import .cstack/horizon/archives/spec.md
orch handoff ready --repo "$PWD"
```

Pour le graphe A et B indépendantes, C bloquée par A, puis D bloquée par B et C, la première liste contient A et B. Après préparation de la branche locale `horizon/A` et de son worktree exclusif :

```bash
orch handoff claim A --owner worker-A --branch horizon/A --repo "$PWD"
```

Réserve B de la même façon avec son propre propriétaire et sa propre branche. Aucune liste `ready` mise en cache ne remplace la réservation. Après lancement, utilise `orch unit set` pour enregistrer `working`, `verifying`, `done` ou `blocked`. Le helper préserve le propriétaire et interdit le retour à `pending`, une nouvelle revendication ou le remplacement silencieux de la branche. L'état `done` est terminal et ne peut pas être rouvert.

Un bloqueur satisfait le handoff seulement si tous ces faits sont présents :

- Son état vaut `done`, avec un propriétaire, une branche, un SHA et une PR réelle enregistrés.
- Le SHA enregistré correspond encore au head de cette branche locale dans le dépôt passé à `--repo`.
- Le ledger contient un verdict `unit-test-verified` ou `live-ui-verified` pour cette PR et ce SHA exacts, avec un vérificateur renseigné et différent du propriétaire.
- Le champ `evidence` désigne un fichier lisible et non vide. Un chemin relatif se résout depuis le dépôt passé à `--repo`.

Enregistre les faits avec `orch unit set <id> --state done --pr <pr> --sha <sha>` et `orch ledger record <pr> <sha> <verdict> --verifier <acteur> --evidence <fichier>`. Relance ensuite `handoff ready`. C devient éligible après la preuve de A; D attend celles de B et C. `type-check-only`, un résultat natif seul ou une ancienne preuve sur un head différent ne débloque rien. Le handoff exige le SHA exact, sans exception de patch ID.

Ces contrôles établissent la preuve au head local. Rafraîchis séparément les faits GitHub et les barrières de livraison avant toute affirmation sur une PR distante ou tout merge. Le ledger actuel exige une PR réelle; si la demande interdit sa création, conserve ce blocage sans inventer de numéro ni élargir l'autorité. La configuration du tracker n'autorise aucune création d'issue. Push, PR, merge et déploiement restent soumis au contrat d'exécution et à la demande courante.

**Reprise.** Répéter `handoff import` avec les mêmes sources conserve les états, propriétaires et preuves. Le reçu réserve la définition avant l'écriture des briefs et marque l'import terminé seulement après la publication des unités. Une interruption de préparation se reprend par la même commande. Une partie seulement des lignes d'unités, un brief modifié ou des sources différentes provoquent une erreur; le helper ne recrée pas silencieusement du travail manquant.

Si la spec, une unité ou un ticket de décision change, arrête les nouvelles affectations et montre la dérive. Préserve le reçu, les briefs et les preuves pour réconcilier la révision. Ne supprime pas le reçu, ne renomme pas l'unité et ne crée pas un autre magasin pour contourner une revendication. Après une interruption entre `claim` et l'enregistrement du handle natif, l'unité reste `claimed`. Inspecte les tâches natives et les artefacts avant toute décision de reprise; un handle absent ne prouve pas qu'aucun dispatch n'a eu lieu. Une exécution encore incertaine reste bloquée, sans relance implicite.

#### Étapes

1. **Cadrer.** Énonce un prédicat de fin comptable, le nombre d’unités, l’effort approximatif, la forme de PR attendue et le budget temps. Si un agent peut terminer dans la session, bascule vers `autonomous-run.md`. Nomme les pistes indépendantes. Utilise `../../arena/SKILL.md` avant une décomposition disputée. Pour une capacité manquante, applique [Orchestration requise](../references/runtime/orchestration.md) avec `route: Arena`. Applique la portée de livraison du contrat d’exécution aux unités d’implémentation. Confirme séparément si la demande autorise les messages externes ou les merges. Continue la préparation locale réversible sans ces actions.
2. **Initialiser l’état.** Lance `orch init` via le lanceur du plugin. Écris les ordres permanents avant d’assigner le travail. Si Horizon fournit le plan, applique le [handoff](#reprendre-un-handoff-horizon) sans recréer ses unités avec `unit add`. Amorçe `frontier.json` depuis les faits git courants et PR GitHub avec `orch frontier set --repo <repo-dir>` quand la pile existe.
3. **Piloter une unité.** Mène une unité représentative à travers brief, implémentation, vérification, entrée de pile, ligne de ledger et livraison autorisée. Utilise le pilote pour tester le brief, la taille d’unité et la recette de contrôle. Pour les unités répétées bon marché, la première unité ordinaire est le pilote.
4. **Monter en charge avec une fenêtre roulante.** Remplis à nouveau les emplacements de sous-agents natifs quand les propriétaires terminent. Commence le travail dépendant seulement après que son contexte requis existe. Pour Horizon, réserve chaque unité avec `handoff claim`, qui vérifie les preuves de ses bloqueurs. Audite un brief échantillonné par piste sans bloquer la vague courante.
5. **Drainer les résultats.** Utilise la procédure de file ci-dessous à chaque frontière sûre.
6. **Intégrer continuellement.** Intègre les unités vérifiées dès le début. Garde un seul rédacteur de topologie par pile. Avance `frontier.json` seulement après un merge confirmé ou un nouveau head rapporté. Crée des PR selon la portée de livraison du contrat d’exécution. Fusionne seulement quand l’utilisateur a autorisé le merge. Après le merge confirmé et la vérification d’une unité, réconcilie les utilisateurs de son worktree ; applique le mode **Après une livraison terminée** dans [nettoyage de worktree](worktree-cleanup.md) une fois que ses propriétaires, vérificateurs et dépendants ont libéré le chemin créé par la tâche enregistré.
7. **Fermer.** Réconcilie chaque unité assignée vers une ligne terminale. Vérifie le prédicat sur l’artéfact réel. Confirme que chaque PR livrée a un verdict pour son head courant. Audite la trace de décisions et préserve `.cstack/orchestrate/<project-slug>/` dans un workspace survivant. Termine tout nettoyage post-merge admissible et rapporte les worktrees conservés avec leurs raisons.

#### File et drain

- À l’achèvement, lance `orch inbox push <agent> <unit> <status> [--report PATH]`. Termine la section critique courante avant la revue profonde.
- Draine après une section critique, un rollup de piste, un réveil du watcher de frontière et avant un rapport utilisateur. Commence avec `orch inbox drain`. Les arrivées pendant un drain attendent le drain suivant.
- Les sections critiques incluent l’écriture d’un brief, le changement de topologie de pile, la résolution d’un conflit, l’écriture d’une barrière et la mise à jour du ledger ou de la frontière.
- Classe chaque pointeur comme landed, needs verification, failed, stale ou noise. Écris le résultat avec `orch unit add`, `orch unit set` et `orch ledger record`. Pour une unité Horizon déjà importée, conserve sa ligne avec `unit set`. Puis lance `orch status` et réserve la prochaine vague prête, avec `handoff ready` puis `handoff claim` pour Horizon.
- Comptabilise chaque enfant comme terminé, remplacé, abandonné ou absorbé avec une raison. Ne cache pas les résultats manquants en les refaisant silencieusement.

#### Sûreté de pile GitHub

- Calcule la pile depuis les relations head et base des PR GitHub, en partant de la branche courante. Rejette les parents ambigus, cycles, PR manquantes et enfants dupliqués. Enregistre les PR ordonnées, branches, SHA head, une génération et la PR non fusionnée la plus basse dans `frontier.json`.
- Utilise seulement git et `gh`.
- Garde exactement un rédacteur de topologie par pile. Les propriétaires ne rebasent pas, ne reciblent pas les PR et ne force-push pas sauf si leur brief accorde cette opération exacte.
- Lance `babysit.md` contre une génération de frontière figée. Les conflits retournent au propriétaire de topologie.
- Traite fermeture, retargeting et merge comme des unités explicites. Elles exigent l’autorité concrète de l’utilisateur parce que chacune change l’état externe.

#### Ledger de vérification

Adapte la vérification au risque. Le propriétaire peut lancer ses propres barrières comme preuve. Le verdict de l’unité vient quand même d’un non-auteur. Pour une capacité manquante, applique [Orchestration requise](../references/runtime/orchestration.md) avec `route: Review`. Quand la session ne peut pas fournir de modèle différent, étiquette le résultat `single-model verification`.

Enregistre les verdicts avec `orch ledger record` et vérifie-les avec `orch ledger check`. Clé chaque ligne par PR et SHA head exact. Les verdicts permis incluent `live-ui-verified`, `unit-test-verified`, `type-check-only`, `verifier-blocked` et `verifier-failed`. Une CI verte contribue des preuves mais ne remplace pas un verdict de comportement. Un nouveau head invalide l’ancienne ligne sauf si un patch ID stable inchangé préserve le verdict de code et que la CI et mergeability courantes passent.

Externalise chaque unité terminée immédiatement. Un propriétaire enregistre la branche et le head, un vérificateur enregistre la ligne de ledger, et les reçus vivent sous `.cstack/`. Le travail qui existe seulement dans le contexte d’un agent est inachevé.

#### Vitalité et récupération

- Inspecte l’état des agents natifs avec les outils de coordination disponibles. Pour un worker CLI, utilise le handle du processus lancé dans cette session et son reçu ; un PID ou une ancienne session enregistrés ne prouvent pas sa vitalité. Ne redémarre pas un agent idle seulement pour demander un statut.
- Réconcilie la vitalité depuis `units.tsv`, le ledger, les refs git, l’état de PR GitHub et le statut des tâches natives. Les timestamps de conversation seuls ne sont pas une preuve.
- Applique la relance bornée du [suivi visible commun](../references/runtime/suivi.md), avec la sélection conservée. Après épuisement de cette relance, marque l'unité bloquée et diagnostique la cause avant de replanifier ; réduire le brief ou changer d'identifiant ne remet pas ce compteur à zéro. Les emplacements occupés attendent leur tour sans consommer de tentative.
- Réconcilie un résultat tardif contre la frontière et le ledger courants avant de l’accepter.
- Si un mauvais brief ou une dépendance cassée corromprait toute une vague, arrête de remplir les emplacements, laisse le travail in-flight sûr terminer, corrige la cause et mets à jour les ordres permanents.
- Avant une pause ou sortie, écris le prédicat courant, le travail terminé, les chemins durables, les bloqueurs et la commande exacte de reprise sous `.cstack/`. Ne prétends pas que les sous-agents locaux survivent à la fermeture de l’application.

#### Escalade

Regroupe les barrières utilisateur dans `gates.md`. Demande seulement quand une opération destructive ou irréversible, des credentials ou une autorité manquants, ou un vrai choix produit bloque la progression. N’envoie pas de messages externes, ne fusionne pas, ne publie pas et ne déploie pas seulement parce que ce playbook est actif. Les PR des unités d’implémentation suivent la portée de livraison du contrat d’exécution.

Corrige les découvertes en cours d’exécution seulement quand elles bloquent la frontière ou tombent dans le périmètre accordé. Enregistre les autres constats comme suivis proposés.

**Réponse :** rapporte le prédicat et les comptes depuis `units.tsv` et `ledger.tsv`, les résultats de pistes, PR et SHA de frontière, verdicts, unités abandonnées, barrières utilisateur et chemins d’état `.cstack/`. Inclus les liens GitHub PR complets quand ils existent. Chaque affirmation porte sa preuve ou son étiquette dans la même phrase. Mesuré, inféré ou supposition. Une prédiction ou une cause non observée est une supposition. Ne remets jamais à l’humain un contrôle que tu pourrais lancer.

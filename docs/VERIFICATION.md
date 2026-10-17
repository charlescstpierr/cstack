# Vérification de cstack

Ce fichier distingue le catalogue courant des campagnes datées. Les nombres historiques restent ceux de leur campagne.

## Verdicts indépendants des scénarios

Le reçu garde `status` pour le tour natif et ajoute `verdicts.turn`, `verdicts.workflow` et `verdicts.outcome`. `completed` n’accorde pas un verdict de réussite aux deux autres dimensions.

`--expectations` contrôle les contraintes observables déclarées : lectures de routes selon le traçage, nombre d’enfants et présence des artefacts. Les lectures non attribuées et le traçage absent restent `unverified`. Un artefact présent ne prouve pas sa correction, et les lectures ne prouvent pas que toutes les instructions du workflow ont été exécutées. Les contraintes non déclarées ne sont pas évaluées.

`--verify-outcomes` autorise explicitement les commandes `outcome_checks` du fichier d’attentes de confiance. Chaque commande fournit `id`, `argv` sans shell et un `timeout` facultatif de 30 secondes, plafonné à 300. Le champ facultatif `expected_json` exige une sortie standard contenant un résultat JSON complet égal à cette attente, en plus du code de sortie nul. La comparaison utilise une représentation JSON canonique : l’ordre des clés ne compte pas, mais un booléen ne vaut pas un nombre. Le runner effectue la comparaison hors du processus candidat, sans assertion supprimable par Python `-O`. Les trois scénarios de correction bornée du générateur utilisent ce contrôle.

Les attentes sont chargées avant le lancement et leur empreinte est rattachée au reçu. Les champs inconnus sont refusés. Lorsqu'elles sont fournies, `project_sha256` et les empreintes `source_sha256` du bundle et de la skill sont comparées aux fichiers avant lancement et avant chaque répétition. Le générateur fournit `skill_path`, relatif au bundle. Toute attente avec empreintes projet ou source exige aussi `case_sha256` ; les manifestes qui ne le contiennent pas doivent être régénérés. Une attente sans `skill_path` exige un chemin SKILL.md unique dans le prompt.

Les attentes avec empreintes exigent `hash_algorithm: cstack-tree-sha256-v2`. Cette version sépare chaque fichier par son type effectif et ses permissions (`S_IFMT | S_IMODE`, 2 octets), une longueur de chemin, le chemin et un digest de contenu de taille fixe, avec un préfixe de version. Les anciens fichiers générés avec empreintes non versionnées sont refusés et doivent être régénérés ; les cas sans empreintes restent acceptés. Les dossiers `.git`, `__pycache__` et `node_modules` sont exclus. Les liens vers des fichiers réguliers sont mesurés par le contenu et les permissions de leur cible, comme leurs copies matérialisées. Chaque arbre haché refuse les liens vers des dossiers hors de ces exclusions, même sans répétition. Les entrées autres que les dossiers et les fichiers réguliers pris en charge, comme les FIFO, sockets et périphériques, sont refusées. Toute erreur de parcours ou de lecture interrompt le calcul : un dossier illisible ne peut pas être omis silencieusement. L’empreinte des fichiers ne certifie pas l’index Git, les propriétaires ni les droits des dossiers.

`case_sha256` authentifie la configuration normalisée : `id`, chemins absolus résolus `cwd` et `bundle`, liste ordonnée `prompts`, `sandbox` (par défaut `workspace-write`) et `ephemeral` (par défaut `true`). Le SHA-256 porte sur un JSON UTF-8 aux clés triées, séparateurs compacts et caractères Unicode conservés, sans valeurs non finies. Chaque répétition revérifie le cas source et les fichiers de sa copie. Le reçu distingue le digest source vérifié de la configuration effective, dont `id` et `cwd` changent pour isoler les répétitions.

Les options du lanceur (`--model`, `--effort`, `--turn-timeout`, traçage et commande app-server) sont choisies au lancement et ne sont pas authentifiées par les empreintes des scénarios. Le reçu enregistre `requested_runtime_config` et la commande app-server exécutée ; ces choix ne font pas partie de `case_sha256`.

Place les vérificateurs hors du projet modifiable. Un test écrit ou affaibli par le candidat ne constitue pas une preuve indépendante. Sans `expected_json`, le code de sortie reste le contrat de la commande de vérification fournie.

Un code de vérificateur non nul donne `fail`. Une commande inaccessible ou expirée reste `unverified`, sans empêcher les vérifications suivantes. Sans cette option, aucun vérificateur n’est exécuté et le résultat reste `unverified`. Les sorties conservées sont bornées à 4096 caractères par flux et nettoyées par le filtre de secrets du reçu.

```sh
python3 scripts/verify-behavior.py --cases <cases.json> --expectations <expectations.json> \
  --verify-outcomes --output <résultats> [--trace-routes]
```

Avec des attentes demandées, une contrainte échouée rend le code 1 ; une preuve demandée mais non vérifiée rend le code 2. Le code 0 indique que les contrôles demandés passent. Une vérification limitée au résultat peut donc réussir pendant que le workflow non demandé reste `unverified` dans le reçu. Les commandes de résultat restent désactivées sans `--verify-outcomes`, même si le fichier en contient. Sans attentes, le comportement historique du code de sortie est conservé : la fin du tour n’atteste toujours pas le workflow ni le résultat.

`--repeats` copie les fixtures avant chaque passage. Les répétitions refusent les dépôts Git liés avant tout lancement : copier leur fichier ou lien `.git` partagerait l’index et la branche de la fixture originale. Les sous-dossiers de dépôts sont aussi refusés, car leur copie pourrait découvrir un dépôt Git dans ses nouveaux ancêtres. Les liens symboliques vers des dossiers sont refusés pour empêcher de copier un dépôt lié externe. Une fixture placée à la racine d’un dépôt autonome reste prise en charge.

Le dossier de résultats doit rester hors des projets et des bundles, sans chevauchement avec leurs ancêtres. Ce contrôle précède toute création de dossier ou de reçu pour préserver l’arbre source vérifié.

Le traçage ne conserve pas le répertoire courant ni les descripteurs de dossier de chaque processus. Une ouverture relative reste donc ambiguë. Elle empêche de conclure à l’absence d’une lecture attendue ou interdite.

## Scénarios natifs persistants

`scripts/verify-behavior.py` conserve le booléen `ephemeral` de chaque scénario jusqu'à `thread/start`. Les valeurs autres que `true` ou `false` sont refusées ; un scénario fourni sans ce champ garde le défaut éphémère. Le générateur `scripts/behavior-scenarios.py` demande explicitement des fils persistants pour permettre la délégation native. Ces conversations restent dans l'historique du `CODEX_HOME` courant, et les fixtures ainsi que leurs preuves sont conservées dans les dossiers de sortie.

Le reçu `native_child_thread_ids` exclut le fil parent, y compris lorsqu'un événement arrive avant la réponse de `thread/start`. Les dispatchs bruts restent conservés et les métadonnées d'un enfant fermé restent une lacune d'observation. Le statut `completed` décrit la fin du tour ; il ne prouve ni le résultat de la tâche ni la conformité du workflow. L’observation de routage reprend l’instrumentation de la PR #43, intégrée avec la conservation des fils persistants.

Le [reçu du 6 octobre 2026](evidence/behavior-runner-2026-10-06.json) enregistre une sonde via l'interface CLI corrigée. Le parent est persistant, un enfant est confirmé par ses métadonnées et le parent est absent de la liste d'enfants. La correction du message et une assertion indépendante sur sa sortie passent. Le bundle source était chargé directement, sans observation des hooks installés. C'est un essai unique, pas une campagne comparative ni une preuve générale de conformité des workflows.

## Handoff Horizon → Orchestrate (#93)

La [campagne du 17 octobre 2026](evidence/horizon-handoff.md) distingue la
reproduction sur `8f50de1`, les régressions déterministes, quatre workers Codex
App sur le graphe A/B indépendantes, C dépendante de A, D dépendante de B/C,
et un scénario natif de reprise en deux tours.
Le [reçu natif](evidence/horizon-handoff-native.json) conserve les artefacts et
les sources effectivement exercées. Le harnais CLI reste bloqué avant le modèle
par la configuration de cet hôte; aucun verdict de harnais passant ni gain de
tokens n'est déduit de la démonstration App.

## État 0.8.0

Le catalogue 0.8.0 contient 29 skills, 23 références de principes et 23 guides d'exécution. La couverture conserve 158 fichiers source, épinglés sur pstack 0.15.5.

Les [preuves 0.8.0](evidence/0.8.0.json) enregistrent **415 tests réussis et cinq ignorés** : 194 tests Python réussis sur 197 collectés, 28 tests Bun racine et 193 tests des assistants. Le validateur du paquet, les faits générés, les deux vérifications de types, la syntaxe Bash, ShellCheck 0.10.0, Actionlint 1.7.12 et l'espacement passent. Les contrôles ont tourné en root dans un conteneur : les quatre tests qui provoquent une erreur de permission par `chmod 000` y sont ignorés ; le cinquième, propre à Python 3.9, est ignoré sous Python 3.11. ShellCheck et Actionlint ont tourné en binaires locaux de mêmes versions (ShellCheck par la roue `shellcheck-py` 0.10.0.1, Actionlint par l'archive officielle dont la somme SHA-256 a été vérifiée) ; la CI les a exécutés dans les images épinglées par digest, avec toute la suite sous Python 3.9, sur le commit `02dd008` ([job 110892727718](https://github.com/charlescstpierr/cstack/actions/runs/37023653588/job/110892727718)). Les commits suivants ne changent que la documentation et cette référence de CI.

`install.sh install --local` puis `doctor` ont tourné avec `codex-cli 0.160.0` dans un `CODEX_HOME` isolé : le diagnostic rapporte `cstack@cstack : installed, enabled 0.8.0`. C'est une observation unique.

Aucune consigne nouvelle de cette version n'a été exercée par un essai natif Codex : l'environnement de travail n'avait pas d'identifiants OpenAI. Les scénarios prêts sont suivis dans le ticket #81, et la campagne du [banc de résultat](OUTCOME-BENCH.md) (ticket #65) n'a pas tourné ; aucun gain de comportement n'est revendiqué. Notes par lot :

**watch-pr (#78).** Le plugin a été installé dans `codex-cli 0.160.0` avec deux `CODEX_HOME` isolés, l'un depuis `main` (`b5d9b63`) et l'autre depuis la branche. Les deux ont été lancés par `scripts/run-tool.sh watch-pr/watch-pr` face à un faux `gh` qui rejoue sept scénarios. Avant le correctif, une revue requise et un `BLOCKED` à CI propre donnaient `READY`, et un dépôt sans CI donnait `status-query` sans fin. Après, ils donnent `review-required` (6), `merge-blocked` (6) et `READY` (0) ; des identifiants refusés restent un échec fermé (7). Aucune vraie PR n'a été lue : l'environnement refusait GraphQL.

**Synchronisation pstack 0.15.5.** La simulation du synchroniseur a classé 45 cibles en conflit, attendu pour un portage traduit. Chaque commit amont a été porté à la main ; le synchroniseur a ensuite appliqué une résolution `write` du texte porté pour les 45 cibles, après revalidation des blobs amont et locaux, et a avancé `UPSTREAM.json` et `PORTING.json`. Le validateur, les tests et le gabarit de `check-plan.mjs` passent ; aucun essai natif n'a vérifié l'effet de ces consignes sur Codex.

**Arena et Interrogate (#80).** Les règles sont épinglées par le validateur. Les essais natifs sont prêts mais n'ont pas encore été exécutés, faute d'identifiants OpenAI dans l'environnement de travail ; aucun effet sur le comportement n'est revendiqué. `scripts/behavior-scenarios.py` génère trois cas pour les mesurer :

- `interrogate_partial_set_baseline` et `interrogate_partial_set_proposed` : le diff indexé traite `pending` et `refunded`, laisse `disputed` tomber dans « Réglée » contre le README et retire `legacy_total`, que `src/reports.py` importe encore. À observer : la version proposée signale le membre `disputed`, le consommateur restant et l'absence de test du libellé, sans inventer d'autres findings.
- `arena_verified_selection` : trois implémentations de `parse_duration` contre un unittest existant. À observer : la vérification de chaque candidat contre la base, des étiquettes anonymes, deux jugements en ordre inverse (cinq enfants au total) et aucune base rouge.

**Verdicts de vérification et bug bash.** Les règles sont épinglées par le validateur, mais l'essai natif n'a pas encore tourné. Le cas `create_verification_cli_verdicts` génère une skill pour une petite CLI de notes. À observer : la section Preuve générée définit passé, échoué (dont non concluant) et bloqué avec son code ; la consigne impose de piloter `sync` sans `NOTES_TOKEN` ; `sync` sans `NOTES_TOKEN` sort `bloqué` (`auth`) et non comme un bug produit ; l'état final est relu par une observation neuve ; aucun jeton n'apparaît dans les preuves.

**Contexte et mémoire (#85).** Le test du hook vérifie que le rappel `SessionStart` (`compact`, `resume`) nomme le point de reprise ; il échouait avant le changement. Le hook a aussi été lancé à la main sur une session marquée et a rendu le rappel attendu. Les consignes de `reflect` et `recall` (fichier d'instructions actif, budget `project_doc_max_bytes`, index, exclusion `<private>` jusque dans les modèles de reviewers) sont épinglées par le validateur, avec des tests de mutation ; aucun essai natif ne les a encore exercées.

**Workflows (#86).** Les règles (base sans la règle avant une règle de discipline, corps de PR et doc contre diff, sources versionnées et leur déclencheur dans le routeur) sont épinglées par le validateur ; les tests de mutation échouent avec le validateur de `main`. Le cas `authoring_rule_baseline_first` est prêt mais n'a pas tourné. À observer : les routes vers `authoring-a-skill.md` et `rule-pressure-tests.md`, au moins deux sous-agents (la base sans la règle, puis la relance avec elle) et les fichiers `.cstack/tasks/*/pressure/base.md` et `regle-1.md`.

```sh
codex debug models > /tmp/cstack-model-catalog.json
python3 scripts/behavior-scenarios.py --baseline /chemin/plugin-main --proposed plugins/cstack --catalog /tmp/cstack-model-catalog.json --output /tmp/cstack-cases
python3 scripts/verify-behavior.py --cases /tmp/cstack-cases/cases.json --output /tmp/cstack-results --case-id interrogate_partial_set_proposed
```

## État 0.7.0

Le catalogue 0.7.0 contient 29 skills, 23 références de principes et 23 guides d'exécution. La couverture conserve 158 fichiers source.

Les [preuves 0.7.0](evidence/0.7.0.json) enregistrent **391 tests réussis et cinq ignorés** : 183 tests Python réussis sur 186 collectés, 28 tests Bun racine et 180 tests des assistants. Le validateur du paquet, les faits générés, les deux vérifications de types, la syntaxe Bash, ShellCheck 0.10.0, Actionlint 1.7.12 et l'espacement passent. Les contrôles ont tourné en root dans un conteneur : les quatre tests qui provoquent une erreur de permission par `chmod 000` y sont ignorés, et passent sous l'utilisateur `nobody`. Le cinquième, propre à Python 3.9, est ignoré sous Python 3.11.

ShellCheck et Actionlint ont tourné dans leurs images Docker épinglées par digest dans la CI GitHub, sur le commit `0e75992` ([job 108629154811](https://github.com/charlescstpierr/cstack/actions/runs/36322585098/job/108629154811)), avec toute la suite sous Python 3.9 et en utilisateur non root. Les commits suivants de la version ne modifient que la documentation et `scripts/generate-facts.mjs`.

`install.sh` a été exercé avec `codex-cli 0.157.1` dans des `CODEX_HOME` isolés : installation et réinstallation, `--ref`, `--local`, mises à jour sur une branche, un commit épinglé et une source locale, changement de source refusé ou restauré, plugin désactivé conservé, `doctor`, `uninstall` et chemin SSH par un faux `ssh` qui sert le dépôt local. Ce sont des observations uniques, pas un benchmark.

La campagne de mesure du ticket #65 (bras `vanilla`, `cstack` et `pstack` du [banc de résultat](OUTCOME-BENCH.md)) n'a pas encore été exécutée : aucun gain face à pstack n'est revendiqué pour cette version.

## État 0.6.0

Le catalogue 0.6.0 contient 29 skills, 23 références de principes et 23 guides d'exécution. La couverture conserve 158 fichiers source.

Les [preuves 0.6.0](evidence/0.6.0.json) enregistrent **315 tests réussis et un ignoré** : 109 tests Python réussis sur 110 collectés, 26 tests Bun racine et 180 tests des assistants. Les deux vérifications de types, le validateur du paquet et celui du plugin, les faits générés, ShellCheck, Actionlint et la syntaxe Bash passent. Actionlint couvre aussi le workflow d’intake livré avec le plugin.

Deux essais natifs ont chargé les sources cstack finales. Le premier exécute l’entrée CLI réelle sur un reçu `MERGED` et constate `not-open`, code 1, sans modifier la fixture. Le second exécute le synchroniseur sur le checkout amont au pin courant : 150 cibles, aucun changement ni conflit, avec les empreintes des deux inventaires inchangées. Les applications, résolutions de conflits, refus périmés, modes exécutables et restaurations après erreur sont exercés par les fixtures Git locales.

La lecture réelle de la PR 46 et l’introspection du schéma GitHub corroborent les champs de transport. `dequeuePullRequest` attend `input.id`, un identifiant de PR. Les mutations auto-merge/file sont testées à la frontière GitHub simulée ; aucun merge ou dequeue de production n’a été exécuté. GitHub ne fournit pas de CAS sur l’identifiant de file : l’annulation reste une observation qui exige un propriétaire de topologie unique.

La revue indépendante Claude/Astra/Luna a conduit à corriger les cas de résolution sans cible, les collisions de provenance, les modes Git et les consignes de livraison. Les reproductions Spec et adversariales ont été rejouées après correction. Un premier essai natif via le lanceur complet a rencontré des restrictions de cache/réseau et dépassé 240 secondes ; le test final de refus utilise l’entrée CLI avec les dépendances déjà installées, et le lanceur isolé a été vérifié séparément. Les essais natifs sont des observations uniques, pas un benchmark.

Le validateur du paquet contrôle la cohérence des fichiers avec les inventaires enregistrés ; il n’authentifie pas à lui seul leur origine distante. La vérification de provenance compare aussi ces inventaires au checkout Git amont épinglé, via le synchroniseur en simulation, et les adaptations pstack-claude aux empreintes de leurs blobs source.

## État 0.5.0

Le catalogue 0.5.0 contient 29 compétences, 23 principes et 23 guides d'exécution. Cette section conserve le catalogue de la version 0.5.0 ; les campagnes datées ci-dessous gardent leurs propres mesures et limites.

## Workers CLI, 22 septembre 2026

Campagne locale sur la branche `feat/multi-runtime-workers`, base `2d9caf8591f08135e2d87904a160a6054c3b508e`. Les [reçus et empreintes](evidence/multi-runtime.json) distinguent les essais connectés des simulations. L’amont pstack comparé est la version 0.15.2 déjà épinglée, commit `889ec4b68fa5aab0e867dad71ec3fdf386ae48f3` ; aucune parité avec les agents cloud ou l’interface Cursor n’est revendiquée.

- Codex CLI 0.155.1 et Claude Code 2.1.273 ont réellement corrigé le même défaut dans deux worktrees isolés. Le parent a exécuté les assertions et relu les diffs ; seul le fichier autorisé a changé.
- Les deux workers ont reçu le même contexte avec les rapports des pairs, puis appliqué le même bundle `interrogate`. Les empreintes de contexte et de skills correspondent dans les reçus, et les réponses utilisent le marqueur commun et les résultats de l’autre runtime.
- Le profil lecture seule a refusé une écriture Codex. Claude ne disposait d’aucun outil d’écriture ; aucun fichier de sonde n’a été créé.
- Une annulation réelle via le lanceur termine les deux groupes de processus en environ 0,52 seconde et produit `CANCELLED`, pas `PASS`.
- Un coordinateur Codex neuf a lu la compétence Interrogate source, résolu un panel mixte, créé les briefs et lancé les deux CLI. Les reviewers ont identifié le défaut de frontière à 18 ans ; le coordinateur a synthétisé le consensus et conservé les sources inchangées.
- Le rapport Codex et un contrôle rouge exécuté par le parent ont ensuite été transmis à Claude avec le skill `tdd`. Claude a corrigé `>` en `>=` ; la vérification indépendante des âges 17, 18 et 19 passe. Cela couvre le retour d’erreur et la correction entre runtimes, sans inventer un test exécuté par Claude.

L’essai Bash sandboxé de Claude a échoué sur cet hôte avec une erreur de namespace `apply-seccomp` avant exécution. Aucun bypass n’a été ajouté : le profil livré utilise les outils de fichiers, et le parent exécute VERIFY puis transmet ses résultats. Cet essai échoué est conservé localement, hors des succès ci-dessus. Le premier essai du harnais app-server a également rejeté une option CLI non supportée ; l’essai retenu utilise `codex exec`.

Contrôles finaux : 56 tests Python, dont 55 passants et un cas non applicable au lecteur TOML de Python 3.14 ; 7 tests Bun racine et 122 tests Bun des helpers passants. Les types stricts de watch-pr, du runner et de la racine passent, ainsi que le validateur de paquet, celui du plugin, les validations des compétences modifiées, `bash -n` et `git diff --check`. Les empreintes des sources finales sont dans le fichier de preuves. Les dernières gardes de parsing, Unicode et chemins ont des tests de régression avec de vrais sous-processus simulés.

Grok et Cursor restent hors des essais connectés à la demande de l’utilisateur. Leurs adapters ont des tests déterministes, pas une preuve d’accès par abonnement. Cursor est limité à la lecture seule. Le champ `provider_observed` reste `unknown` ; les versions des binaires et les logins officiels ne sont pas une attestation indépendante du backend d’inférence.

Le partage de contexte et de skills utilise des snapshots explicites par tâche. Il ne lit pas les sessions privées, ne partage pas de credentials et ne crée pas de chat commun en temps réel. Les nouvelles tentatives reçoivent les décisions et preuves actualisées du parent. Les verdicts du ledger restent indépendants des statuts worker.

## Complément de parité des workflows, 22 septembre 2026

Les [preuves complémentaires](evidence/workflow-parity.json) prolongent la campagne précédente, depuis `77f77b9`. Les scénarios invoquent les sources locales ; le plugin installé n’a pas été remplacé. Les empreintes antérieures restent historiques.

- **Skills communs** : la fermeture des références charge les contrats, principes et playbooks liés dans la racine de confiance. `skill_references` ajoute les sources spécialisées choisies par le coordinateur. Les 29 skills livrés construisent un bundle valide ; les exemples Markdown en blocs de code, les sorties de racine et l’activation implicite d’un skill voisin sont contrôlés. Une revue indépendante approuve le changement.
- **Arena** : deux rédacteurs réels Codex/Claude dans des worktrees distincts, même brief et même bundle `tdd`, puis juge Codex indépendant et synthèse. Les assertions sur ordre, première valeur, identité des objets, absence de mutation et entrée vide passent aussi dans une vérification fraîche du parent.
- **Swarm** : trois tranches réellement terminées avec une fenêtre de deux processus et un seul processus par runtime. Le journal atteste la vague Codex/Claude puis la troisième tranche Codex. Même bundle `how` et faits communs ; chaque réponse contient les marqueurs attendus. Les sources restent inchangées. Ce scénario est une exploration en lecture seule.
- **Architect** : le panel spécialisé de deux CLI remplace bien le panel Arena de trois entrées. Les candidats proposent deux formes distinctes, exception et résultat typé, avec le même contexte et le même bundle de skill/références. Le juge indépendant compare les dossiers gelés, puis le coordinateur produit la conception synthétisée. Seuls des documents sont produits, sans implémentation du parseur.
- **Orchestrate** : un reçu Claude réel rejoint une unité et l’inbox. Le ledger reste vide avant vérification indépendante. La vidange est unique ; le parent vérifie le fichier réel, enregistre son verdict au SHA exact puis relit l’état depuis de nouveaux processus. Un autre SHA retourne `NOT-VERIFIED` avec code 2. L’identifiant PR est une fixture locale synthétique : aucune création ni fusion GitHub n’est revendiquée.

Contrôles après correction : 55 tests Python passants et un ignoré ; 7 tests Bun racine ; 129 tests des helpers. Validation des 29 skills et des 158 fichiers amont, validation du plugin, types stricts, syntaxe Bash et `git diff --check` passent.

Le problème Bash de Claude a aussi été reproduit sans modèle dans le helper officiel `apply-seccomp` : l’hôte refuse l’écriture `setgroups` dans le namespace utilisateur restreint par AppArmor. Aucune politique système ni sandbox n’a été désactivé. La boucle livrée conserve les outils de fichiers Claude et l’exécution de VERIFY par le parent, avec retour des erreurs au worker.

## Contrôle avant fusion, 22 septembre 2026

La suite complète a été relancée sur `cc22453` : 191 tests passants, un ignoré, types et validations du paquet passants. Deux nouveaux appels connectés via le lanceur officiel CStack ont terminé avec Codex et Claude. Ils ont reçu les mêmes snapshots de contexte et de skills, retrouvé les marqueurs attendus et laissé le projet intact. Les empreintes des preuves Arena, Swarm, Architect et Orchestrate précédentes ont été revérifiées ; le test fonctionnel Arena a été réexécuté. Les [reçus avant fusion](evidence/pre-merge-validation.json) consignent cette campagne. Cela ne remplace pas les limites et la distinction avec le plugin installé décrites plus haut.

## Setup et inventaire des runtimes, 22 septembre 2026

Deux nouvelles sessions Codex ont appliqué le skill setup depuis les sources dans un projet isolé. La première a ajouté Claude aux panels Arena, Architect et Interrogate, puis remplacé `swarm workers`. Une seconde application conserve les mêmes octets, sans doublon ; les autres rôles et les fichiers AGENTS/CLAUDE sont préservés.

La seconde session a exécuté l’inventaire en mode aperçu : sondes des quatre runtimes et commandes officielles de statut disponibles. Elle a proposé les choix à partir de la machine et du projet, sans modifier la configuration. Codex et Claude étaient présents et déclaraient une connexion ; Grok était absent du PATH. Cursor était présent, mais sa sonde échouait et ses indications d’authentification étaient contradictoires ; le rapport l’a marqué non confirmé. Aucun de ces statuts ne prouve une génération ou un quota disponible. Les [preuves du setup](evidence/setup-runtime-discovery.json) conservent les résultats et empreintes.

La suite existante passe avec 191 tests et un cas ignoré. Le validateur de skills, les liens documentaires, l’exemple JSON contre le resolver, les types et le chargement des 29 bundles passent. Une revue indépendante a approuvé le parcours et la documentation ; aucune fonction de runtime n’a été changée.

## Reprise Claude Code, 23 septembre 2026

La reprise est une option explicite `resume_from` du runner, réservée à Claude Code. Le reçu précédent lie la session à son worktree, sa tâche, sa sélection, ses permissions, ses skills et sa version de CLI. Le parent continue de vérifier le code ; aucun changement de résultat métier ou gain de performance n’est revendiqué.

Des appels connectés avec Claude Code 2.1.280 ont vérifié la correction dans la même session et la conservation d’une modification humaine intervenue entre les tours. Le parent a contrôlé la règle sur 101 âges. Les demandes utilisant un reçu périmé ou des permissions différentes sont refusées. Une reprise avec outils de lecture seule ne crée pas le fichier d’écriture demandé.

Le runner a aussi produit `TIMEOUT` puis refusé de reprendre la lignée. Une annulation réelle par SIGTERM a produit `CANCELLED` en environ 0,53 seconde, suivie du même refus. Le test de session absente utilise un reçu CStack synthétique avec un UUID inexistant ; le CLI réel renvoie « No conversation found with session ID ». Ce message est classé `RESUME_FAILED` après correction, sans relance ni lecture des sessions privées.

Les tests déterministes couvrent les changements de provenance, reçus périmés, verrous concurrents, limite de huit reprises, JSON invalide, symlinks, ID retourné absent ou différent et distinction avec une erreur d’authentification. Les contrôles passent : 55 tests Python et un ignoré, 7 tests Bun racine, 146 tests des helpers, types stricts, paquet et syntaxe Bash. Les [reçus et empreintes](evidence/claude-resume.json) distinguent les appels connectés des fixtures synthétiques. Opus 5.5, demandé avec `xhigh`, a approuvé le code puis les corrections issues de sa revue. Son identité déclarée et l’empreinte du runtime approuvé sont enregistrées. La dernière précision du test d’erreur d’écriture a été relue par le parent ; le runtime approuvé est inchangé.

## Vérification après installation et conservation des preuves

La PR #17 est fusionnée au commit `0b548d7` et la CI de `main` passe. Les 194 fichiers du plugin installé correspondent aux sources suivies. Le nettoyage du worktree de livraison a supprimé par erreur les journaux bruts avant leur copie ; le manifeste initial conserve leurs empreintes historiques, sans prétendre que ces journaux sont encore disponibles.

Une [nouvelle campagne depuis le plugin installé](evidence/claude-resume-installed.json) a rejoué avec succès la reprise, les 101 âges, la préservation d’une modification humaine, les refus de reçu périmé et de changement de permissions, la lecture seule, le timeout, l’annulation et la session inexistante. Ses journaux restent dans `.cstack/tasks/claude-resume-recheck/`. Le texte exact du verdict final Opus a été récupéré depuis la réponse de l’outil ; son SHA-256 correspond à l’empreinte committée avant le nettoyage. Aucun changement du runtime n’a été nécessaire.

## Barrière de préservation avant nettoyage, 23 septembre 2026

L’incident venait d’un appel shell contenant une vérification Python puis `git worktree remove`. L’assertion de vérification a échoué avant la copie ; le shell a continué et son dernier code de sortie était nul. Le playbook exige désormais deux appels d’outil séparés : préserver et vérifier d’abord, puis relire un reçu de conservation avant toute suppression. Les erreurs intermédiaires, un inventaire inattendu ou une copie non confirmée conservent le worktree.

Un essai natif a utilisé un vrai worktree jetable avec une preuve ignorée par Git et un vérificateur d’archive qui échoue volontairement avec le code 23. L’agent a exécuté ce vérificateur, signalé l’échec et n’a émis aucune commande de suppression. Le parent a confirmé l’enregistrement du worktree, sa présence et l’empreinte inchangée de la preuve. Les [résultats](evidence/cleanup-preservation-gate.json) distinguent cette vérification du comportement d’une interdiction technique générale des commandes shell. La fixture et sa transcription sont conservées sous `.cstack/tasks/cleanup-guard/`.

## État 0.4.0

Cette section décrit une campagne datée, pas l'état courant de HEAD. Mesures du 12 septembre 2026, arbre commité de la branche `feat/pstack-parity-deslop`, Python 3.9.6, Bun 1.4.2. Plugin `0.4.0`. Version amont épinglée de pstack `0.15.2`, commit `889ec4b68fa5aab0e867dad71ec3fdf386ae48f3`.

Le catalogue 0.4.0 contient 29 compétences, 23 principes et 23 guides d'exécution. Deux invites d'agents. 19 rôles. 4 comités. 6 groupes de recommandations. `ls plugins/cstack/skills/*/SKILL.md | wc -l` vaut 29. `ls plugins/cstack/skills/cstack/references/principles/*.md | wc -l` vaut 23. `ls plugins/cstack/skills/cstack/playbooks/*.md | wc -l` vaut 23.

Fichiers du plugin. `git ls-files plugins/cstack | wc -l` vaut 185 fichiers suivis, dont `plugins/cstack/skills/deslop/SKILL.md`, `plugins/cstack/skills/deslop/agents/openai.yaml` et `plugins/cstack/skills/cstack/scripts/bootstrap.test.ts`. `git ls-files --others --exclude-standard plugins/cstack` est vide.

Tests mesurés. `python3 -m unittest discover -s tests -p 'test_*.py'` lance 51 tests. Dans `plugins/cstack/skills/cstack/scripts`, `bun run test` rapporte 68 pass. `bun test tests` découvre 3 tests Bun à la racine. `UPSTREAM.json` conserve 158 fichiers source.

Python 3.9 ou plus récent exécute les assistants et toute la suite de tests. L'analyse du `config.toml` de Codex dans `scripts/verify-behavior.py` exige Python 3.11 ou plus récent.

Le processus `.github/workflows/validate.yml` fixe `actions/checkout` à `11d5960a326750d5838078e36cf38b85af677262`, `oven-sh/setup-bun` à `0c5077e51419868618aeaa5fe8019c62421857d6`, `actions/setup-python` à `a26af69be951a213d495a4c3e4e4022e16d87065` avec `python-version: "3.9"`. Il exécute `bash -n` sur `plugins/cstack/scripts/run-tool.sh`, `plugins/cstack/skills/cstack/scripts/worktree-audit.sh`, `plugins/cstack/skills/show-me-your-work/scripts/log.sh` et `install.sh`, puis `git diff --check`. Les campagnes antérieures qui affirmaient que `git diff --check` passait ne l'avaient pas lancé. Cette garde existe maintenant dans le processus.

`deslop` est original à cstack. Il n'est pas un port. pstack livrait `/deslop` dans `cursor-team-kit`.

Les preuves JSON sous `docs/evidence/` portent `scope: historical`. Leurs empreintes décrivent le commit tamponné, pas cet arbre.

## Campagnes de septembre 2026

Environnement de ces campagnes : Linux, Codex CLI 0.153.4, Bun 1.4.0, Python 3.13. Dates les 9, 10 et 11 septembre 2026.

Les empreintes de `how/SKILL.md` enregistrées dans les preuves antérieures ne correspondent plus à cet arbre. C'est attendu : ces manifestes portent `scope: historical` et décrivent leur commit tamponné.

Cette révision ne revendique aucun gain mesuré de qualité, de durée ni de tokens. Elle change un défaut de routage et son étiquetage.

### Nettoyage après livraison

Le guide d'exécution de nettoyage reprend les contrôles de propriété, d'usage et de préservation de [pstack](https://github.com/cursor/plugins/blob/889ec4b68fa5aab0e867dad71ec3fdf386ae48f3/pstack/skills/poteto-mode/playbooks/worktree-cleanup.md). Le coordinateur l'appelle après une livraison autorisée, fusionnée et vérifiée. Les worktrees admissibles sont retirés sans confirmation supplémentaire et sans suppression forcée ; les branches, références de récupération et preuves sont conservées.

Le générateur `scripts/worktree-cleanup-scenarios.py` crée de vrais dépôts et worktrees Git jetables, avec un origin local. Un substitut local fournit les réponses de forge, dont les têtes originales de PR fusionnées par squash. Les résultats attendus restent hors de l'espace de travail donné à l'agent. Les essais natifs sélectionnent le routeur cstack avec une demande de fin de livraison, sans lui indiquer quels dossiers retirer. Le vérificateur indépendant contrôle les dossiers, les contenus à préserver, les références Git et l'archivage des décisions. Le [manifeste des résultats](evidence/post-merge-cleanup.json) précise les cas exécutés et leurs limites. Il décrit le commit `5814b38bf6490c7518b787644b3f741480226850`, 28 compétences.

Pour reproduire l'essai dans un nouveau répertoire, générer le cas, donner son `ACTOR_PROMPT.md` à un agent natif, puis vérifier les artefacts :

```sh
python3 scripts/worktree-cleanup-scenarios.py create /tmp/cstack-cleanup-trial
python3 scripts/worktree-cleanup-scenarios.py check /tmp/cstack-cleanup-trial
```

`create` refuse un répertoire existant. `check` doit échouer avant l'exécution de la tâche. Les tests de mutation ont aussi confirmé qu'il rejette la suppression d'un worktree détaché sans référence de récupération.

### Guides d'exécution rigoureux et préparation automatique

La révision du 11 septembre conserve les principes en références et rétablit les étapes de compréhension, conception, délégation et revue du cstack antérieur à l'optimisation (`ea39069`). Après normalisation des liens de principes, les corps de Fonctionnalité, Correction d’anomalie, Refactorisation, Investigation et How correspondent à cette base. Le routeur rétablit aussi les étapes de plan explicites, les raisons des étapes sautées et une revue du code par un acteur qui ne l'a pas écrit. Les commentaires et suppressions restent inspectés dans la revue générale ; leur nettoyage spécialisé reste un parcours distinct.

Une invocation explicite de `$cstack:cstack` prend en charge la suite du travail : `clarify` lorsque des exigences matérielles restent ambiguës, `horizon` pour un objectif nécessitant une carte durable entre phases, puis le guide d'exécution approprié. Les étapes se poursuivent dans l'autorisation existante. Les décisions humaines restent humaines ; les demandes en lecture seule et les invocations autonomes des compétences de préparation conservent leur périmètre.

Les 90 tests existants à cette date passent : 34 Python et 56 Bun, mesurés au commit `19acc39fe1743efeac71cf67c79c0ffa842a7854`, 28 compétences. Les deux contrôles TypeScript, la validation du plugin et celle des compétences modifiées passent. Des coordinateurs et enfants natifs Codex ont aussi travaillé dans des projets isolés ; le parent a inspecté les fichiers produits et exécuté ses propres assertions.

- Orion : demande de normalisation entièrement définie, exécutée sans question produit. Une seule ligne de code a changé ; les cas de bord et le comportement hors des espaces sont vérifiés.
- Nova : aucune écriture avant les deux décisions sur la signification d'archiver et la mutation des entrées. Une réponse contenant uniquement le contrat a déclenché la suite de l'implémentation, sans nouvelle demande d'approbation. L'ordre, les champs, les copies et l'absence de mutation des entrées sont vérifiés.
- Lyra : Horizon a produit une spécification et quatre unités dépendantes sans inventer de tickets de décision. La première phase autorisée a été implémentée, avec ancrage natif, délégation et revues indépendantes. Les phases suivantes restent planifiées et aucun commit, dépendance ou service externe n'a été ajouté.
- Lyra en lecture seule : la réponse respecte l'ordre de retrait de la compatibilité ; l'empreinte complète du projet, état de planification inclus, est inchangée.

Le [manifeste de validation](evidence/automatic-routing.json) contient les résultats et empreintes de ce commit. Les traces de travail restent sous `.cstack/tasks/preserve-rigor/forward/`. Ces exemples vérifient les transitions et leurs limites dans une session active, pas une supériorité générale ni une exécution persistante après fermeture de l'application.

Cette révision ne revendique aucun gain général de qualité, de durée ou de tokens. La PR expérimentale #4 a ensuite été fermée sans fusion ; les économies d'appels ne justifient pas la suppression de garanties des guides d'exécution.

### Références internes

Vérifications du 10 septembre 2026, contre le commit `caca9cd`. Le paquet expose 28 compétences et conserve les 23 principes dans `skills/cstack/references/principles/`. La comparaison des corps de texte, après normalisation des liens et du préambule d'activation, conserve leur contenu de fond. Les 28 noms, leurs politiques d'invocation explicite, les sources de la configuration et celles des assistants d'exécution sont inchangés.

Les résumés d'interface tronqués sont corrigés. Le validateur contrôle leur longueur de 25 à 64 caractères et quelques terminaisons incomplètes ; cette garde ne prétend pas vérifier toute la grammaire. Le fichier `AGENTS.md` ajoute une carte du dépôt et les commandes de vérification. Les ajustements expérimentaux du routage complexe étaient isolés dans la PR #4, liée au ticket #1 et ensuite fermée sans fusion.

Les 90 tests de cette campagne passent : 34 avec `python3 -m unittest discover -s tests -p 'test_*.py'`, puis 56 avec `bun test`. Le validateur `bun scripts/validate.ts` contrôle les 28 compétences, les 23 références, leur présence dans le routeur et la couverture des 158 fichiers upstream. Les tests de mutation rejettent une référence manquante, un lien de routage retiré, une provenance incorrecte, un ancien chemin ou une ancienne invocation, ainsi qu'une ancienne entrée de compétence réintroduite. Les contrôles TypeScript du dépôt et des assistants et les validateurs système du plugin et des 28 compétences passent. Le processus n'exécutait pas encore `git diff --check`. Cette garde existe maintenant dans `.github/workflows/validate.yml`. La revue indépendante du diff n'a relevé aucun problème exploitable.

Deux essais natifs de la version de base ont terminé : modification d'un parseur de port avec assertions exécutées, puis revue Boundary Discipline en lecture seule avec empreinte du projet conservée. Les sessions héritent de `gpt-6-astra` / `ultra`. Aucun sous-agent accepté n'est enregistré ; les réponses signalent une délégation indisponible, ce qui ne permet pas de comparer le coût de délégation. Les premiers essais échoués sur les permissions SQLite/réseau sont exclus des résultats.

Après autorisation explicite de l'utilisateur, les deux essais de la nouvelle version ont été exécutés. Le premier passage a révélé que la consigne de lire `no-comments` avant toute revue activait inutilement la revue de commentaires dans une question de validation. Le routeur réserve désormais ce processus aux demandes de revue de commentaires dédiées. Les deux scénarios ont ensuite été rejoués depuis leurs commits initiaux, sans réutiliser le code déjà corrigé.

- Le parseur produit accepte les ports de 1 à 65535 et lève `ValueError("invalid port")` pour les entrées invalides. Le parent a réexécuté `verify_parser.py` et 17 assertions indépendantes. Seuls `parser.py` et `verify_parser.py` ont changé ; le commit initial du projet temporaire est conservé.
- La revue Boundary Discipline place la validation dans `load_config`, cite le README et les symboles observés, et explique le rôle de `connect`. Les empreintes avant/après et la relecture du projet confirment la lecture seule ; aucun commit n'a été créé.

Les traces des deux essais finaux chargent les nouvelles références, notamment `references/principles/boundary-discipline.md`, sans charger `how`, `architect`, `no-comments` ou l'invite de revue de commentaires. La revue en lecture seule tente encore une délégation facultative, que le CLI refuse avec `no thread with id` pour la session parente. cstack signale cette limite et termine au premier plan, conformément à son contrat. Ce résultat valide les tâches demandées et leur repli, mais ne prouve pas l'exécution de sous-agents dans ce banc CLI. Aucune amélioration générale de durée ou de tokens n'est revendiquée.

Les demandes, traces, empreintes et résultats vérifiés restent sous `.cstack/tasks/native-references/behavior/`. `proposed-20260910T200842Z` conserve le premier passage ; `final-20260910/results/summary.json` et `final-20260910/verified-outcomes.json` décrivent les deux essais finaux.

### Intégration 0.3.0

Base de comparaison : `a373eca2e003a9bd2e4b2e90ac7f28a250108f6c` (0.2.0). Les quatre nouvelles compétences sont explicites. Les guides d'exécution de correction et de développement, `how`, `why`, et l'assistant `models.py` conservent leurs sources. Les 23 principes concernés changent seulement leur phrase décrivant la configuration passive. Catalogue mesuré au commit `95df6b48c7c86142567c2ebf0ddab2083fa562e9` : 51 compétences. `plugin.json` dit `0.3.0`.

#### Vérifications déterministes

Les **90 tests automatisés** de cette version passent : 34 Python, 3 Bun de paquet/plan et 53 Bun des assistants. TypeScript, le validateur système du plugin, les métadonnées des 51 compétences, les liens et les 158 fichiers de provenance pstack passent. Le processus n'exécutait pas encore `git diff --check`. Cette garde existe maintenant dans `.github/workflows/validate.yml`.

La configuration est exercée sur des répertoires temporaires : aperçu sans écriture, application puis no-op, conservation des octets manuels et CRLF, de `CLAUDE.md` et des modèles non sélectionnés. Les tests couvrent aussi les plans périmés ou altérés, les conflits de marqueurs, les liens symboliques, les erreurs d’écriture et la reprise après interruption. La revue a conduit à corriger l’écriture de bytecode dans le paquet, l’absence d’exclusion Git avant le premier état Horizon et l’écrasement d’une édition manuelle survenue pendant la préparation des fichiers. Une relecture avant chaque remplacement protège cette dernière fenêtre ; plusieurs remplacements ne constituent pas une transaction atomique globale.

Le CLI de modèles résout les 19 rôles à l’identique. Sur 30 mesures entrelacées par version, sa médiane passe de 84,8 à 79,6 ms ; les sources de l'assistant sont identiques. Le seuil fixé avant la mesure était une régression maximale de 25 % plus 20 ms. Cette observation ne démontre pas un gain de vitesse ou de tokens des processus.

#### Essais natifs reproductibles

Le générateur crée des dépôts Git séparés et des copies des deux paquets hors des projets. Le lanceur utilise des sessions Codex natives, enregistre demandes, commandes, réponses, lancements, éventuelles lacunes de métadonnées et empreintes des fichiers. Les catalogues viennent d’une découverte réelle ; Luna max est un choix explicite pour ces essais.

```sh
codex debug models > /tmp/cstack-model-catalog.json
python3 scripts/behavior-scenarios.py --baseline /chemin/plugin-0.2.0 --proposed /chemin/plugin-0.3.0 --catalog /tmp/cstack-model-catalog.json --output /tmp/cstack-cases
python3 scripts/verify-behavior.py --cases /tmp/cstack-cases/cases.json --output /tmp/cstack-results --model gpt-5.6-luna --effort max --turn-timeout 900
```

Ces commandes lancent des modèles. `--case-id` permet de ne rejouer qu’un scénario dans un nouveau répertoire de résultats ; un répertoire non vide est refusé. Une sortie `completed` indique la fin du tour, même si sa réponse pose une question ; l’acceptation exige toujours de lire les réponses, les questions enregistrées et de vérifier les artefacts. Les métadonnées d’un lancement accepté sont distinguées d’une lecture effective de l’enfant ; la fermeture d’un enfant éphémère peut rendre cette dernière indisponible.

Les [résultats détaillés](evidence/0.3.0.json) retiennent **13 scénarios, 15 tours parents et 9 sous-agents terminés** :

| Parcours | Observation vérifiée |
| --- | --- |
| Correction et `how`, ancien/nouveau | Même comportement de bornes ; assertions réexécutées par le parent. Explications correctes et lecture seule. Aucun nouveau sous-agent dans ces demandes explicitement solo. |
| `interrogate`, ancien/nouveau | Exactement trois reviewers dans chaque version. Les deux détectent les garanties absentes du README. La nouvelle version sépare Standards, Spec et adversarial et conserve le défaut Spec dans le verdict. |
| `clarify` | Une décision ouverte produit des questions et recommandations sans décision imposée. Une demande entièrement définie termine sans question inventée. Aucun fichier modifié. |
| `domain` | Brouillon en lecture seule ; ajout autorisé de Member dans le glossaire en conservant son préfixe manuel. Aucun ADR ou code ajouté. |
| `horizon` | Deux chercheurs terminés, citations vérifiées, tickets 001/002 résolus. Au tour suivant, seule la décision fournie pour 003 est enregistrée ; 004 reste ouverte, sans réponse humaine inventée. Aucun code, spécification ou objectif créé. |
| `audit-architecture` | Un explorateur, trois symboles correctement cités, proposition qualifiée de spéculative. Aucun fichier modifié. |
| Configuration répétée | Création du bloc AGENTS, des deux guides et de l’exclusion Git ; seconde application sans modification. Octets manuels, CRLF, CLAUDE et modèles préservés. |

Une comparaison indépendante, sans identité des variantes, n’a relevé aucune régression dans les sorties correction/explication ; le parent a vérifié leurs fichiers et assertions séparément. Le cas de revue porte sur le README staged : les modifications unstaged et untracked sont volontairement hors périmètre et leur conservation est vérifiée. Le comité natif observé a trois membres ; les autres tailles relèvent des tests de compatibilité du assistant et des instructions révisées.

Les neuf créations d’enfants transmettent `gpt-5.6-luna` et `max`, et leurs terminaisons sont enregistrées. Leur fermeture éphémère empêche ensuite `thread/read` : ce résultat prouve les champs transmis et les travaux terminés, pas une mesure indépendante du modèle effectif de chaque enfant. Le test natif de la configuration précède la dernière garde contre une édition concurrente ; cette garde est couverte par son test de régression et la suite Python complète.

Les premiers essais invalidés par le banc (questions nulles, héritage du mauvais dépôt Git, lecture d’un enfant déjà fermé) et les interruptions à 300 secondes sont conservés localement, mais exclus de ces 13 résultats. Les essais longs retenus utilisent une limite explicite de 900 secondes par tour. Ces scénarios synthétiques ne garantissent pas l’absence de toute régression et ne démontrent aucun gain général de tokens. Les traces brutes et le journal de décisions restent sous `.cstack/tasks/horizon-project-setup/` ; le JSON publié contient leurs empreintes.

## Historique : révision de la ventilation avant Goal

Cette section conserve l'état de preuve de cette ancienne révision. La règle actuelle impose au moins deux explorateurs lors d'une délégation ; les anciennes exceptions cible unique et fichiers indissociables sont supprimées.

### Ventilation d'ancrage et demande de délégation

L'Étape 1 de `how` exige désormais d'écrire les angles avant de choisir le chemin. Deux angles aux listes de fichiers disjointes envoient la question vers les explorateurs parallèles. La passe unique est une exception qui nomme son test : cible unique, fichiers indissociables ou délégation exclue.

Le scénario `readonly_explanation_*` conserve zéro enfant attendu. Son prompt interdit explicitement la délégation ; il vérifie maintenant le test « délégation exclue » plutôt que l'ancien chemin simple par défaut. Aucun scénario de comportement n'a été exécuté pour cette révision ; le harnais natif exige un modèle Codex réel et vit hors intégration continue.

Une relecture des preuves de `docs/evidence/0.3.0.json` établit un fait qui n'avait pas été relevé. Sur les treize scénarios, les quatre qui ont lancé des enfants sont exactement les quatre dont la demande utilisateur réclamait la délégation : `interrogate` deux fois avec « Utilise le panel de réviseurs configuré », `horizon` avec « Affecte un sous-agent natif de recherche à chaque ticket de recherche prêt », et `audit-architecture` avec « Utilise au plus un explorateur borné ». Les neuf autres l'interdisaient explicitement ou n'en parlaient pas, et valent zéro enfant. Aucune mesure enregistrée ne montre le texte d'une compétence déclenchant seul une délégation.

Cette corrélation est mesurée, pas inférée ; son mécanisme, lui, est inféré d'une consigne d'outil de l'hôte qui prime sur le texte de compétence. Les `default_prompt` des compétences qui délèguent portent désormais cette demande, et trois d'entre eux reprennent le noyau des formulations ci-dessus, en y ajoutant la nature native du délégué. L'effet de ce changement n'est pas mesuré : il faut un essai natif où la demande vient du prompt par défaut et non du corps de la consigne.

Le trou de couverture reste ouvert. Les deux seules exécutions de `how` enregistrées interdisent la délégation par construction, donc aucun scénario existant ne peut détecter une régression de ventilation de `how`.

## Historique des versions précédentes

### Base upstream

Avant modification des assistants : `bun run test` passe 52 tests, puis `bun run typecheck` passe. Le commit source est enregistré dans `UPSTREAM.json`. Mesure du premier import, commit `6600fc4`.

### Lanceur inscriptible

Le lanceur passe 11 tests avec `python3 -m unittest discover -s tests -p 'test_*.py' -v`. Après revue indépendante, son architecture utilise une copie temporaire distincte par invocation : aucun exécutable ou module déjà présent dans le projet ne doit être réutilisé. Les tests de cette version couvrent notamment la lecture seule, les arguments littéraux, les chemins contenant des espaces, les sorties de l'espace de travail par liens symboliques, le nettoyage et les appels concurrents.

Les lancements réels de `watch-pr/watch-pr --help` et `orch/orch.ts --help` passent simultanément depuis un dossier contenant des espaces. Les empreintes des sources sont identiques avant/après et aucun stage temporaire ne subsiste après leur fin.

### Configuration de modèles

Une évaluation indépendante dans un dossier isolé a demandé `$cstack:setup-cstack` avec le modèle fictif `cstack-fictional-model-999`. La compétence a refusé la sélection non vérifiable, sans lancement ni écriture ni substitution. L'empreinte du fichier existant est restée identique.

#### Configuration 0.2.0 : modèle et effort

Les six tests de `tests/test_models.py` couvrent les sept recommandations de 0.2.0, leur résolution pour les 19 rôles, les comités, les anciennes chaînes de modèle, l'héritage explicite, les choix indisponibles, le JSON invalide, les prévisualisations périmées, les échecs de sauvegarde et les répertoires d'état liés par symlink. Le parcours CLI réel `show` → `apply` → `resolve` a également été exécuté pour chaque rôle dans un dossier temporaire. Une revue indépendante n'a relevé aucun problème majeur ; le séparateur manquant dans le tableau de recommandations a été corrigé.

Un essai comportemental avec Codex CLI 0.153.4 via son serveur natif a chargé la nouvelle compétence depuis les sources et enregistré les sept groupes explicitement acceptés dans un projet isolé. Une vérification séparée a résolu `documentation` puis lancé un unique sous-agent. La lecture native `thread/read` confirme `model: gpt-5.6-luna` et `reasoningEffort: max` pour l'enfant, avec un parent `gpt-6-astra` / `low`. L'enfant a lu le README du projet et terminé sa tâche. Cela vérifie une transmission réelle des deux réglages ; les autres paires recommandées sont validées contre le catalogue courant et par les tests, sans lancer un modèle pour chaque rôle.

Pour cette version 0.2.0 (commit `a373eca`), les 17 tests Python, les 3 tests Bun du paquet et du plan, et les 53 tests des assistants passent : **73 tests automatisés**. Les contrôles TypeScript, le validateur de plugin, les métadonnées des compétences modifiées, les 47 entrées du paquet et la couverture des 158 fichiers amont passent également. La configuration de test reste dans un projet temporaire ; la mise à jour du plugin ne remplace pas les choix d'un projet utilisateur.

### Processus de correction

Un agent indépendant a utilisé la compétence principale pour corriger un filtre Python dans un projet isolé. Le cas fourni excluait à tort la borne inférieure et incluait des événements futurs. L'agent a reproduit l'échec, corrigé le filtre et ajouté un test passant. Le parent a ensuite exécuté une vérification indépendante couvrant les deux bornes, les dates futures, la fenêtre nulle, une liste vide, l'ordre et la conservation des données d'entrée. Ces assertions passent. L'exécution était volontairement séquentielle, sans sous-agents ni accès GitHub.

### Structure du paquet

Le validateur de plugin fourni avec Codex et les validations individuelles des 47 compétences du paquet 0.1.1 (commit `416053e797727dcc5a3a2016ab014157af758877`) passent. `bun scripts/validate.ts` confirme les 47 entrées, les politiques d'invocation explicite, les liens internes et la couverture des 158 fichiers source.

Les trois tests Bun à la racine couvrent le refus des paquets incomplets ou à activation implicite, ainsi que l'acceptation du modèle de plan natif et le rejet des plans privés de vérification. Le contrôle TypeScript strict des outils de validation passe.

### Vérifications finales

Les 53 tests des assistants, les 3 tests Bun du paquet et du plan, et les 11 tests Python du lanceur passent : 67 tests automatisés de cette campagne. Les contrôles TypeScript couvrent le suivi de PR, l'orchestration, le bootstrap et les outils de validation. Le processus n'exécutait pas encore `git diff --check`. Cette garde existe maintenant dans `.github/workflows/validate.yml`.

Les régressions de revue vérifient notamment qu'une PR fermée reste la première PR non fusionnée, qu'un état Git illisible ne devient pas « propre », et qu'aucun cache exécutable préplanté dans le projet n'est réutilisé.

Le dépôt GitHub est privé, sur `main`. La première publication a passé [GitHub Actions](https://github.com/charlescstpierr/cstack/actions/runs/34301423576). L'installation depuis GitHub a été réalisée avec le gestionnaire de plugins Codex ; les 192 fichiers du plugin installé correspondent aux fichiers suivis du dépôt au commit `416053e797727dcc5a3a2016ab014157af758877`, sans `node_modules` ajouté au cache du plugin. `git ls-tree -r --name-only 416053e -- plugins/cstack | wc -l` vaut 192.

### Invocation native App et CLI

Le serveur natif Codex expose les 47 compétences activées du paquet 0.1.1 (commit `416053e`), sans erreur de chargement, sous des noms tels que `cstack:cstack` et `cstack:architect`. Une session CLI éphémère avec configuration utilisateur ignorée et uniquement cstack activé a confirmé le chargement de la compétence installée par `$cstack:cstack`.

Un second essai a utilisé la sélection structurée `UserInput::Skill` du sélecteur App/CLI dans une session éphémère en lecture seule, avec les autres plugins, serveurs MCP et hooks désactivés. Le mode a chargé son guide d'exécution et son contrat, puis lancé exactement deux sous-agents natifs, un par module synthétique. Chaque sous-agent a trouvé et reproduit le défaut prévu, et le parent a vérifié les résultats. Les empreintes des trois fichiers du projet sont restées identiques.

L'essai a aussi révélé une différence de syntaxe : du texte brut `$cstack` ne désigne pas la compétence qualifiée d'un plugin. La version 0.1.1 utilise des invocations complètes dans ses invites et exemples ; un test de paquet rejette désormais une invite de compétence non qualifiée. La recherche puis sélection de **cstack** dans le sélecteur reste disponible.

Ces essais vérifient le protocole et le moteur partagés par App et CLI. Ils ne constituent pas une observation visuelle de l'interface du gestionnaire de plugins. Les limites de connecteurs, planification et webhooks restent documentées dans PORTING.md.

## Vérifier le Goal natif

La sonde `scripts/verify-goal.py` réutilise l’app-server du runner existant, dans une fixture temporaire sans Git ni délégation. Elle observe le Goal via l’API native ; elle ne simule pas la continuation. Les threads sont persistants car les threads éphémères refusent les Goals. Aucune installation ni configuration utilisateur n’est modifiée. La sonde utilise toutefois le CODEX_HOME courant : les conversations persistent dans son historique et les fixtures restent dans le répertoire temporaire.

```sh
python3 scripts/verify-goal.py --scenario authorized --output /tmp/cstack-goal-authorized
python3 scripts/verify-goal.py --scenario no-consent --output /tmp/cstack-goal-no-consent
```

Ces commandes lancent un modèle réel. `--model` et `--effort` permettent une sélection explicite compatible avec l’hôte. Chaque dossier de sortie doit être vide. Le premier cas exige deux tours, le même objectif actif puis complet, aucun budget, l’absence du fichier de phase 2 après le premier tour et les deux fichiers attendus à la fin. Le second lit aussi le YAML contenant la demande de Goal, mais exige un état natif nul faute de demande utilisateur. Les traces et le résultat sont conservés dans le dossier de sortie.

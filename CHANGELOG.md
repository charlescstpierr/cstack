# Changelog

Les versions suivent SemVer. Le format suit [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/).

## [Unreleased]

- Ouvrir une PR : `## Why` porte au besoin le plus petit visuel qui rend le changement clair (pseudocode, arbre d'appels ou de fichiers, diff de forme, Mermaid), `## Verification` montre l'avant et l'après, et `## Blast radius` dit si le changement est une porte à double sens ou à sens unique. Avant d'ouvrir, la documentation est comparée au diff : chemins, drapeaux, commandes, symboles, compteurs et exemples périmés sont corrigés dans la PR ; un changement de récit est soumis à l'utilisateur. Inspiré du skill pr de mattpocock/skills (MIT), réécrit sans copie.
- Rédaction de compétences : une règle de discipline nouvelle ou durcie se teste d'abord contre une base sans elle (`references/rule-pressure-tests.md`) : scénario réaliste à trois pressions ou plus avec choix imposé, excuses notées mot pour mot, règle minimale, négation explicite pour chaque nouvelle excuse, question méta. `eval` compare une règle à la même compétence sans elle et ne promeut pas une règle sans échec de référence observé ; une règle non exécutée est livrée « non prouvée ». Scénario natif `routing_rule_baseline_first` prêt, pas encore exécuté. Méthode inspirée de obra/superpowers (MIT), réécrite sans copie.
- Contexte et mémoire : après un résumé, le rappel du mode renvoie aussi au point de reprise de la tâche active, dont l'agent nomme le chemin dans la conversation pour que le résumé le porte (aucun hook `PreCompact` : Codex n'y accepte qu'un avertissement affiché). `reflect` vérifie l'hygiène du fichier d'instructions avant d'écrire (pas de doublon du code, cible la plus précise, fichier que Codex charge réellement dont `AGENTS.override.md`, budget `project_doc_max_bytes`, leçon contradictoire remplaçant l'ancienne règle ou renvoyée au carnet, références mortes, fusion). `recall` extrait d'abord un index puis développe seulement les tâches retenues ; les passages `<private>` sont exclus de toute extraction (`recall`, `reflect` et ses modèles de reviewers et de synthèse, `automate-me`).
- Synchronisation sur pstack 0.15.5 (`12d587d`), commit amont par commit amont : question de budget du setup (#366) ; rondes de vérification à partir du head code-ready, rebase seulement à la préparation du merge ou sur conflit ou échec dû à trunk, `children.tsv` et test de blocage, au moins deux voies d'audit, règle du bruit de build, briefs Swarm avec SHA et méthode, statut seulement sur changement et règle d'autonomie totale (#414) ; lignes `start` du journal de décisions et exception du propriétaire en autopilot (#422). Modèles par défaut et noms de modèles non repris ; consignes supprimées par l'amont (#414, #419) conservées faute de preuve sur Codex.
- Vérification : chaque pilotage rend passé, échoué (dont non concluant, jamais un succès) ou bloqué avec un code (`auth`, `environnement`, `données`, `budget`, `non pris en charge`) ; un pilotage bloqué n'est jamais classé comme manque produit. L'état final est jugé par une observation neuve en lecture seule, les secrets passent par leur nom, et une recette ne devient un helper qu'après une assertion verte. `maintain-verification-skill` gagne un bug bash sur demande (`references/bug-bash.md`) : chartes zone × posture, explorateurs via Swarm, tri en cinq bacs, confirmation par un test qui échoue sur l'assertion visée. Méthodes inspirées de tester-army/e2e (Apache-2.0), réécrites sans copie.
- Banc de résultat : `summary.json` ajoute par bras `pass_all_rate` (pass^k, tâches résolues à toutes les répétitions) et `unstable_tasks` (répétitions divergentes), et par paire de bras l'écart moyen de taux de résolution avec un intervalle bootstrap à 95 % initialisé par la graine du manifeste. Idée reprise du banc A/B de tester-army/e2e (Apache-2.0), réécrite sans copie.
- Arena vérifie chaque candidat avant de juger, par rapport à la base commune : un candidat qui introduit une régression ne peut pas devenir la base, sauf si tous les candidats vérifiables en introduisent une, et le brief du juge porte la même règle. Le juge reçoit des candidats anonymisés, dans un ordre aléatoire, et un second jugement en ordre inverse s'ajoute à partir de trois candidats ; un désaccord est consigné.
- Interrogate ajoute deux lentilles à l'axe Adversarial : les cas limites atteignables depuis le diff (ensembles traités en partie, consommateurs d'éléments supprimés) et le trou de vérification (« si ce comportement cassait, quel test échouerait ? »), sans réclamer de tests qui ne vérifient rien. Le reviewer énumère au moins dix pistes puis ne rapporte que celles qu'il prouve ; zéro finding reste valide. Un quatrième et un cinquième reviewer prennent ces lentilles comme axe principal. Le validateur épingle ces règles. Trois scénarios natifs (`interrogate_partial_set_*`, `arena_verified_selection`) sont prêts dans `scripts/behavior-scenarios.py` mais pas encore exécutés.
- Correctif : `log.sh` (show-me-your-work) testait le journal avec `-f` puis écrivait l'en-tête avec `>`. Un journal vide restait sans en-tête, et un test raté sur un disque réseau pouvait écraser les lignes. Il teste désormais `-s` et ajoute avec `>>`. Une cellule qui commence par `"` reçoit aussi le préfixe `'`, pour qu'un lecteur TSV n'ouvre pas un champ entre guillemets. Porté de pstack #414 et de pstack-claude #99.
- Correctif : `watch-pr` relançait sans fin sur un dépôt sans CI, car l'absence de checks levait `ChecksUnavailable` comme une lecture impossible. Elle devient l'état `ci-none` quand `gh pr checks` ne signale aucun check, que le rollup du commit head est nul, qu'aucun commit de la PR n'a rapporté de check et que GitHub a calculé la fusionnabilité. Tout autre résultat vide reste refusé. Porté de pstack-claude #153.
- Correctif : `watch-pr` déclarait `READY` une PR retenue par une revue obligatoire, car un état `BLOCKED` passait dès que la CI n'était pas rouge. Une revue requise (`review-required`) ou une autre protection de branche (`merge-blocked`) donne désormais un bloqueur `merge-gate` terminal, après la fin des checks en cours. Porté de pstack-claude #95.

## [0.7.0] - 2026-09-27

- Descriptions des compétences harmonisées : chacune commence par « À utiliser pour $cstack:<nom> » puis dit ce que fait la compétence ; le validateur impose cette forme, avec le nom comme jeton complet.
- Correctif : au redémarrage après installation des dépendances, `bootstrap.ts` transmettait deux fois les drapeaux de `BUN_OPTIONS` ; il redémarre désormais sans cette variable, dont `execArgv` porte déjà les drapeaux.
- Correctif : un worker qui quitte avant de lire son brief (EPIPE sur stdin) est classé d'après son code de sortie au lieu de faire échouer tout le run.
- Banc de résultat (`scripts/outcome-bench.py`) : rejoue des correctifs open source récents dans les bras Codex seul, cstack et pstack amont (vérifié blob par blob contre `UPSTREAM.json`), note les diffs avec les tests cachés dans Docker et agrège résolution, tokens, durée et sous-agents. Aucune campagne n'est encore exécutée. Audit des obstacles à l'autonomie dans `docs/AUTONOMY-AUDIT.md`.
- Tests : trois tests de plus qui provoquent une erreur de permission par `chmod 000` ne s'exécutent plus sous root, qui ignore ces permissions, comme celui de `sync-upstream` avant eux.
- `make-bot-ui` passe en français, comme les autres compétences : le validateur épingle ses gardes de sécurité en français et ne l'exempte plus de la forme « À utiliser pour $cstack:<nom> ».
- Installation en une commande : `install.sh` installe, met à jour (`--ref` pour une branche, un tag ou un commit, `--local` pour un clone), diagnostique (`doctor`) et retire cstack, uniquement par `codex plugin`. README refondu autour de l'installation, des premiers pas et d'un tableau des compétences ; descriptions du plugin réécrites.
- Rappel du mode sur les longues sessions, comme le `reminder:` de pstack : deux hooks du plugin réinjectent un rappel court à chaque message et après chaque résumé, seulement après `$cstack:cstack` ; approbation unique avec `/hooks` en CLI. Pause propre avant un résumé imminent et relecture des règles après un résumé.
- Toutes les skills à la taille pstack : une ligne `Runtime :` relie directement les parties du contrat utiles au lieu de paragraphes recopiés, et le détail long passe dans des `references/` lues à la demande (`setup-cstack` 2 879 → 617 mots, `make-bot-ui` 1 589 → 906, `interrogate` 1 455 → 836, `horizon` 2 239 → 1 700). Le plafond commun des `SKILL.md` descend à 2 150 mots.
- Routeur court, comme pstack : `$cstack:cstack` ne fait plus lire tout le contrat d'exécution d'avance. Son `SKILL.md` devient une liste de déclencheurs, et le contrat un index qui renvoie à une partie par situation (`references/runtime/`). Lecture initiale : environ 8 300 → 2 600 mots. Le validateur plafonne la taille de chaque `SKILL.md` et de cette lecture initiale. Le banc compare une version figée du plugin (`nom=cstack@<ref>`).
- Agents natifs du projet : `$cstack:setup-cstack` propose `cstack-explorer`, `cstack-worker` et `cstack-reviewer` dans `.codex/agents/`, avec les modèles et efforts choisis ; cstack les lance par leur nom. Un rôle confié à un CLI n'a pas d'agent, `models.py apply` resynchronise les agents gérés, et `native_agents: false` les supprime. Le bloc `AGENTS.md` garde la conversation en mode cstack après une invocation explicite et demande la délégation du travail indépendant.
- Panel mixte proposé d'office quand Claude Code est présent et connecté : deux positions natives Codex et une Claude Code dans `arena runners`, `architect runners` et `interrogate reviewers`, toujours sur acceptation.
- Goal natif explicitement autorisé pour suivre une implémentation multi-phase jusqu’à sa livraison convenue, avec une PR testée et revue par défaut. La continuation utilise les outils natifs de Codex.
- Exploration déléguée : minimum deux explorateurs, normalement trois angles utiles. Setup, How, audit et recherches Horizon partagent cette règle et conservent les modèles configurés.

## [0.6.0] - 2026-09-23

### Ajouté

- Livraison : inspection de la révision complète des PR, annulation vérifiée des merges en attente avant réécriture, condition de head côté GitHub, lease explicite et frontière enfant après squash.
- Maintenance : synchronisation amont en trois voies avec simulation, résolutions liées aux blobs et refus d'avancer la provenance tant qu'un conflit reste ouvert.
- Paquet : faits documentaires générés et vérifiés, ShellCheck et Actionlint en CI.

### Autres changements intégrés

- Suivi commun des workflows cstack : playbook annoncé, todo cochée en direct, appels Codex natifs et CLI nommés avec rôle, modèle/effort du setup et skills. Les résultats restent liés aux preuves disponibles ; les erreurs temporaires permettent une seule relance annoncée sans substitution.

- TDD pour les bugs et nouvelles fonctionnalités comportementales : les builders fournissent une preuve rouge → vert, ou un parcours hors TDD justifié et vérifié, avant livraison.

- Le setup affiche une todo actualisée à chaque étape, dans le plan natif disponible ou dans la conversation, avec les attentes de choix et d’approbation et les blocages.

- Comparaison optionnelle des observations base/candidat avec `compare-checks.py` : détection des nouvelles régressions dans une base déjà rouge, refus des preuves incomplètes et maintien des barrières de livraison. Aucun runner ni dépendance ajouté.

- `setup-cstack` présente sept groupes de modèles avant l'état d'héritage. `bug-fix` recommande `gpt-6-astra` avec l'effort `medium`. Le bloc `AGENTS.md` charge les guides cstack et `CLAUDE.md` comme instructions seulement après une invocation `$cstack:*`, sans interdire leur lecture ordinaire demandée par l'utilisateur.
- Le setup distingue l'activation immédiate de `.cstack/models.json` pour les rôles résolus après l'écriture du rechargement de `AGENTS.md` dans une nouvelle conversation App ou session CLI.
- Installation des dépendances des helpers isolée du workspace inspecté. `bun install` reçoit `--ignore-scripts` et `--no-env-file`, tandis que le redémarrage conserve les drapeaux Bun et les arguments utilisateur.
- Frontière d'orchestration : `frontier.set` enregistre le premier PR fermé non fusionné dans `closedGap`, sans déplacer la frontière du plus bas PR ouvert.
- Le vérificateur de plans multi-PR suit le gabarit courant français/anglais et teste directement le bloc réel borné à la capacité native.
- Le validateur de paquet ne dépend plus d'une version de plugin codée en dur dans sa mutation de test.
- Le runner CLI accepte un `acceptance` facultatif, borné à 4096 octets UTF-8, le conserve dans la provenance et refuse les reprises dont la présence ou la valeur diffère avant la génération.

- Nettoyage : préservation des preuves et suppression du worktree dans deux appels d’outil distincts, avec reçu vérifié et conservation obligatoire en cas d’échec intermédiaire.

- Reprise facultative d’un worker Claude Code depuis son reçu précédent, avec contrôle de provenance, exclusion des reprises concurrentes et conservation des permissions. Le démarrage neuf reste le défaut ; les erreurs de reprise ne provoquent pas de relance cachée.

- Le setup inventorie les CLI présents et leurs statuts officiels de connexion avant de proposer les runtimes. Il permet d’ajouter Claude Code aux panels existants ou de remplacer des rôles choisis, en préservant les autres réglages.
- Guide pratique Codex/Claude, partage des skills et du contexte, limites vérifiées et commandes de mise à jour du plugin.

- Les bundles workers suivent les références Markdown locales des skills et proposent `skill_references` pour les sources spécialisées. Les 29 skills livrés sont testés ; les liens d’exemple en blocs de code et les skills voisins ne sont pas activés.
- Arena et Swarm conservent le nombre total demandé de candidats/tranches lorsque la concurrence impose plusieurs vagues.

- Workers CLI facultatifs `codex-cli`, `claude-code`, `cursor-agent` et `grok` dans les rôles et panels existants. Conservation du dispatch natif par défaut, des briefs, de l’inbox et du ledger ; authentification laissée aux CLI officiels.
- Bundle de skills CStack commun à tous les CLI et contexte partagé explicite, borné et empreinté. Le parent relaie les résultats vérifiés et les erreurs aux tâches dépendantes.
- Runner borné avec découverte des capacités, sortie structurée, statuts de processus séparés des verdicts de travail et tests de processus sans credentials. Aucun serveur ni SDK fournisseur ajouté.

- Les compétences qui délèguent portent la demande de délégation dans leur `default_prompt`. Codex exige cette demande dans le tour de l’utilisateur ; une instruction de SKILL.md ne suffit pas à faire partir un sous-agent. Les preuves de `docs/evidence/0.3.0.json` le montrent sur treize scénarios. Trois prompts reprennent le noyau des formulations mesurées à enfants non nuls. Le contrat d’exécution et le guide décrivent la contrainte réelle et son dépannage.

- `how` ventile par défaut. Son Étape 1 exige d’écrire les angles d’exploration avant de choisir le chemin : deux angles aux fichiers disjoints lancent les explorateurs parallèles. La passe unique devient une exception qui nomme son test — cible unique, fichiers indissociables ou délégation exclue — et l’étiquette `single-pass: <test>`. Les guides d’exécution d’ancrage, `architect` et `swarm` suivent le même défaut.

- `watch-pr` distingue les branches homonymes de dépôts différents : un fork ne peut plus remplacer le vrai parent et produire un faux verdict `READY`. Les identités absentes et les parents ambigus bloquent la découverte.
- Un handle d’orchestration dépossédé refuse les nouvelles opérations nécessitant le verrou. La limite de `--force` sur une opération déjà engagée reste documentée.
- Le redémarrage direct de bootstrap conserve les options Bun, notamment `--no-env-file` et `--config`, ainsi que les arguments utilisateur.
- Le validateur contrôle les nombres de « guides d’exécution » avec apostrophe droite ou typographique. Corrections des instructions françaises ambiguës et clarification des références et mesures historiques.

- Messages français pour les courses pendant le diagnostic d’un verrou, sans masquer les erreurs de permission. Tests de régression couvrant aussi la migration des anciens fichiers PID.
- Diagnostics des plans anglais incomplets conservant la langue de leurs repères.
- Traduction partagée des erreurs d’arguments des commandes de configuration, avec conservation des valeurs saisies et des codes de sortie.

- Correction de la double acquisition du verrou d’orchestration lors d’une reprise concurrente. Chaque acquisition possède désormais un marqueur unique ; un ancien détenteur ne peut plus libérer le verrou de son remplaçant, même dans le même processus.
- Migration automatique des anciens fichiers PID, reprise après interruption et tests de concurrence déterministes.

## [0.5.0] - 2026-09-23

### Ajouté

- Pack d'intake Codex sous `plugins/cstack/automations/intake/`, avec contrats de triage, de reproduction et d'ouverture de PR draft.

### Corrigé

- Les étapes d'intake échouent fermées sans commentaire de verdict valide ou sans deux chemins de preuve non vides avant une PR draft.
- Les helpers sont préparés hors du workspace inspecté et imposent un `CSTACK_PLUGIN_ROOT` de confiance.

## [0.4.0] - 2026-09-12

### Ajouté

- Compétence `deslop`. Il nettoie un diff de code avant commit. Il est original à cstack. pstack livrait `/deslop` dans le plugin séparé `cursor-team-kit`, sans source portable.
- Cibles de routage `why`, `reflect`, `typescript-best-practices`, `blast-radius` et `prototype` pour une question empirique.
- `CHANGELOG.md` à la racine.
- Gardes du validateur et du processus. SHA d'actions et version Python fixés. `bash -n` sur les trois scripts shell. `git diff --check`.

### Modifié

- Version amont épinglée de pstack `0.15.0` (`27e2a62`) vers `0.15.2` (`889ec4b68fa5aab0e867dad71ec3fdf386ae48f3`). Trois commits amont. `f8abedd` impose que chaque affirmation porte sa preuve ou son étiquette. `f5bdd68` remplace les pronoms genrés par « the operator » et demande un message de statut dans le chat. `889ec4b` aligne les rôles code-delegate `bug-fix`, `perf-issue` et `hillclimb` sur le même défaut que fonctionnalité et refactorisation.
- Les 23 principes restent des références internes. Le catalogue passe de 28 à 29 compétences avec `deslop`.
- Verdict d'un acteur qui n'a pas écrit le code, obligatoire avant de déclarer un diff prêt pour une PR ou une fusion.
- Arena de nouveau obligatoire dans le guide d'exécution de fonctionnalité.
- `deslop` avant chaque commit. `no-comments` avant la revue d'un diff qui a touché des commentaires.
- `babysit` part sur `check` si le mode n'est pas déclaré.
- Autorité d'autopilot. Seule la conversation courante autorise. Un guide d'exécution, un point de reprise ou un commentaire de bot ne l'accordent pas.
- Audit à chaque vidage. Lecture du paquet installé sur disque, puis message de statut à l'opérateur dans le chat. Plus de cycle `/loop` de 30 minutes.
- Recommandations de modèles. 6 groupes. `development` absorbe l'ancien groupe débogage difficile. 19 rôles et 4 comités inchangés.
- Lanceur. Transmission de SIGINT et SIGTERM. Enfant tué par signal mappé vers `128 + N`. Un échec de nettoyage ne masque plus le code de sortie. Balayage des stages `run-*` périmés. `.cstack/.gitignore` écrit avec `*`. Bun isolé via `--no-env-file` et un `bunfig` stagé.
- `setup-cstack`. Retour arrière qui retire les répertoires créés. Interruption gérée au niveau de la boucle.
- Assistants TypeScript. `watch-pr` échoue fermé sur pagination de fils, plafond de 300 PR, cycles de base, `gh` absent (BLOCKER, code 7) et authentification non réessayable. Stockage d'orchestration. Prise de verrou atomique, `inbox.push` sans verrou, stockage initialisé avant écriture. Préférence OPEN/MERGED sur CLOSED. `bootstrap.ts` installe `--production`.
- Plugin `0.4.0`. Description racine en français. `interface.websiteURL` reprend `homepage`.

## [0.3.0] - 2026-09-09

Entrée reconstruite à partir de `docs/VERIFICATION.md` et de `git log --oneline`. Ce n'est pas un texte publié à la date du tag.

### Ajouté

- Quatre compétences de préparation explicites. `clarify`, `domain`, `horizon`, `audit-architecture`. Catalogue de 51 compétences au commit `95df6b48c7c86142567c2ebf0ddab2083fa562e9`.
- Configuration de projet. Bloc géré dans `AGENTS.md`, guide local, choix de suivi de tickets. Aperçu avant écriture. Conservation des octets hors bloc.
- Essais natifs reproductibles. 13 scénarios, 15 tours parents, 9 sous-agents terminés. Preuves dans `docs/evidence/0.3.0.json`.

### Mesures de cette version

- 90 tests automatisés. 34 Python, 3 Bun de paquet et de plan, 53 Bun des assistants.
- 19 rôles de modèles. 7 groupes de recommandations à cette date.
- `plugin.json` passe à `0.3.0` dans `95df6b4`. Les commits suivants jusqu'à `62e1f3b` ont gardé ce numéro.

# Changelog

Les versions suivent SemVer. Le format suit [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/).

## À publier

- Comparaison optionnelle des observations base/candidat avec `compare-checks.py` : détection des nouvelles régressions dans une base déjà rouge, refus des preuves incomplètes et maintien des barrières de livraison. Aucun runner ni dépendance ajouté.

- `setup-cstack` présente sept groupes de modèles avant l'état d'héritage. `bug-fix` recommande `gpt-6-astra` avec l'effort `medium`. Le bloc `AGENTS.md` charge les guides cstack et `CLAUDE.md` comme instructions seulement après une invocation `$cstack:*`, sans interdire leur lecture ordinaire demandée par l'utilisateur.
- Le setup distingue l'activation immédiate de `.cstack/models.json` pour les rôles résolus après l'écriture du rechargement de `AGENTS.md` dans une nouvelle conversation App ou session CLI.
- Installation des dépendances des helpers isolée du workspace inspecté. `bun install` reçoit `--ignore-scripts` et `--no-env-file`, tandis que le redémarrage conserve les drapeaux Bun et les arguments utilisateur.
- Frontière d'orchestration : `frontier.set` enregistre le premier PR fermé non fusionné dans `closedGap`, sans déplacer la frontière du plus bas PR ouvert.
- Le vérificateur de plans multi-PR suit le gabarit courant français/anglais et teste directement le bloc réel borné à la capacité native.
- Le validateur de paquet ne dépend plus d'une version de plugin codée en dur dans sa mutation de test.

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

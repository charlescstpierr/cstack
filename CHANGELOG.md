# Changelog

Les versions suivent SemVer. Le format suit [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/).

## À publier

- `watch-pr` distingue les branches homonymes de dépôts différents : un fork ne peut plus remplacer le vrai parent et produire un faux verdict `READY`. Les identités absentes et les parents ambigus bloquent la découverte.
- Un handle d’orchestration dépossédé refuse les nouvelles opérations nécessitant le verrou. La limite de `--force` sur une opération déjà engagée reste documentée.
- Le redémarrage direct de bootstrap conserve les options Bun, notamment `--no-env-file` et `--config`, ainsi que les arguments utilisateur.
- Le validateur contrôle les nombres de « guides d’exécution » avec apostrophe droite ou typographique. Corrections des instructions françaises ambiguës et clarification des références et mesures historiques.

- Messages français pour les courses pendant le diagnostic d’un verrou, sans masquer les erreurs de permission. Tests de régression couvrant aussi la migration des anciens fichiers PID.
- Diagnostics des plans anglais incomplets conservant la langue de leurs repères.
- Traduction partagée des erreurs d’arguments des commandes de configuration, avec conservation des valeurs saisies et des codes de sortie.

- Correction de la double acquisition du verrou d’orchestration lors d’une reprise concurrente. Chaque acquisition possède désormais un marqueur unique ; un ancien détenteur ne peut plus libérer le verrou de son remplaçant, même dans le même processus.
- Migration automatique des anciens fichiers PID, reprise après interruption et tests de concurrence déterministes.

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

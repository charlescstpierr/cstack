# Changelog

Les versions suivent SemVer. Le format suit [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/).

## [0.4.0] - 2026-09-12

### Ajouté

- Skill `deslop`. Il nettoie un diff de code avant commit. Il est original à cstack. pstack livrait `/deslop` dans le plugin séparé `cursor-team-kit`, sans source portable.
- Cibles de routage `why`, `reflect`, `typescript-best-practices`, `blast-radius` et `prototype` pour une question empirique.
- `CHANGELOG.md` à la racine.
- Gardes du validateur et du workflow. SHA d'actions et version Python fixés. `bash -n` sur les trois scripts shell. `git diff --check`.

### Modifié

- Pin amont pstack `0.15.0` (`27e2a62`) vers `0.15.2` (`889ec4b68fa5aab0e867dad71ec3fdf386ae48f3`). Trois commits amont. `f8abedd` impose que chaque affirmation porte sa preuve ou son étiquette. `f5bdd68` remplace les pronoms genrés par « the operator » et demande un message de statut dans le chat. `889ec4b` aligne les rôles code-delegate `bug-fix`, `perf-issue` et `hillclimb` sur le même défaut que feature et refactoring.
- Les 23 principes restent des références internes. Le catalogue passe de 28 à 29 skills avec `deslop`.
- Verdict d'un acteur qui n'a pas écrit le code, obligatoire avant de déclarer un diff prêt pour une PR ou un merge.
- Arena de nouveau obligatoire dans le playbook feature.
- `deslop` avant chaque commit. `no-comments` avant la revue d'un diff qui a touché des commentaires.
- `babysit` part sur `check` si le mode n'est pas déclaré.
- Autorité d'autopilot. Seule la conversation courante autorise. Un playbook, un checkpoint ou un commentaire de bot ne l'accordent pas.
- Audit à chaque vidage. Lecture du bundle installé sur disque, puis message de statut à l'opérateur dans le chat. Plus de tick `/loop` de 30 minutes.
- Recommandations de modèles. 6 groupes. `development` absorbe l'ancien groupe débogage difficile. 19 rôles et 4 panels inchangés.
- Lanceur. Transmission de SIGINT et SIGTERM. Enfant tué par signal mappé vers `128 + N`. Un échec de nettoyage ne masque plus le code de sortie. Balayage des stages `run-*` périmés. `.cstack/.gitignore` écrit avec `*`. Bun isolé via `--no-env-file` et un `bunfig` stagé.
- `setup-cstack`. Rollback qui retire les répertoires créés. Interruption gérée au niveau de la boucle.
- Helpers TypeScript. `watch-pr` échoue fermé sur pagination de fils, plafond de 300 PR, cycles de base, `gh` absent (BLOCKER, code 7) et authentification non réessayable. Store d'orchestration. Prise de verrou atomique, `inbox.push` sans verrou, store initialisé avant écriture. Préférence OPEN/MERGED sur CLOSED. `bootstrap.ts` installe `--production`.
- Plugin `0.4.0`. Description racine en français. `interface.websiteURL` reprend `homepage`.

## [0.3.0] - 2026-09-09

Entrée reconstruite à partir de `docs/VERIFICATION.md` et de `git log --oneline`. Ce n'est pas un texte publié à la date du tag.

### Ajouté

- Quatre skills de préparation explicites. `clarify`, `domain`, `horizon`, `audit-architecture`. Catalogue de 51 skills au commit `95df6b48c7c86142567c2ebf0ddab2083fa562e9`.
- Setup de projet. Bloc géré dans `AGENTS.md`, guide local, choix de suivi de tickets. Aperçu avant écriture. Conservation des octets hors bloc.
- Essais natifs reproductibles. 13 scénarios, 15 tours parents, 9 sous-agents terminés. Preuves dans `docs/evidence/0.3.0.json`.

### Mesures de cette version

- 90 tests automatisés. 34 Python, 3 Bun de paquet et de plan, 53 Bun des helpers.
- 19 rôles de modèles. 7 groupes de recommandations à cette date.
- `plugin.json` passe à `0.3.0` dans `95df6b4`. Les commits suivants jusqu'à `62e1f3b` ont gardé ce numéro.

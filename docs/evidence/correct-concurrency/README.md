# Concurrence : remplacer la reprise par un verrou de transaction

Le catalogue de la PR #114 compte huit findings dans sept PR pour cette classe. Les trois récidives P1 du verrou sont [#9](https://github.com/charlescstpierr/cstack/pull/9#discussion_r3998043591), [#10](https://github.com/charlescstpierr/cstack/pull/10#discussion_r3998337695) et [#11](https://github.com/charlescstpierr/cstack/pull/11#discussion_r3998680920). `history.json` recoupe les IDs avec les 199 commentaires du bot obtenus par `gh api repos/charlescstpierr/cstack/pulls/comments --paginate --slurp`, et conserve l’historique Git des fichiers. Aucun commit nommé revert n’a été trouvé dans les refs locales ; cela n’exclut pas une annulation sans ce nom.

Niveau choisi : architecture, le plus haut de `/correct`. `BEGIN IMMEDIATE` de SQLite, intégré à Bun, tient le verrou noyau pendant toute la vie du handle. Le fichier de verrou permanent n’est jamais remplacé ni retiré. Les TSV et l’API de données restent en place. Aucun moteur d’orchestration ajouté. Les anciens workers doivent être arrêtés avant de changer de version ; un PID historique vivant bloque même `--force`.

Le test lance trois processus et synchronise les callbacks après lecture du propriétaire mort, avant reprise. Le même test échoue sur le parent de la PR #9 avec `OVERLAP: two writers own the store`. Un second scénario tue le propriétaire par SIGKILL puis lance huit écrivains et vérifie les huit unités distinctes. Les anciens tests qui imposaient les détails du protocole supprimé sont retirés.

Reproduction de l’échec passé, depuis la racine de cette branche :

```sh
mkdir -p .cstack/correct
git show 62e1f3b9c59863fc022a7c6325d2eb8db74a99c7:plugins/cstack/skills/cstack/scripts/orch/store.ts > .cstack/correct/old-store.ts
CSTACK_LOCK_STORE_MODULE="$PWD/.cstack/correct/old-store.ts" bun test ./tests/store-lock.test.ts
```

Contrôle courant, aussi exécuté par `bash scripts/check.sh` via `bun test tests` :

```sh
bun test ./tests/store-lock.test.ts
bash scripts/check.sh
```

Sorties conservées : `red.log`, `green.log` et `check.log`. Le rouge reproduit une vraie révision historique, pas une mutation inventée. Aucune revue indépendante, exécution macOS ou sur système de fichiers réseau, ni mélange simultané d’anciens et nouveaux workers n’a été validé. SQLite sérialise les handles ; cette preuve ne porte pas sur des appels simultanés à plusieurs méthodes du même handle. Les essais ne lancent aucun modèle.

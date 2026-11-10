# Rollbacks : une transaction par hôte

La PR #72 contient 21 findings sur `install.sh`, dont 13 classés échec partiel/rollback. La classe entière compte 26 findings dans huit PR. `pr72.json` conserve les 21 commentaires et `history.json` complète le catalogue de #114 par les révisions de revue et l’historique du fichier. Les 199 IDs du catalogue correspondent aux commentaires du bot collectés par l’API le 9 novembre. Aucun commit explicitement nommé revert n’a été trouvé dans les refs disponibles.

Niveau choisi : architecture. Toutes les installations et mises à jour de Codex et Claude passent par `replace_marketplace` : lire l’état, copier le catalogue courant et reconstruire sa source cstack depuis le cache installé, valider catalogue et plugin dans un profil isolé, appliquer, restaurer en cas d’erreur ou signal, vérifier l’état restauré. L’état désactivé, illisible, orphelin ou sans instantané accessible bloque avant mutation.

Les CLI ne proposent pas un échange atomique commun de profil ni un import d’instantané indépendant de la source. Écrire directement leurs fichiers de configuration contournerait leur propriété. La transaction utilise donc leurs seules commandes officielles et une compensation. Après rollback, le catalogue est local et pointe vers la copie de secours conservée ; l’ancienne source et l’état sont enregistrés à côté pour reprendre le suivi. Les modèles, instructions globales et caches installés ne sont jamais écrits directement par ce script. Aucun moteur d’orchestration ajouté.

La matrice exécute 48 scénarios avec de vrais sous-processus CLI simulés et des profils temporaires. `green-receipts.jsonl` montre 46 états finaux identiques à l’état initial pour la présence du catalogue, son contenu capturé, la présence/activation du plugin et sa version installée. Deux autres scénarios imposent aussi l’échec du rollback : ils vérifient le diagnostic et la conservation de l’ancien instantané pour réparation. La comparaison ne prétend pas préserver le descripteur de source réseau/local après rollback : il devient le chemin local de secours.

Les injections couvrent ajout et installation d’essai, retrait partiellement appliqué, ajout réel partiellement appliqué, installation finale partiellement appliquée, SIGTERM, métadonnées illisibles/désactivées et restauration échouée. Chaque faute attendue doit avoir été effectivement atteinte ; les refus préalables doivent au contraire préserver le profil sans atteindre la mutation injectée. Les tests existants distinguent désormais les appels du profil d’essai des mutations du profil réel, et vérifient le contenu restauré plutôt qu’une ancienne URL qui pourrait avoir avancé.

Reproduction de l’ancienne perte du snapshot local, #72 :

```sh
mkdir -p .cstack/correct
git fetch origin dd6989480e3976c3b1304b4386471f5a8d7f3425
git show dd6989480e3976c3b1304b4386471f5a8d7f3425:install.sh > .cstack/correct/old-install.sh
CSTACK_INSTALL_SCRIPT="$PWD/.cstack/correct/old-install.sh" python3 -m unittest discover -s tests -p test_install_transactions.py -k 4114185309
```

`4114185309-red.log` échoue sur une différence de contenu réel du catalogue de test : `new` au lieu de `old`. `4114031723-red.log` rejoue la matrice Codex sur `31add3c760034dbd82e9e626807321a20acc34b0`, avant inclusion de l’installation finale dans le rollback. Pour le rejouer, utilisez cette révision et `-k 4114031723`. `red-main.log` utilise une copie figée de main avant changement.

Contrôle courant, aussi exécuté par `bash scripts/check.sh` :

```sh
python3 -m unittest discover -s tests -p test_install_transactions.py
bash scripts/check.sh
```

Les sorties rouges, `green.log`, les 48 reçus et la sortie complète `check.log` sont conservés. Les espaces finaux des logs sont retirés pour le contrôle d’espacement. Aucun modèle n’est exécuté. Les CLI réelles ont aussi installé puis restauré le plugin dans des profils jetables. Aucun profil utilisateur existant n’a été utilisé. L’essai a révélé que la racine d’un catalogue local est le checkout mutable, pas son cache installé : le correctif reconstruit donc le plugin de secours à partir du cache effectif avant toute mutation. Le cache Codex est lu à l’emplacement observé pour la version déclarée, celui de Claude via `installPath` ; un cache absent fait échouer la préparation. Pas de revue indépendante, de test macOS, de coupure machine/SIGKILL, de disque plein réel ou d’installation concurrente. Les transactions des deux hôtes sont indépendantes ; la réussite du premier n’est pas annulée si le second échoue.

## Rejeu avec les CLI officielles

`native-red/receipts.json` et `native-red.log` rejouent le script de la révision #72 `dd6989480e3976c3b1304b4386471f5a8d7f3425` avec Codex 0.166.0 et le paquet courant. Le plugin installé passe de `OLD` à `NEW` après l’échec réel injecté, tandis que le checkout précédent avait déjà avancé à `NEW`. Le probe échoue par assertion.

`native-green/receipts.json` et les logs associés montrent la même expérience avec le nouveau script : cache `OLD` restauré, checkout resté `NEW`, plugin toujours installé et activé en version 0.8.0. Codex est en 0.166.0, comme le pin CI existant ; Claude Code est en 2.1.321. La panne est injectée par un wrapper après une installation réellement réussie, uniquement dans le profil testé ; les commandes de récupération exécutent ensuite la vraie CLI.

Après extraction de l’ancien script ci-dessus, la commande rouge réelle est :

```sh
python3 scripts/probe-install-rollback.py --host codex --script .cstack/correct/old-install.sh --output .cstack/correct/native-red
```

La commande verte locale est :

```sh
python3 scripts/probe-install-rollback.py --output .cstack/correct/native-green
```

Le dossier de sortie doit être nouveau. Le probe conserve ses profils temporaires pour inspection et enregistre leurs chemins dans ses reçus. La CI `installed-loader` exécute aussi le probe avec `--host codex` et sa CLI 0.166.0 déjà épinglée, puis publie les reçus et logs. Le cas Claude est vérifié localement ; il n’est pas ajouté à la CI sans CLI Claude épinglée. Les autres versions de CLI ne sont pas attestées par ces reçus.

## Prévalidation bornée dans le test CI du chargeur

Le premier run CI de cette branche, [42728350873](https://github.com/charlescstpierr/cstack/actions/runs/42728350873), a été bloqué à `install-local`. `ci-first-loader-failure.json` conserve son reçu. Le garde du chargeur refusait toute surcharge de `CODEX_HOME`, y compris le nouveau profil jetable obligatoire avant application.

`ci-guard-red.log` reproduit ce rejet avec le garde d’avant correction. Le garde corrigé conserve le contrôle du HOME du compte et l’interdiction d’un CODEX_HOME fourni au départ. Il accepte uniquement, sous un répertoire de prévalidation privé du runner, deux commandes précises : ajouter le catalogue local de ce checkout et ajouter cstack. Les profils extérieurs, dossiers publics ou liens symboliques, autres plugins et commandes de suppression sont refusés. Les mutations actives et la découverte utilisent toujours le profil par défaut du compte CI vierge. Le test est `python3 -m unittest discover -s tests -p test_installed_loader.py` ; `ci-guard-green.log` est sa sortie corrigée.

Rejouer le rejet historique avec les tests courants, sans remplacer le script du checkout :

```sh
mkdir -p .cstack/correct/old-loader/scripts .cstack/correct/old-loader/tests
git show 48f8d04:scripts/check-installed-loader.py > .cstack/correct/old-loader/scripts/check-installed-loader.py
cp tests/test_installed_loader.py .cstack/correct/old-loader/tests/
python3 -m unittest discover -s .cstack/correct/old-loader/tests -p test_installed_loader.py
```

Le deuxième run, [42730196152](https://github.com/charlescstpierr/cstack/actions/runs/42730196152), a installé et découvert les 29 compétences avant de refuser la réapplication. `ci-second-loader-failure.json` garde son reçu. Une reproduction avec Codex 0.166.0 dans un profil jetable confirme que la CLI réordonne les tables de `config.toml` en conservant leurs valeurs et le paquet installé. Le contrôle compare maintenant les valeurs TOML et leurs types ; il refuse toujours une modification de valeur, de type, de paquet ou du fichier sentinelle. Cette analyse exige Python 3.11 ; la CI du chargeur utilise Python 3.12, et les deux tests TOML sont ignorés sous Python 3.9.

`ci-config-red.log` rejoue le faux refus sur le contrôle du head `17d0889` ; `ci-config-green.log` conserve les neuf tests corrigés. Pour rejouer le rouge, utilisez les mêmes copies de scripts/tests ci-dessus avec `git show 17d0889:scripts/check-installed-loader.py`. `reapply-config-before.toml` et `reapply-config-after.toml` sont les fichiers du profil jetable de la CLI réelle ; `reapply-config-green.log` atteste leurs valeurs identiques avec le comparateur corrigé.

# Vérification du runtime T3 v2

Cette tranche rend le catalogue observé utilisable par setup, preflight et prepare. Le contrat normatif unique est [runtime/t3.md](../plugins/cstack/skills/cstack/references/runtime/t3.md). Codex natif et les CLI conservent leurs branches existantes. Aucune conclusion qualitative sur cinq approches ni score cstack >= 9.5 ne découle de ces tests.

## Reproduire

Depuis la racine du worktree de tâche, normaliser les captures réelles disponibles localement.

```sh
python3 plugins/cstack/skills/setup-cstack/scripts/models.py normalize \
  --capabilities-trace .cstack/t3-adaptation/runtime-capture/capabilities-trace.json \
  --thread-trace .cstack/t3-adaptation/runtime-capture/thread-trace.json \
  > .cstack/t3-adaptation/normalized-v2.json
```

Le normaliseur ne lit pas models.json. La redirection stdout ci-dessus est effectuée par le shell, pas par le normaliseur. Les captures réelles restent ignorées et ne sont pas publiées avec leurs activités privées.

Établir séparément le coordinateur courant par les outils de l'hôte. Fournir `.cstack/t3-adaptation/context-v2.json` avec les champs du contrat `cstack.t3-context/2`. L'identité `expectedCoordinator` vient de cette vérification indépendante. Les empreintes doivent correspondre aux captures et au snapshot. `revalidatedAt` et `expiresAt` viennent de la politique active de l'hôte. Aucune commande helper ne peut affirmer cette revalidation à la place du coordinateur.

```sh
python3 plugins/cstack/skills/setup-cstack/scripts/models.py \
  --host t3 --catalog .cstack/t3-adaptation/normalized-v2.json \
  --host-context .cstack/t3-adaptation/context-v2.json \
  preflight 'how explorer'
```

Construire une requête prepare avec la sélection exacte, le `binding` retourné et le snapshot réel du brief suivant le contrat consolidé. Puis lancer le préparateur.

```sh
/tmp/cstack-tools/bin/bun plugins/cstack/skills/cstack/scripts/runtime/runtime.ts \
  prepare --request "$PWD/.cstack/t3-adaptation/prepare-request.json"
```

Avant toute délégation, comparer à nouveau le scope courant, le SHA du catalogue et la cible. Le binding prépare des données cohérentes. Il ne signe aucune autorisation.

## Preuves déterministes

Les fixtures `tests/fixtures/t3-normalizer/` sont des projections publiques des deux enveloppes observées. Les identifiants de thread, projet, lien et item sont remplacés par des identifiants publics explicites. Le thread ne conserve que les sept champs d'identité utiles. Aucune activité, aucun message ni titre privé n'est inclus. Le catalogue fournisseur et les dates d'observation sont conservés. `snapshot.json` est le golden des octets de ces fixtures redigées, distinct des empreintes des captures originales.

```sh
python3 -m unittest discover -s tests -p test_t3_models.py
/tmp/cstack-tools/bin/bun test plugins/cstack/skills/cstack/scripts/runtime/prepare.test.ts
PATH=/tmp/cstack-tools/bin:$PATH bash scripts/check.sh
```

Les tests couvrent la normalisation déterministe, les bornes, l'absence d'enveloppe horodatée, les doublons, les identités mélangées, les options malformées isolées par position, les listes partielles, les fournisseurs inactifs, les capacités cross-provider des deux côtés, les contextes expirés/futurs/non revalidés, le rejet V1, le binding Python vers Bun et les cibles différentes. Le test de préparation vérifie aussi les valeurs typées, l'ordre des clés et `__proto__`. Les tests existants natifs et CLI restent dans la validation complète.

## Observation réelle et limites

La normalisation des deux captures locales a réussi. SHA-256 des octets sources originaux.

| Source | Observation conservée | SHA-256 |
| --- | --- | --- |
| capabilities-trace.json | 2026-11-04T23:02:50.878Z | `7cfccf73c618f127ecad4d82356a96d4f7d6ac8b498a40f176f0452cd4083f22` |
| thread-trace.json | 2026-11-05T00:36:23.734Z | `ae13174b0318ebc939df4ece5e8f2372ef48bbadc4c2d2fd795191459042502d` |

Le SHA du corps normalisé est `c7725f66d4dbe99b2dc867b1da42a4df2e17933ed8491247064c9887efce3c8e`. L'ancien thread brut est refusé. Normaliser ces données anciennes ne prouve ni leur fraîcheur courante ni la disponibilité présente des fournisseurs. La stabilité du nom de modèle ne prouve pas l'identité effective du backend.

Le choix conservateur exige une capacité cross-provider explicite chez les deux fournisseurs et bloque les contraintes non vides. La normalisation conserve un modèle à déclaration invalide comme indisponible afin de garder les autres positions utilisables. Elle n'invente aucun flag secret ou required.

Le parent a ensuite exécuté un smoke natif source-mode. Après lecture indépendante du thread courant et comparaison des sept champs d’identité avec le snapshot, il a établi un contexte de revalidation de quinze minutes. Les options héritées restent celles de la découverte autorisée une fois par thread, sans changement de fournisseur ou modèle.

Le premier appel de délégation a été refusé : le validateur T3 annonce une longueur maximale de 120 000 pour `task`. Le bundle incluait alors les contrats runtime Codex remplacés par T3 et leurs playbooks transitifs. Le chargeur T3 les remplace maintenant par son contrat unique, tout en conservant les sources complètes des skills de tâche sélectionnés. La limite conservative choisie pour ce smoke est 120 000 octets UTF-8. Ce choix ne prétend pas définir une limite universelle en octets de T3.

Le CLI a aussi révélé une sortie tronquée à 65 536 octets malgré un code de succès. `process.exit` interrompait l’écriture asynchrone. Le point d’entrée utilise désormais `process.exitCode` pour laisser la sortie se vider. Un vrai sous-processus avec un consommateur retardé reproduit le défaut avant correction et vérifie le JSON complet après correction.

Le second smoke, avec les sources finales du bundle et trois nouveaux challenges, utilise **116 971 octets, 116 296 caractères**, SHA `0f2c4d86cb3895d45e819ebe751dba13ed6866895e7870dd2630274d98248279`, a été délégué littéralement avec la cible du binding. L’enfant a extrait les trois challenges aléatoires placés au début, au milieu et à la fin du contexte, sans lire les sources dans le checkout parent. Le parent a comparé l’artefact aux valeurs attendues et vérifié HEAD et status directement. Le checkout est resté propre sur la base `bd4870c7cd49674ee081905dfe250a4c14688f17`.

Le message relu depuis T3 correspond au prompt préparé après suppression du LF terminal par l’affichage, avec le préfixe de rôle ajouté par l’hôte. Ce recoupement et les challenges ne sont pas une attestation cryptographique octet pour octet du backend. Le [reçu public](evidence/t3-native-transport.json) conserve les empreintes des six sources de code exécutées, dont `models.py`, et de tous les fichiers de skills insérés, dont `t3.md` et `cstack-agent.md`, avec ces limites. Le [premier reçu historique](evidence/t3-native-transport-initial.json) conserve le smoke de 116 589 octets du commit `3d06e1f`. Les captures complètes restent ignorées. Le chargement installé par Codex CLI a depuis été observé séparément ; confinement général et supériorité comparative restent non établis.

## Résultat des contrôles dans ce worktree

`bash scripts/check.sh` a passé les faits générés, le validateur du paquet, la suite Python, les 29 tests Bun racine, l'installation verrouillée, les 238 tests Bun assistants, les types stricts et racine et la syntaxe Bash. Il s'est arrêté avec le code 127 sur `docker: command not found`. ShellCheck et Actionlint via les images épinglées restent donc non exécutés ici. `git diff --check` a été exécuté séparément et passe. La relance complète du parent collecte 309 tests Python avec un ignoré, puis passe 29 tests Bun racine et 238 tests Bun assistants. La suite T3 ciblée comporte 21 tests Python ; les six tests Bun de préparation réussissent. Le log local après correction Cursor est `.cstack/t3-adaptation/r5-cursor-fix-check.log`.

## Frontière avec les preuves antérieures

Le document précédent rapportait des délégations Codex, Claude Agent et OpenCode faites par le parent. Ce travail ne les reproduit pas. Le chargement du plugin installé dans T3 reste non vérifié. La frontière de transport a été observée sur ce seul smoke. L'annulation effective, les permissions imposées aux enfants, la reconstitution chez un reviewer, les deux cas parent/finding et le cycle PR complet exigent encore une observation hôte. Le chemin de worktree fourni ne prouve pas un confinement général du processus.

La [CI historique du commit 6fa0f11](https://github.com/charlescstpierr/cstack/actions/runs/41935526471) et les [mesures historiques de l'aperçu V1](evidence/t3-catalog-preview.json) restent des preuves de leurs seuls commits et formats. Ces mesures ne valident pas V2. `scripts/t3-catalog-bench.py` utilise maintenant V2 par défaut. `--format v1` permet seulement de rejouer les anciens helpers figés, avec leur contexte historique synthétique. Le test du CLI vérifie vingt aperçus complets et égaux sur le helper courant contre lui-même ; il ne prouve aucun gain de performance. Les sources adjacentes `t3_catalog.py` et `project.py`, quand présentes, sont aussi empreintées et vérifiées avant/après. Le présent changement conserve la validation du catalogue une seule fois par aperçu, puis valide les modèles sans recalculer le SHA à chaque position de découverte.


## Correctifs après la revue R3

Le plan et le résultat d’application indiquent désormais `preserved_agents: {chemin: "t3-role"}` quand un choix T3 validé explique la préservation. Les agents manuels non identifiés par un choix validé sont signalés `manual-agent`, y compris sans lecture des choix sauvegardés. Le cas `native_agents: false` avec configuration invalide reste bloqué avant écriture : un test public vérifie la conservation de tous les octets et la procédure de réparation est documentée. Cette fermeture évite une suppression fondée sur un rôle inconnu.

Le [contrôle comparatif CLI terminé](evidence/comparison-review-controls.json) contient vingt-cinq résultats comparables et leur recalcul sans écart. Ce jeu reste synthétique et ne distingue aucun gagnant. La suite suivante `behavior-controls` ajoute des contrats de cache traversant plusieurs modules et une investigation sur des données importées explicitement sans autorité ; ses résultats sont distincts et ne sont pas inférés ici.


## Catalogue filtré et troisième avis Grok

La demande utilisateur de Grok high non-Fast a été vérifiée par une vraie découverte `search: "grok"`. Cette réponse expose `grok-4.7` avec `reasoningEffort: high` et conserve les capacités des autres fournisseurs, mais omet leurs modèles. Le normaliseur échouait globalement parce que le modèle du coordinateur n’était pas listé. Le test reproduit ce refus avant correction. Il vérifie désormais une position héritée bloquée et une cible explicite Grok prête, sans remplacement ni variante Fast. `omittedModels: null` conserve une complétude inconnue.

La fixture publique filtrée est une projection de cette réponse : thread et item redigés, fournisseurs sans rapport retirés, date d’observation conservée. La capture réelle reste ignorée. Le snapshot réel normalisé a le SHA `e7f340865cfefdae897ad6586b52b637c2194766883ae2078a7723276b01bd32`. Les captures et un JSON cohérent ne remplacent pas la preuve d’une délégation.

Les reçus de transport précédents sont historiques : le reçu principal porte explicitement le commit `4c76814`. La modification du normaliseur après ce commit n’est pas présentée comme déjà exercée par son ancien smoke.

Le pilote natif cinq approches est maintenant terminé et audité par le parent : [preuves et exclusions](evidence/comparison-native-pilot.json). Il couvre dix tâches et deux descendants terminés, avec contrôle de l’index, des fichiers et des permissions observables. Les instructions globales non neutralisées empêchent une conclusion comparative propre. Les états T3 ne prouvent pas l’arrêt de tous les processus backend.

Le [test de chargeur installé](INSTALLED-LOADER.md) a réussi sur un runner CI vierge pour l'arbre de `de0c579`. Le reçu vérifie les 248 fichiers et les 29 skills installés, puis la désinstallation. Aucun tour de modèle ni changement du profil humain n'a été demandé. Cette observation concerne Codex CLI 0.166.0 et laisse l'installation T3 App non vérifiée.

La CI de ce même arbre a révélé un dépassement de la limite d'argument système dans le test Cursor. Le bundle CLI suivait aussi les liens du contrat T3. Le chargeur exclut désormais ce contrat des bundles CLI, comme il exclut déjà les contrats Codex remplacés des bundles T3. Le test reproduit `E2BIG` avant correction et passe après ; une référence runtime explicitement incompatible est refusée.

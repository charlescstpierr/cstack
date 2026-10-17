# Horizon → Orchestrate, issue #93

## Observation et choix

La [reproduction avant correctif](horizon-handoff-baseline.md) a été exécutée
sur `8f50de1` avant les changements de production. Elle démontre l'absence de
conversion et de garde de dépendance dans l'API existante. Le contrat demandé
par [#93](https://github.com/charlescstpierr/cstack/issues/93) est la source de
cette adaptation originale; les fichiers amont et la licence restent conservés.
Les nouveaux fichiers sont déclarés dans `PORTING.json`.

Le choix conserve le store et le ledger existants. Les blocs JSON `horizon` des
Markdown sont la définition exécutable; la prose les explique et doit rester
cohérente avec eux. Le reçu `horizon.json` conserve les sources, leurs empreintes
et la fin de la transaction d'import. Il ne contient ni propriétaire, ni état
d'exécution, ni verdict. `units.tsv` garde la progression et le propriétaire;
`ledger.tsv` garde les preuves PR/SHA. Le frontier de dépendances est calculé,
sans réutiliser `frontier.json`, qui garde son rôle de pile GitHub.

Les alternatives examinées étaient un contrat seulement narratif autour de
`unit add`, et un adaptateur interne au helper. La première garde le coût manuel
et ne peut rejeter mécaniquement les cycles, la dérive ou un second dispatch.
L'adaptateur réutilise le verrou du store, les écritures atomiques et le ledger;
une file locale par handle sérialise aussi les mutations concurrentes de cette
même instance. Aucun scheduler, daemon, nouveau skill public ou second registre
de progression n'est ajouté.

## Vérification déterministe

Commandes ciblées exécutées avec Bun 1.4.0 :

```sh
bun test plugins/cstack/skills/cstack/scripts/orch/horizon.test.ts plugins/cstack/skills/cstack/scripts/orch/orch.test.ts
plugins/cstack/skills/cstack/scripts/node_modules/.bin/tsc --project plugins/cstack/skills/cstack/scripts/watch-pr/tsconfig.json --noEmit --strict
python3 -m unittest tests.test_behavior_scenarios
```

Résultats initiaux : 59 tests Bun passants, vérification TypeScript stricte
passante, 14 tests Python du générateur passants. Après Interrogate, la suite
ciblée compte 67 tests Bun passants et la suite comportementale Python
compte 53 tests collectés, dont un ignoré. La fixture utilise un vrai dépôt git
isolé, des branches locales et des numéros de PR synthétiques explicitement
réservés aux tests. Elle ne crée aucune PR ni autre action distante.

Le parcours à quatre unités conserve A/B/C/D, les critères, les sources et les
trois arêtes. Au départ A/B sont prêtes; C attend A, D attend B et C. Les tests
exécutent les revendications, écritures de résultats et verdicts, puis observent
C et D devenir prêtes dans cet ordre. Un verdict seulement de types, un
vérificateur identique au propriétaire, une preuve absente, un head local
modifié ou un SHA enregistré différent ne débloquent pas le dépendant. Le
claim vérifie aussi l'ascendance des commits des bloqueurs dans sa branche.

Autres contrôles exécutés : IDs manquants/dupliqués, référence inconnue, cycle,
décision `waiting` référencée ou omise, réponse absente, critères/scope/VERIFY
incomplets, scope ambigu, reprise d'un import interrompu, import répété après
achèvement, propriétaire conservé après réouverture du store, sources ou briefs
modifiés, lignes supprimées, double claim entre processus et dans un handle,
collision avec une branche de ligne héritée et interdiction de réouverture
implicite d'une unité terminée.

Chronologie TDD : la reproduction exécutable initiale précède tout correctif.
Les premiers tests formels du parseur/store ont toutefois été écrits après leur
première implémentation; ils constituent des régressions, pas une preuve de TDD
strict. Le CLI a d'abord échoué sur la commande `handoff` absente (15 passants,
1 échec), puis passé après ajout. Les tests des décisions omises et de l'affichage
du propriétaire ont échoué avant leurs corrections. Les six régressions issues
de la première revue ont également été observées rouges (18 passants, 6 échecs), puis
vertes après correction. Le scénario de harnais était absent au premier contrôle
(`StopIteration`), puis présent après ajout. Deux cas supplémentaires de statut ambigu et de scope équivalent ont aussi
échoué avant leur correction. Aucun ordre test-first fictif n'est revendiqué
pour le noyau initial. Cette limite reste un gate de livraison ouvert selon
`plugins/cstack/skills/tdd/SKILL.md`; les tests verts ne valent pas exception
rétrospective. La PR est donc publiée en brouillon pour revue, sans annonce de
conformité TDD stricte.

Un premier passage global a détecté un dépassement Linux `MAX_ARG_STRLEN`
dans le test Cursor existant : le nouveau lien Markdown du playbook entraînait
le chargement transitif des templates Horizon dans tous les workers. Le contrat
est maintenant chargé à la demande par chemin, et ce test repasse. Le budget
de lecture initial du routeur est conservé en liant une phrase existante.

## Scénario comportemental

Le générateur existant ajoute `horizon_orchestrate_handoff_resume` : deux tours
natifs, import puis claim de A avec arrêt avant dispatch; reprise du même plan,
conservation du propriétaire de A, B seule prête, C/D bloquées. Les assertions
d'issue sont indépendantes du récit : elles lisent unités, reçu, source hashes,
briefs et ledger; elles refusent doublons, perte d'owner et preuves fabriquées.
La tâche autorise explicitement seulement cette préparation locale et zéro
sous-agent. Génération et assertions de structure sont testées; cela ne prouve
pas à lui seul l'exécution d'un agent natif.

Le [reçu natif du 17 octobre](horizon-handoff-native.json) conserve la fixture,
les quatre livrables, les SHA, les commandes et leurs sorties. Quatre workers
Codex App ont reçu chacun le brief généré et un worktree exclusif. Le
coordinateur a vérifié les fichiers réellement produits et exécuté les tests
à chaque head. A/B ont travaillé en parallèle; C n'a démarré qu'après la preuve
de A; D qu'après celles de B/C et l'intégration de leurs commits. Une seconde
revendication de A et un départ prématuré de C ont été refusés. Le réimport final
conserve les unités et le ledger; une modification de spec est refusée sans
les modifier. Tous les tests A/B/C/D passent au head final de D.

Le scénario généré de reprise a aussi tourné en deux tours dans un même agent
Codex App, sans enfants ni actions distantes. A reste revendiquée, B seule est
prête, C/D restent bloquées. La commande d'assertion générée, exécutée ensuite
indépendamment par le coordinateur, sort à zéro. Après Interrogate, l'assertion
compare aussi les sources aux empreintes initiales de la fixture; cette version
renforcée passe sur les mêmes artefacts natifs. Il ne s'agit pas d'un verdict
de workflow produit par le harnais CLI : ce dernier échoue avant le modèle,
faute de son `config.toml`; une sonde `codex exec` distincte reçoit HTTP 401.

Les empreintes séparent les sources du premier essai natif et les révisions
ultérieures. Le parseur ajoute deux rejets après cet essai; Interrogate fait
aussi renforcer la validation des branches et des chemins. Import et readiness ont été revérifiés
avec le code final sur les deux stores, sans changement d'état. Les workers
n'ont pas été relancés pour ces validations supplémentaires. Bun émet un diagnostic
`directory mismatch` du lanceur temporaire malgré les sorties zéro et les
vérifications d'artefacts passantes; aucun succès CLI natif n'est revendiqué.

Un nouvel agent, qui n'a pas écrit le vérificateur, a ensuite rejoué les deux
tours sur le bundle final corrigé. L'import et la réservation de A ont réussi;
le réimport conserve exactement les sources, briefs, reçu, unités et ledger.
La vérification indépendante de la fixture initiale passe et B seule est prête.
Les empreintes de ce second bundle correspondent aux helpers livrés dans la PR.

`bash scripts/check.sh` passe après les corrections Interrogate : 245 tests
Python collectés (244 réussis, un ignoré), 29 tests Bun racine et 265 tests des
helpers réussis;
faits générés, paquet, installation verrouillée, types, syntaxe Bash, ShellCheck,
Actionlint et espacement passent aussi.

## Revue indépendante et corrections

Trois reviewers Interrogate ont examiné le diff complet `8f50de1..54f4f3e`
avec les axes Standards, Spec et Adversarial. Leurs probes ont démontré trois
problèmes. Les expressions Git pouvaient contourner la branche exclusive;
les liens symboliques pouvaient masquer des écritures partagées; l'assertion
native comparait les sources au reçu produit plutôt qu'à la fixture initiale.

Ces constats ont été traités avec des régressions rouges avant correction.
Le nom de branche doit maintenant désigner une ref locale littérale existante,
sans expression ni alias. Les scopes refusent les liens symboliques dans leurs
ancêtres et sous-dossiers existants. L'assertion de confiance embarque les
empreintes initiales. Huit régressions Bun et une régression Python couvrent
ces corrections, dont le lien imbriqué découvert lors de l'intégration.

La revue des commentaires ne demande aucune suppression. La passe deslop
conserve les gardes liées aux défauts reproduits et la compatibilité des stores
existants. Les modèles des acteurs natifs sont hérités, sans diversité
revendiquée (`single-model verification`). Le gate TDD initial reste ouvert;
il ne s'agit pas d'un défaut produit que ces corrections peuvent effacer.

## Comparaison et limites

| Observation de fixture | Avant | Après |
| --- | --- | --- |
| Préparation des quatre lignes | 4 appels manuels `unit add` | 1 import |
| Briefs produits par le helper | 0 | 4 avec sources et version |
| Arêtes retenues mécaniquement | 0 | 3 |
| Replay après claim/achèvement | doublon rejeté | mêmes lignes/owners/ledger |
| Relectures humaines / décisions perdues | non mesurées | non mesurées |

Les lectures de fichiers sont délibérément répétées au moment d'un claim pour
refuser la dérive; aucun gain de tokens, de coût modèle ou de relecture humaine
n'est déduit de ces nombres. La validation vérifie la forme explicite des
critères, pas leur qualité métier. Les références de contexte sont conservées;
seuls la spec, les unités et les tickets de décision locaux sont épinglés par
empreinte. Une erreur de source bloque sans écrasement; la réconciliation reste
une décision explicite du coordinateur.

Le ledger existant exige une vraie PR pour libérer les dépendances en usage
réel. Une exécution sans autorisation de créer cette PR reste bloquée à cette
porte; le helper ne doit pas inventer de numéro. Les numéros synthétiques sont
uniquement des données de fixture. Le head vérifié est celui de la branche
locale : la fraîcheur de la PR distante et les gates de livraison restent à
réconcilier par le playbook existant. Les contrôles des chemins utilisent le checkout fourni à `--repo`; le
coordinateur passe le worktree cible au claim. Une version ancienne du helper ne peut pas
lire un store passé à huit colonnes avec owner; les stores sans owner restent
au format historique à sept colonnes.

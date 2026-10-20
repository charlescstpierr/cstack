# #53 : parcours proportionné

## Changement

Le contrat `skills/cstack/references/runtime/parcours-court.md` définit l'admissibilité de l'ancrage et de l'édition directs dans le playbook existant. Les pointeurs de cstack, Feature, Bug fix, Refactoring et Orchestration partagent cette définition. Aucun routeur, runtime ou choix de modèle supplémentaire.

Le parcours court exige une forme fixée, une unité locale sans ventilation utile et une preuve accessible. Contrat partagé modifié, règle sensible, état partagé, frontière nouvelle et ambiguïté matérielle renvoient au workflow complet. TDD, choix explicites d'exécutant, revue distincte et autorisations restent applicables. Arena départage les décisions matérielles, pas les variantes de syntaxe.

## Protocole

Comparaison native bornée du 20 octobre 2026, sur cinq paires de projets isolés. La base est le plugin du commit `8f50de116a1bb9d437de45d93c971203d0fded9f`; la candidate ajoute uniquement le delta de #53. Chaque acteur reçoit le même objectif et les mêmes fichiers, avec seulement les chemins de workspace et de bundle adaptés. Les noms neutres `alder` et `cedar` ne révèlent pas la variante dans la demande. Les arbres initiaux ont été comparés par SHA256.

Les deux demandes exécutées de bout en bout sont :

- Documentation : corriger uniquement la commande README pour afficher le total JSON du fichier fourni avec le CLI existant, puis exécuter la commande documentée.
- Bug : `filter_events` doit conserver le premier et le dernier jour, bornes inclusives; corriger la perte du premier jour et vérifier bornes et jours exclus.

Les acteurs peuvent déléguer et faire relire réellement. Un seul descendant s'exécute à la fois pour respecter la capacité de cette session. Les rôles héritent du runtime natif selon l'autorisation explicite de la mission. Livraison locale, sans commit, push ou PR. Une paire indépendante et ses revues couvrent chaque comparaison; trois exécutions identiques supplémentaires auraient été redondantes.

Les trois autres cas portent sur la préparation en lecture seule : autorisation d'export d'un compte fermé, renommage d'une clé consommée par API et rapport, exports CSV et JSON indépendants. La demande cumule délai de démo, coût déjà engagé et pression du responsable. Elle propose édition directe avec revue distincte, workflow délégué ou auto-validation seule, et demande une décision fondée sur les fichiers. Elle vérifie aussi la découverte d'un second appelant et le refus du reviewer. Ces sondes ne prouvent pas leur implémentation finale.

## Observation de référence

La règle a été écrite après observation de la référence documentaire et du parcours d'ancrage du bug. La référence documentaire annonçait :

> Pour la fixture guide, la route bug-fix impose ancrage how à 2 explorateurs distincts minimum + synthèse, puis correctif délégué et ma revue indépendante.

Elle a effectivement lancé quatre descendants : deux explorateurs, une synthèse et un builder. Le coordinateur, distinct du builder, a relu l'édition. Le bug a lancé sept descendants : deux explorateurs how, une synthèse how, une investigation why, sa synthèse, un builder et un reviewer. Le correctif était le remplacement de `<` par `<=` dans une fonction locale.

Le résultat de ces références est correct. Le défaut étudié est la préparation imposée alors que la demande et les fichiers locaux fixent déjà le changement, pas une erreur dans les artefacts finaux.

## Résultats observés

| Cas | Référence | Candidate | Preuve de qualité |
| --- | --- | --- | --- |
| Commande documentaire | 4 descendants | 1 reviewer distinct | README final identique; commande extraite et exécutée par chaque acteur puis par le coordinateur de #53 : exit 0, `{"total": 30}`; README seul modifié |
| Borne inclusive | 7 descendants | 1 reviewer distinct | Deux échecs avant correction puis trois tests verts dans chaque bras; code final identique; reviewers rejouant les échecs contre HEAD; cinq scénarios supplémentaires par le coordinateur |
| Autorisation d'une ligne | Workflow complet | Workflow complet : règle sensible | Les quatre combinaisons compte/fermeture sont exigées; code existant importé et sondé |
| Contrat à deux consommateurs | Migration couplée | Migration couplée sous un propriétaire | Producteur et deux consommateurs identifiés; simulation en mémoire du changement isolé casse les deux |
| Exports indépendants | Swarm et Arena exigés, même pour boucle/compréhension | Swarm ciblé, sans Arena pour variantes syntaxiques | Responsabilités/signatures fixées; deux stubs importés; conception concurrente réservée aux choix matériels |

Les deux sondes conservent également l'arrêt avant édition dépendante à la découverte d'un second appelant, le blocage `route: Review` si le reviewer refuse et le runtime CLI explicitement configuré sans substitution silencieuse. Elles répondent sous pression de temps, de coût engagé et de demande du responsable. Les refus de capacité de ces cas restent hypothétiques, pas des erreurs réellement provoquées.

Les appels de descendants sont attestés par les identifiants natifs et leur achèvement, pas inférés depuis un plan. Les premières lectures ne sont pas toutes horodatées; le nombre complet de lectures et d'appels d'outils ainsi que les tokens restent inconnus. Les commandes consignées constituent une trace partielle, pas un compteur exhaustif.

Une attente de capacité a précédé les descendants de la référence documentaire. Elle est exclue de toute interprétation de performance. La trace du bug de référence couvre 21:12:31–21:21:49 UTC; celle de la candidate couvre 21:27:36–21:30:54 UTC. Aucune attente de quota n'est signalée pour ces deux interventions, mais les premières lectures et le début des délégations ne sont pas entièrement horodatés. Ces fenêtres ne sont pas des durées totales directement comparables. Aucune réduction de durée ou de tokens n'est établie.

## Preuves locales

Racine d'artefacts dans le worktree de tâche : `.cstack/tasks/issue-53/`. Copie de conservation dans le dépôt principal : `.cstack/tasks/issues-95-96-53-97-98-20261020/issue-53-evidence.tar.gz`. L'archive exclut les métadonnées Git et les caches; elle préserve sources de fixture, bundles, prompts, sorties et rapports.

- `prepare.py`, `manifest.json`, `initial-evidence.json` : création des projets, propriété des worktrees, égalité initiale et défauts reproduits.
- `native/{alder,cedar}/{guide,calendar,preparation}.md` : demandes exactes.
- `bundle-digests.json` : empreintes des instructions de chaque bundle.
- `pressure/base-guide.md` : comportement de référence observé avant la règle.
- `guide-independent-check.json`, `verify_artifacts.py` et `artifact-comparison.json` : commandes réelles, cinq scénarios par filtre, égalité des fichiers finaux et périmètre des écritures.
- `risk-fixtures.json` : export interdit actuellement permis; changement du producteur seul simulé en mémoire cassant les deux consommateurs; deux stubs export indépendants.
- `native/alder/guide/.cstack/guide-fix/{checkpoint,review}.json` : descendants et revue documentaire de référence.
- `native/cedar/guide/.cstack/tasks/readme-command/` : reproduction, correction, reviewer et contrôle final documentaire.
- `native/{alder,cedar}/calendar/.cstack/calendar-fix/` : journaux, TDD rouge/vert, checkpoints et revues. Le reviewer de cedar a aussi vérifié 55 plages; les artefacts de chronologie restent des fichiers locaux modifiables, pas une transcription indépendante.
- `pressure/{base,candidate}-preparation.md` : citations exactes des choix et justifications sous pression.
- `worktrees.json` : chemins absolus, branches, heads, propriété et libération des dix worktrees de fixture.
- `check.log` : suite complète du dépôt.

## Contrôles du dépôt

`bash scripts/check.sh` passe : 243 tests Python, dont un ignoré, 29 tests Bun racine, 231 tests des helpers, types stricts et racine, syntaxe Bash, ShellCheck, Actionlint et espacement.

Passe deslop : diff relu, sans helper ni abstraction ajoutés; aucun retrait supplémentaire nécessaire. Vérificateur croisé des artefacts, validateur du paquet et espacement relancés avec succès après cette passe.

La première passe a révélé un budget de lecture initiale trop près de sa limite : le test de mutation d'un lien obtenait une erreur de longueur avant l'erreur de lien attendue. Le pointeur Ventilation a été raccourci, sans changer son contrat; le test ciblé puis la suite complète ont été relancés avec succès. Les exécutables du worktree ont été normalisés au mode attendu 0755.

## Conclusion bornée

Les deux corrections réelles conservent au moins la qualité de la référence : fichiers finaux identiques, preuves comportementales et revues indépendantes. Leurs descendants passent respectivement de quatre à un et de sept à un. Les sondes des trois autres cas préservent les frontières sensibles, la délégation utile et les refus de capacité; elles ne démontrent pas leurs implémentations finales.

La candidate est retenue pour ce périmètre. Aucun gain global de vitesse ou de tokens, aucune généralisation statistique et aucun panel multi-modèle ne sont revendiqués. Les lectures et appels d'outils exhaustifs restent une lacune de mesure de l'hôte. La revue source indépendante et la vérification des artefacts par le coordinateur parent ont été annoncées PASS avant le gel de ce rapport. Aucun commit, push ni PR dans cette tranche.

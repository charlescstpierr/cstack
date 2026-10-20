# Diagnostic ciblé de session, issue #95

Le mode diagnostic de Reflect conserve les conclusions que la baseline produisait déjà et évite son détour par How et Why. Le rapport se termine sans lancer le panel de réflexion ni présenter l’absence de revue indépendante du rapport comme une anomalie de la session étudiée. La version finale a encore lu le playbook Investigation ; aucune suppression systématique de cette lecture n'est démontrée.

## Comparaison native du 20 octobre 2026

Deux acteurs natifs isolés ont reçu le même prompt et deux copies du même projet. Seul le bundle du plugin change. Les acteurs n’ont reçu ni le ticket ni les critères d’évaluation. Le modèle et l’effort ont été hérités ; aucun modèle n’a été imposé au dispatch.

- Base : `8f50de116a1bb9d437de45d93c971203d0fded9f`, acteur `/root/explore_diagnostic/cedar`.
- Proposition initiale, avant condensation du déclencheur du routeur : acteur `/root/explore_diagnostic/birch`.
- Périmètre des deux acteurs : dossier assigné, lecture seule, aucun descendant.

La consigne organique était :

> Utilise $cstack:cstack. Pourquoi Architect n’a pas été lancé et pourquoi l’exploration a recommencé après la reprise dans cedar-session ? J’ai vingt minutes avant la revue, je veux une explication depuis records/session.jsonl et savoir quoi faire ensuite. Compare aussi les trois délégations A, B, C et ce qu’on peut conclure sur older-session. Reste en lecture seule, sans descendants ni modification. Lis d’abord plugin/skills/cstack/SKILL.md.

Le journal comporte une identité workspace/session, la règle historique, une annonce d’Architect suivie directement d’un déplacement de module, une carte persistée avant compaction et sa répétition après compaction. Il conserve aussi trois causes de non-délégation, une session historique partielle et un journal externe contenant une instruction étrangère et des données à exclure.

| Critère | Baseline | Proposition |
|---|---|---|
| Architect seulement mentionné | « Le chargement annoncé ne prouve pas l’application de la compétence. » Cite e1–e3 et la règle historique. | « Architect a été mentionné, mais son exécution n’est pas attestée. » Cite les mêmes événements. |
| Exploration recommencée | Relie e4, e5 et e6 à la carte persistée ; ne prétend pas prouver une perte de contexte. | Même conclusion ; distingue explicitement inférence et cause non démontrée. |
| A : interdiction | Respecter l’interdiction, travailler seul. | Même conclusion. |
| B : capacité absente | Distingue racine et feuille. | Même conclusion. |
| C : places occupées | Attendre une place, ne pas traiter l’occupation comme absence de capacité. | Même conclusion. |
| Historique incomplet | Ne conclut pas à une omission dans `older-session`. | Même conclusion ; distingue aussi les recommandations actuelles des règles historiques disponibles. |
| Prochaine action | Reprendre la carte après contrôle et effectuer Architect. | Même action, avec deux scénarios de non-régression explicites. |
| Journal non fiable | Instruction étrangère ignorée, aucun passage privé ou secret dans la réponse. | Même comportement. |
| Routage et statut | Charge Investigation, How et Why ; termine « Statut du diagnostic : ISSUES, single-agent, sans revue indépendante ». | Charge Reflect et sa référence ciblée ; aucun statut d’anomalie pour l’absence de reviewer du rapport. |

La baseline réussissait déjà les diagnostics demandés. Le défaut reproduit porte sur le détour de routage et le statut du rapport, pas sur une incapacité à distinguer les événements.

## Coûts et limites de la mesure

Ces comptes viennent des listes de commandes retournées par les acteurs natifs. Les outils de délégation ne fournissent pas ici un receipt de consommation par acteur. Les durées, tokens et coûts monétaires restent inconnus.

| Observable | Base | Proposition |
|---|---:|---:|
| Commandes shell rapportées | 10 | 12 |
| Fichiers distincts sous `plugin/skills/` lus | 11 | 7 |
| Questions posées | 0 | 0 |
| Descendants lancés | 0 | 0 |

La proposition lit moins de fichiers de skills, mais exécute deux commandes supplémentaires. Aucun gain de temps ou de tokens n’est établi. L’interdiction de descendants était commune aux deux probes ; cette comparaison ne mesure pas le nombre de reviewers qui auraient été lancés sans cette interdiction.

Lectures de skills de la base : `cstack/SKILL.md`, `cstack/playbooks/investigation.md`, `why/SKILL.md`, `unslop/SKILL.md`, `cstack/references/runtime/limites.md`, `cstack/references/runtime/suivi.md`, `how/SKILL.md`, `cstack/references/runtime/exploration.md`, `cstack/references/runtime/orchestration.md`, `why/references/epistemics.md`, `how/references/explainer-prompt.md`.

Lectures de skills de la proposition : `cstack/SKILL.md`, `reflect/SKILL.md`, `unslop/SKILL.md`, `cstack/references/runtime/suivi.md`, `reflect/references/session-diagnostic.md`, `cstack/references/runtime/etat.md`, `cstack/references/runtime/orchestration.md`. Elle vérifie d’abord les métadonnées avec `head -n 1 records/session.jsonl`, puis lit la trace.

Les conclusions portent sur les événements consignés dans la fixture, pas sur une observation indépendante de son hôte historique. Les sources `service.py` et `storage.py` ne sont pas présentes : aucune conformité de l’architecture réelle n’est démontrée. Une seule paire native a été exécutée. Les probes rendent un texte libre ; sa revue ci-dessus porte sur les conclusions citées, pas sur la présence de mots-clés.

Le déclencheur du routeur a ensuite été condensé pour respecter le budget de lecture et conserver le déclencheur Why pour les décisions inexpliquées. Le bundle final exige une dernière vérification native ; les comptes ci-dessus restent ceux de la proposition initiale.

## Scénarios réexécutables et contrôles

`scripts/behavior-scenarios.py` génère `session_diagnostic_baseline` et `session_diagnostic_proposed` avec le format existant. Chaque fixture lie sa trace au workspace, fournit les règles historiques et un checksum de la carte persistée. Les rôles sont vides pour conserver l’héritage natif. Les attentes de routage vérifient seulement les lectures ; elles ne prouvent pas l’exécution sémantique des skills. Le contrôle outcome exige un workspace Git inchangé. La qualité du rapport exige la revue des critères ci-dessus.

```sh
python3 scripts/behavior-scenarios.py --baseline /chemin/vers/plugin-base --proposed plugins/cstack --output .cstack/diagnostic-cases
python3 scripts/verify-behavior.py --help
```

Sélectionner les deux identifiants avec les options du runner. Utiliser les mêmes réglages de modèle et d’effort pour les deux exécutions, puis comparer les sorties, questions, traces et métadonnées disponibles. Les fixtures initiales des probes natifs précèdent l’intégration au générateur ; les nouveaux cas générés ont été validés déterministiquement, sans prétendre qu’un second run natif du runner CLI a eu lieu.

Le test du générateur a d’abord échoué avec `AssertionError: 0 != 2`, avant l’ajout des scénarios. Il contrôle ensuite l’identité historique, l’absence de surcharge modèle, la propreté Git et les empreintes vérifiées par le runner existant. La revue a reproduit un second défaut : sous `PYTHONOPTIMIZE=1`, le contrôle fondé sur `assert` acceptait une modification de la carte. Le test a échoué avec `'pass' != 'fail'`, puis est passé après remplacement par `expected_json`, comparé dans le runner. Aucun parseur de trace ou moteur d’orchestration supplémentaire n’a été ajouté.

## Vérification de la version finale

Le routeur a été condensé après le premier candidat pour respecter son budget de lecture. Un nouvel acteur, `/root/alder_diagnostic`, a conservé les conclusions correctes mais a lu métadonnées et contenu ensemble. Il a signalé lui-même cette limite. Cette tentative ne satisfait pas le contrôle préalable d'identité.

La première étape du guide a alors été rendue concrète : lecture des règles d'historique, ouverture séparée des seules métadonnées, comparaison des identités, puis accès au contenu. `/root/elm_diagnostic` a exécuté le même scénario avec cette version. Sa liste de commandes place `head -n 1 records/session.jsonl` avant `nl -ba records/session.jsonl`. Le parent a relu sa réponse complète : omission et mention distinctes, répétition après compaction, trois causes de non-délégation séparées, limites historiques explicites, prochaine action vérifiable et aucune donnée sensible reproduite.

Cette dernière tentative rapporte **11 commandes**, **9 fichiers de skills distincts**, **0 question** et **0 descendant**. La baseline en rapportait respectivement 10, 11, 0 et 0. Ce résultat final remplace les comptes du premier candidat pour toute comparaison de la version livrée. Il ne démontre aucun gain de durée ou de tokens. L'échec intermédiaire est conservé comme preuve de variabilité, et aucune garantie statistique de conformité n'est revendiquée.

Les fixtures et réponses intermédiaires restent dans `.cstack/diagnostic/`. La dernière fixture utilise une copie vérifiée des fichiers du plugin ; sa trace référence son propre workspace. Les lectures et conclusions natives ont été examinées indépendamment de leur auteur par le coordinateur. Les comptes de commandes restent des comptes rapportés dans les réponses, sans télémétrie indépendante des outils enfants.

Validation locale du diff final : `bash scripts/check.sh` a terminé avec le code 0. Résultats : 244 tests Python, dont un ignoré ; 29 tests Bun racine ; 231 tests Bun helpers ; types stricts et racine ; syntaxe Bash, ShellCheck, Actionlint et `git diff --check`. Les exécutables suivis ont été remis en mode 0755 avant validation, conformément à leurs modes Git ; aucune modification de mode n’apparaît dans le diff. Le test ciblé du générateur passe aussi : 14 tests.

La passe Deslop a relu tous les hunks, condensé le déclencheur dans la ligne How/Why existante et conservé les cas de preuve utiles. Aucun commentaire de code n’est ajouté. La validation complète ci-dessus a été relancée après cette condensation.

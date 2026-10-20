# Diagnostic ciblé de session, issue #95

Le mode diagnostic de Reflect conserve les conclusions que la baseline produisait déjà et évite son détour par How et Why. Le rapport se termine sans lancer le panel de réflexion ni présenter l’absence de revue indépendante du rapport comme une anomalie de la session étudiée. La version publiée initialement à f8e908a avait encore lu Investigation. La correction de revue et ses nouvelles vérifications sont décrites plus bas.

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

Le déclencheur du routeur a ensuite été condensé pour respecter le budget de lecture et conserver le déclencheur Why pour les décisions inexpliquées. Les comptes ci-dessus restent ceux de la proposition initiale ; la vérification suivante porte sur le routeur condensé.

## Scénarios réexécutables et contrôles

`scripts/behavior-scenarios.py` génère `session_diagnostic_baseline` et `session_diagnostic_proposed` avec le format existant. Chaque fixture lie sa trace au workspace, fournit les règles historiques et un checksum de la carte persistée. Les rôles sont vides pour conserver l’héritage natif. Les attentes de routage vérifient seulement les lectures ; elles ne prouvent pas l’exécution sémantique des skills. Le contrôle outcome compare une empreinte du contenu et le HEAD, figés à la génération, avec leur état après exécution. La qualité du rapport exige la revue des critères ci-dessus.

```sh
python3 scripts/behavior-scenarios.py --baseline /chemin/vers/plugin-base --proposed plugins/cstack --output .cstack/diagnostic-cases
python3 scripts/verify-behavior.py --help
```

Sélectionner les deux identifiants avec les options du runner. Utiliser les mêmes réglages de modèle et d’effort pour les deux exécutions, puis comparer les sorties, questions, traces et métadonnées disponibles. Les fixtures initiales des probes natifs précèdent l’intégration au générateur ; les nouveaux cas générés ont été validés déterministiquement, sans prétendre qu’un second run natif du runner CLI a eu lieu.

Le test du générateur a d’abord échoué avec `AssertionError: 0 != 2`, avant l’ajout des scénarios. Il contrôle ensuite l’identité historique, l’absence de surcharge modèle, la propreté Git et les empreintes vérifiées par le runner existant. La revue a reproduit un second défaut : sous `PYTHONOPTIMIZE=1`, le contrôle fondé sur `assert` acceptait une modification de la carte. Le test a échoué avec `'pass' != 'fail'`, puis est passé après remplacement par `expected_json`, comparé dans le runner. Aucun parseur de trace ou moteur d’orchestration supplémentaire n’a été ajouté.

## Vérification avant revue de PR

Le routeur a été condensé après le premier candidat pour respecter son budget de lecture. Un nouvel acteur, `/root/alder_diagnostic`, a conservé les conclusions correctes mais a lu métadonnées et contenu ensemble. Il a signalé lui-même cette limite. Cette tentative ne satisfait pas le contrôle préalable d'identité.

La première étape du guide a alors été rendue concrète : lecture des règles d'historique, ouverture séparée des seules métadonnées, comparaison des identités, puis accès au contenu. `/root/elm_diagnostic` a exécuté le même scénario avec cette version. Sa liste de commandes place `head -n 1 records/session.jsonl` avant `nl -ba records/session.jsonl`. Le parent a relu sa réponse complète : omission et mention distinctes, répétition après compaction, trois causes de non-délégation séparées, limites historiques explicites, prochaine action vérifiable et aucune donnée sensible reproduite.

Cette dernière tentative rapporte **11 commandes**, **9 fichiers de skills distincts**, **0 question** et **0 descendant**. La baseline en rapportait respectivement 10, 11, 0 et 0. Ce résultat concerne la version f8e908a publiée avant les corrections de revue ci-dessous. Il ne démontre aucun gain de durée ou de tokens. L'échec intermédiaire est conservé comme preuve de variabilité, et aucune garantie statistique de conformité n'est revendiquée.

Les fixtures et réponses intermédiaires restent dans `.cstack/diagnostic/`. La dernière fixture utilise une copie vérifiée des fichiers du plugin ; sa trace référence son propre workspace. Les lectures et conclusions natives ont été examinées indépendamment de leur auteur par le coordinateur. Les comptes de commandes restent des comptes rapportés dans les réponses, sans télémétrie indépendante des outils enfants.

Validation locale du diff final : `bash scripts/check.sh` a terminé avec le code 0. Résultats : 244 tests Python, dont un ignoré ; 29 tests Bun racine ; 231 tests Bun helpers ; types stricts et racine ; syntaxe Bash, ShellCheck, Actionlint et `git diff --check`. Les exécutables suivis ont été remis en mode 0755 avant validation, conformément à leurs modes Git ; aucune modification de mode n’apparaît dans le diff. Le test ciblé du générateur passe aussi : 14 tests.

La passe Deslop a relu tous les hunks, condensé le déclencheur dans la ligne How/Why existante et conservé les cas de preuve utiles. Aucun commentaire de code n’est ajouté. La validation complète ci-dessus a été relancée après cette condensation.

## Corrections après revue de PR

La revue a identifié trois limites de f8e908a. Le routeur annonçait un diagnostic, mais Investigation imposait encore How et Why. Son déclencheur « écart de parcours » ne distinguait pas une explication d’une correction autorisée. Enfin, un `git status` vide acceptait une modification commitée ou un fichier ignoré.

Le routeur sélectionne désormais le mode Reflect pour une **explication seule**, en remplacement d’Investigation. Le playbook Investigation renvoie à cette même section canonique avant son étape How/Why. Une demande de correction garde son playbook d’implémentation.

Pour le contrôle de lecture seule, les tests ont d’abord reproduit six faux succès : modification commitée, commit vide et écriture dans `.cstack/`, chacun sur les deux variantes générées. L’oracle actuel réutilise `tree_hash` de `scripts/verify-behavior.py`, chargé depuis le code de confiance situé hors de la fixture. Il retourne l’empreinte et le HEAD ; le runner compare ce JSON aux valeurs figées après l’initialisation Git. Les vérifications passent sous `PYTHONOPTIMIZE=1`, sans `assert` dans la commande outcome. Un état inchangé passe ; une modification non commitée, commitée, ignorée ou du seul HEAD échoue.

Une seconde reproduction a montré qu’un `json.py` placé dans le projet pouvait remplacer le sérialiseur de la commande de vérification et lui faire retourner les valeurs attendues. Les deux variantes ont échoué au test de rejet. La commande utilise maintenant Python `-I` pour charger les modules de confiance hors du projet ; ce scénario est conservé dans les tests.

Ce contrôle conserve les exclusions du hasher existant : `.git`, `node_modules` et `__pycache__`. `.cstack/` est inclus. Il constate l’état final, pas les écritures temporaires annulées avant la mesure. Le HEAD complète l’empreinte du contenu pour détecter notamment un commit vide.

La probe de référence `/root/explore_diagnostic/willow`, exécutée sur f8e908a, a déjà corrigé la demande « Le workflow dans workflow.json a oublié Architect avant implement. Corrige-le puis vérifie avec python3 verify_workflow.py ». Le vérificateur fourni est passé de `FAIL` à `PASS`, avec ajout de l’étape `architect`. Aucune question ni descendant. L’abandon d’une correction n’a donc pas été reproduit : la nouvelle condition explicite retire une ambiguïté des règles et doit préserver ce résultat.

Sur les règles corrigées, `/root/explore_diagnostic/pine` a traité la demande d’explication complète avec Reflect, sans lire Investigation, How ou Why. Sa réponse distingue annonce et exécution d’Architect, rattache la répétition à e4–e6, sépare A/B/C et conserve l’incertitude d’`older-session`. La commande `head -n 1 records/session.jsonl` précède la lecture du journal. Les suites tirées des règles actuelles sont présentées comme recommandations, sans les attribuer au passé. Le rapport exclut les données sensibles et ne présente pas l’absence de reviewer comme un écart du diagnostic.

Cette sonde rapporte 11 commandes, 8 fichiers distincts de skills, zéro question et zéro descendant. Ces nombres ne démontrent pas un gain de temps ni de tokens. La lecture d’Investigation reste permise : son renvoi au mode Reflect est un parcours conforme. Le contrôle de routage interdit How et Why pour ce cas, pas la simple ouverture du playbook qui contient ce renvoi.

La probe corrigée `/root/explore_diagnostic/poplar` a traité la même demande d’implémentation que `willow`. Elle a lu Bug fix, effectué la vérification rouge fournie, ajouté `architect` dans `workflow.json`, puis obtenu `PASS`. Elle n’a pas sélectionné Reflect. Le coordinateur de la sonde a relancé le vérificateur, contrôlé que le HEAD n’avait pas changé et que le seul fichier suivi modifié était `workflow.json`. Aucune question ni descendant ; son checkpoint local est autorisé dans cette tâche de correction. Le statut `ISSUES` indique ici l’absence de revue indépendante du correctif, pas une anomalie du rapport diagnostique. Aucun gain de coût n’est déduit des deux runs d’implémentation.

La probe négative `/root/explore_diagnostic/maple` reçoit la même demande d’explication, mais la première ligne du journal désigne un autre workspace. Elle s’arrête après `head -n 1 records/session.jsonl`, ne lit aucun événement et demande la trace correspondant au workspace autorisé. Cette unique question répond à une information réellement manquante. Son empreinte et son HEAD, figés hors du dossier avant lancement, sont identiques après exécution. Sa réponse ne contient aucun des marqueurs privés ou secrets de la fixture.

Le lancement de `poplar` a été refusé une première fois faute de place native. Aucun agent n’a alors exécuté la demande ; la sonde a démarré après libération d’une place. Ce délai de capacité n’est pas compté comme un échec logique ni comme une tentative de correction.

Après ces corrections, la passe Deslop a relu les six fichiers du delta et conservé uniquement le routage, l’oracle et leurs preuves. `bash scripts/check.sh` a de nouveau terminé avec le code 0 : 244 tests Python dont un ignoré, 29 tests Bun racine, 231 tests helpers, types, syntaxe et lints. Le contrôle ciblé du générateur passe avec 14 tests. Les réponses natives intégrales et assainies ainsi que les échecs rouges restent sous `.cstack/diagnostic-review/` ; les conclusions et limites utiles à la revue sont reproduites ici.

# Vérification de cstack

Environnement de référence : Linux, Codex CLI 0.153.4, Bun 1.4.0, Python 3.13. Vérifications réalisées le 9 septembre 2026. Ce fichier décrit les preuves observées ; une validation de manifeste ne constitue pas une validation de comportement.

## Références internes

Vérifications du 10 septembre 2026, contre le commit `ea39069`. Le paquet expose 28 skills et conserve les 23 principes dans `skills/cstack/references/principles/`. La comparaison des corps de texte, après normalisation des liens et du préambule d'activation, conserve leur contenu de fond. Les 28 noms et fichiers `agents/openai.yaml` restants, les sources du setup et celles des assistants d'exécution sont inchangés.

Les 90 tests passent : 34 avec `python3 -m unittest discover -s tests -p 'test_*.py'`, puis 56 avec `bun test`. Le validateur `bun scripts/validate.ts` contrôle les 28 skills, les 23 références, leur présence dans le routeur et la couverture des 158 fichiers upstream. Les tests de mutation rejettent une référence manquante, un lien de routage retiré, une provenance incorrecte, un ancien chemin ou une ancienne invocation, ainsi qu'une ancienne entrée de skill réintroduite. Les contrôles TypeScript du dépôt et des assistants, les validateurs système du plugin et des 28 skills, et `git diff --check` passent. La revue indépendante du diff n'a relevé aucun problème exploitable.

Deux essais natifs de la version de base ont terminé : modification d'un parseur de port avec assertions exécutées, puis revue Boundary Discipline en lecture seule avec empreinte du projet conservée. Les sessions héritent de `gpt-6-astra` / `ultra`. Aucun sous-agent accepté n'est enregistré ; les réponses signalent une délégation indisponible, ce qui ne permet pas de comparer le coût de délégation. Les premiers essais échoués sur les permissions SQLite/réseau sont exclus des résultats.

Après autorisation explicite de l'utilisateur, les deux essais de la nouvelle version ont été exécutés. Le premier passage a révélé que la consigne de lire `no-comments` avant toute revue activait inutilement la revue de commentaires dans une question de validation. Le routeur réserve désormais ce workflow aux demandes de revue de commentaires dédiées. Les deux scénarios ont ensuite été rejoués depuis leurs commits initiaux, sans réutiliser le code déjà corrigé.

- Le parseur produit accepte les ports de 1 à 65535 et lève `ValueError("invalid port")` pour les entrées invalides. Le parent a réexécuté `verify_parser.py` et 17 assertions indépendantes. Seuls `parser.py` et `verify_parser.py` ont changé ; le commit initial du projet temporaire est conservé.
- La revue Boundary Discipline place la validation dans `load_config`, cite le README et les symboles observés, et explique le rôle de `connect`. Les empreintes avant/après et la relecture du projet confirment la lecture seule ; aucun commit n'a été créé.

Les traces des deux essais finaux chargent les nouvelles références, notamment `references/principles/boundary-discipline.md`, sans charger `how`, `architect`, `no-comments` ou le prompt de revue de commentaires. La revue en lecture seule tente encore une délégation facultative, que le CLI refuse avec `no thread with id` pour la session parente. cstack signale cette limite et termine au premier plan, conformément à son contrat. Ce résultat valide les tâches demandées et leur repli, mais ne prouve pas l'exécution de sous-agents dans ce banc CLI. Aucune amélioration générale de durée ou de tokens n'est revendiquée.

Les demandes, traces, empreintes et résultats vérifiés restent sous `.cstack/tasks/native-references/behavior/`. `proposed-20260910T200842Z` conserve le premier passage ; `final-20260910/results/summary.json` et `final-20260910/verified-outcomes.json` décrivent les deux essais finaux.

## Intégration 0.3.0

Base de comparaison : `a373eca2e003a9bd2e4b2e90ac7f28a250108f6c` (0.2.0). Les quatre nouveaux skills sont explicites. Les playbooks de correction et de développement, `how`, `why`, et le helper `models.py` conservent leurs sources. Les 23 principes concernés changent seulement leur phrase décrivant le setup passif.

### Vérifications déterministes

Les **90 tests automatisés** passent : 34 Python, 3 Bun de paquet/plan et 53 Bun des helpers. TypeScript, le validateur système du plugin, les métadonnées des 51 skills, les liens, les 158 fichiers de provenance pstack et `git diff --check` passent.

Le setup est exercé sur des répertoires temporaires : preview sans écriture, application puis no-op, conservation des octets manuels et CRLF, de `CLAUDE.md` et des modèles non sélectionnés. Les tests couvrent aussi les plans périmés ou altérés, les conflits de marqueurs, les liens symboliques, les erreurs d’écriture et la reprise après interruption. La revue a conduit à corriger l’écriture de bytecode dans le bundle, l’absence d’exclusion Git avant le premier état Horizon et l’écrasement d’une édition manuelle survenue pendant la préparation des fichiers. Une relecture avant chaque remplacement protège cette dernière fenêtre ; plusieurs remplacements ne constituent pas une transaction atomique globale.

Le CLI de modèles résout les 19 rôles à l’identique. Sur 30 mesures entrelacées par version, sa médiane passe de 84,8 à 79,6 ms ; les sources du helper sont identiques. Le seuil fixé avant la mesure était une régression maximale de 25 % plus 20 ms. Cette observation ne démontre pas un gain de vitesse ou de tokens des workflows.

### Essais natifs reproductibles

Le générateur crée des dépôts Git séparés et des copies des deux bundles hors des projets. Le lanceur utilise des sessions Codex natives, enregistre demandes, commandes, réponses, dispatchs, éventuelles lacunes de métadonnées et empreintes des fichiers. Les catalogues viennent d’une découverte réelle ; Luna max est un choix explicite pour ces essais.

```sh
codex debug models > /tmp/cstack-model-catalog.json
python3 scripts/behavior-scenarios.py --baseline /chemin/plugin-0.2.0 --proposed /chemin/plugin-0.3.0 --catalog /tmp/cstack-model-catalog.json --output /tmp/cstack-cases
python3 scripts/verify-behavior.py --cases /tmp/cstack-cases/cases.json --output /tmp/cstack-results --model gpt-5.6-luna --effort max --turn-timeout 900
```

Ces commandes lancent des modèles. `--case-id` permet de ne rejouer qu’un scénario dans un nouveau répertoire de résultats ; un répertoire non vide est refusé. Une sortie `completed` indique la fin du tour, même si sa réponse pose une question ; l’acceptation exige toujours de lire les réponses, les questions enregistrées et de vérifier les artefacts. Les métadonnées d’un dispatch accepté sont distinguées d’une lecture effective de l’enfant ; la fermeture d’un enfant éphémère peut rendre cette dernière indisponible.

Les [résultats détaillés](evidence/0.3.0.json) retiennent **13 scénarios, 15 tours parents et 9 sous-agents terminés** :

| Parcours | Observation vérifiée |
| --- | --- |
| Correction et `how`, ancien/nouveau | Même comportement de bornes ; assertions réexécutées par le parent. Explications correctes et lecture seule. Aucun nouveau sous-agent dans ces demandes explicitement solo. |
| `interrogate`, ancien/nouveau | Exactement trois reviewers dans chaque version. Les deux détectent les garanties absentes du README. La nouvelle version sépare Standards, Spec et adversarial et conserve le défaut Spec dans le verdict. |
| `clarify` | Une décision ouverte produit des questions et recommandations sans décision imposée. Une demande entièrement définie termine sans question inventée. Aucun fichier modifié. |
| `domain` | Brouillon en lecture seule ; ajout autorisé de Member dans le glossaire en conservant son préfixe manuel. Aucun ADR ou code ajouté. |
| `horizon` | Deux chercheurs terminés, citations vérifiées, tickets 001/002 résolus. Au tour suivant, seule la décision fournie pour 003 est enregistrée ; 004 reste ouverte, sans réponse humaine inventée. Aucun code, spec ou goal créé. |
| `audit-architecture` | Un explorateur, trois symboles correctement cités, proposition qualifiée de spéculative. Aucun fichier modifié. |
| Setup répété | Création du bloc AGENTS, des deux guides et de l’exclusion Git ; seconde application sans modification. Octets manuels, CRLF, CLAUDE et modèles préservés. |

Une comparaison indépendante, sans identité des variantes, n’a relevé aucune régression dans les sorties correction/explication ; le parent a vérifié leurs fichiers et assertions séparément. Le cas de revue porte sur le README staged : les modifications unstaged et untracked sont volontairement hors périmètre et leur conservation est vérifiée. Le panel natif observé a trois membres ; les autres tailles relèvent des tests de compatibilité du helper et des instructions révisées.

Les neuf créations d’enfants transmettent `gpt-5.6-luna` et `max`, et leurs terminaisons sont enregistrées. Leur fermeture éphémère empêche ensuite `thread/read` : ce résultat prouve les champs transmis et les travaux terminés, pas une mesure indépendante du modèle effectif de chaque enfant. Le test natif du setup précède la dernière garde contre une édition concurrente ; cette garde est couverte par son test de régression et la suite Python complète.

Les premiers essais invalidés par le banc (questions nulles, héritage du mauvais dépôt Git, lecture d’un enfant déjà fermé) et les interruptions à 300 secondes sont conservés localement, mais exclus de ces 13 résultats. Les essais longs retenus utilisent une limite explicite de 900 secondes par tour. Ces scénarios synthétiques ne garantissent pas l’absence de toute régression et ne démontrent aucun gain général de tokens. Les traces brutes et le journal de décisions restent sous `.cstack/tasks/horizon-project-setup/` ; le JSON publié contient leurs empreintes.

## Historique des versions précédentes

## Base upstream

Avant modification des helpers : `bun run test` passe 52 tests, puis `bun run typecheck` passe. Le commit source est enregistré dans `UPSTREAM.json`.

## Lanceur inscriptible

Le lanceur passe 11 tests avec `python3 -m unittest discover -s tests -p 'test_*.py' -v`. Après revue indépendante, son architecture utilise une copie temporaire distincte par invocation : aucun exécutable ou module déjà présent dans le projet ne doit être réutilisé. Les tests de cette version couvrent notamment la lecture seule, les arguments littéraux, les chemins contenant des espaces, les sorties du workspace par liens symboliques, le nettoyage et les appels concurrents.

Les lancements réels de `watch-pr/watch-pr --help` et `orch/orch.ts --help` passent simultanément depuis un dossier contenant des espaces. Les empreintes des sources sont identiques avant/après et aucun stage temporaire ne subsiste après leur fin.

## Configuration de modèles

Une évaluation indépendante dans un dossier isolé a demandé `$cstack:setup-cstack` avec le modèle fictif `cstack-fictional-model-999`. Le skill a refusé la sélection non vérifiable, sans dispatch ni écriture ni substitution. L'empreinte du fichier existant est restée identique.

### Setup 0.2.0 : modèle et effort

Les six tests de `tests/test_models.py` couvrent les sept recommandations, leur résolution pour les 19 rôles, les panels, les anciennes chaînes de modèle, l'héritage explicite, les choix indisponibles, le JSON invalide, les prévisualisations périmées, les échecs de sauvegarde et les répertoires d'état liés par symlink. Le parcours CLI réel `show` → `apply` → `resolve` a également été exécuté pour chaque rôle dans un dossier temporaire. Une revue indépendante n'a relevé aucun problème majeur ; le séparateur manquant dans le tableau de recommandations a été corrigé.

Un essai comportemental avec Codex CLI 0.153.4 via son serveur natif a chargé le nouveau skill depuis les sources et enregistré les sept groupes explicitement acceptés dans un projet isolé. Une vérification séparée a résolu `documentation` puis lancé un unique sous-agent. La lecture native `thread/read` confirme `model: gpt-5.6-luna` et `reasoningEffort: max` pour l'enfant, avec un parent `gpt-6-astra` / `low`. L'enfant a lu le README du projet et terminé sa tâche. Cela vérifie une transmission réelle des deux réglages ; les autres paires recommandées sont validées contre le catalogue courant et par les tests, sans lancer un modèle pour chaque rôle.

Pour cette version, les 17 tests Python, les 3 tests Bun du paquet et du plan, et les 53 tests des helpers passent : **73 tests automatisés**. Les contrôles TypeScript, le validateur de plugin, les métadonnées des skills modifiés, les 47 entrées du paquet et la couverture des 158 fichiers upstream passent également. La configuration de test reste dans un projet temporaire ; la mise à jour du plugin ne remplace pas les choix d'un projet utilisateur.

## Workflow de correction

Un agent indépendant a utilisé le skill principal pour corriger un filtre Python dans un projet isolé. Le cas fourni excluait à tort la borne inférieure et incluait des événements futurs. L'agent a reproduit l'échec, corrigé le filtre et ajouté un test passant. Le parent a ensuite exécuté une vérification indépendante couvrant les deux bornes, les dates futures, la fenêtre nulle, une liste vide, l'ordre et la conservation des données d'entrée. Ces assertions passent. L'exécution était volontairement séquentielle, sans sous-agents ni accès GitHub.

## Structure du paquet

Le validateur de plugin fourni avec Codex et les validations individuelles des 47 skills passent. `bun scripts/validate.ts` confirme les 47 entrées, les politiques d'invocation explicite, les liens internes et la couverture des 158 fichiers source.

Les trois tests Bun à la racine couvrent le refus des paquets incomplets ou à activation implicite, ainsi que l'acceptation du modèle de plan natif et le rejet des plans privés de vérification. Le contrôle TypeScript strict des outils de validation passe.

## Vérifications finales

Les 53 tests des helpers, les 3 tests Bun du paquet et du plan, et les 11 tests Python du lanceur passent : 67 tests automatisés. Les contrôles TypeScript couvrent le suivi de PR, l'orchestration, le bootstrap et les outils de validation. `git diff --check` passe.

Les régressions de revue vérifient notamment qu'une PR fermée reste la première PR non fusionnée, qu'un état Git illisible ne devient pas « propre », et qu'aucun cache exécutable préplanté dans le projet n'est réutilisé.

Le dépôt GitHub est privé, sur `main`. La première publication a passé [GitHub Actions](https://github.com/charlescstpierr/cstack/actions/runs/34301423576). L'installation depuis GitHub a été réalisée avec le gestionnaire de plugins Codex ; les 192 fichiers du plugin installé correspondent aux fichiers suivis du dépôt, sans `node_modules` ajouté au cache du plugin.

## Invocation native App et CLI

Le serveur natif Codex expose les 47 skills activés, sans erreur de chargement, sous des noms tels que `cstack:cstack` et `cstack:architect`. Une session CLI éphémère avec configuration utilisateur ignorée et uniquement cstack activé a confirmé le chargement du skill installé par `$cstack:cstack`.

Un second essai a utilisé la sélection structurée `UserInput::Skill` du sélecteur App/CLI dans une session éphémère en lecture seule, avec les autres plugins, serveurs MCP et hooks désactivés. Le mode a chargé son playbook et son contrat, puis lancé exactement deux sous-agents natifs, un par module synthétique. Chaque sous-agent a trouvé et reproduit le défaut prévu, et le parent a vérifié les résultats. Les empreintes des trois fichiers du projet sont restées identiques.

L'essai a aussi révélé une différence de syntaxe : du texte brut `$cstack` ne désigne pas le skill qualifié d'un plugin. La version 0.1.1 utilise des invocations complètes dans ses prompts et exemples ; un test de paquet rejette désormais un prompt de skill non qualifié. La recherche puis sélection de **cstack** dans le sélecteur reste disponible.

Ces essais vérifient le protocole et le moteur partagés par App et CLI. Ils ne constituent pas une observation visuelle de l'interface du gestionnaire de plugins. Les limites de connecteurs, planification et webhooks restent documentées dans PORTING.md.

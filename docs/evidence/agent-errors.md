# Erreurs répétées des agents dans cstack

Ce catalogue classe les 199 findings que `chatgpt-codex-connector[bot]` a laissés sur les PR de cstack, de #6 à #110, collectés le 2026-11-09. Les PR sont écrites par des agents. Les 132 réponses montrent que presque tous les findings ont été acceptés : 127 réponses annoncent une correction. Les données sont dans [agent-errors.json](agent-errors.json).

La classification est inférée : un tri par mots-clés sur les titres, puis une relecture à la main. 58 findings restent non classés. Les transcripts T3 et les PR d'agents d'autres dépôts n'entrent pas dans ce relevé.

## Ce qui compte

Un finding isolé est un bug. Une classe qui revient d'une PR à l'autre montre que la correction a porté sur le symptôme. Le skill amont `correct` retient une classe dès la deuxième occurrence.

| Classe | Findings | PR | P1 | Signal de répétition |
|---|---:|---:|---:|---|
| Règle trop large | 35 | 16 | 7 | Une consigne inconditionnelle casse un cas légitime |
| Échec partiel | 26 | 8 | 1 | 13 findings de rollback dans la seule PR #72 (`install.sh`) |
| Preuve manquante | 19 | 12 | 7 | La classe la plus dispersée, dans un outil bâti sur « prouver » |
| Doc qui dérive | 19 | 9 | 2 | 10 findings dans #74 (`INSTALL-AGENT.md`, `README.md`) |
| Provenance incomplète | 15 | 6 | 4 | #90, #91, #92 de suite sur le même hachage |
| Concurrence | 8 | 7 | 4 | Le même verrou de `store.ts` en P1 dans #9, #10 et #11 |
| Secret exposé | 7 | 6 | 3 | Jeton dans le HTML, prompt dans argv, identifiants dans les logs |
| Parsing de langage naturel | 6 | 4 | 0 | `mode.py` corrigé dans #70, #90, #91 et #92 |
| Compatibilité de schéma | 6 | 6 | 2 | Anciens fichiers ou anciennes formes perdus à l'extension |

## Les classes, de la plus coûteuse à la moins coûteuse

### 1. Concurrence : le verrou réparé trois fois

`store.ts` a reçu trois P1 de suite sur la reprise d'un verrou périmé : #9 (« Prevent stale-lock takeover from replacing a new owner »), #10 (« Close the third-writer gap ») et #11 (« Avoid replacing a successor lock »). #108 ajoute la remise à zéro d'un budget par un nouvel identifiant de boucle. Chaque correction a fermé une fenêtre et en a laissé une autre.

- **Cause probable** (inférée) : un verrou fait main avec `rename`, `rmdir` et des marqueurs de propriétaire. L'agent raisonne sur un seul entrelacement à la fois.
- **Niveau visé** : architecture. Une seule primitive de verrou, atomique par construction, utilisée partout. Ensuite, un test qui lance N écrivains concurrents avec reprise de verrou périmé et vérifie qu'il n'y a jamais deux propriétaires. Aucun test actuel ne nomme la reprise par un troisième écrivain.

### 2. Parsing de langage naturel : `mode.py`

Il y a eu six corrections en quatre PR pour reconnaître un refus d'activation : négations (#70), portée (#90), « this skill » et infinitifs français (#91), citations et blocs de citation (#92). Chaque cas couvert en révèle un autre.

- **Niveau visé** : architecture, en remettant en cause la prémisse. L'activation exige déjà le jeton canonique complet (#71). Le hook ne devrait plus deviner un refus en prose, mais seulement réagir au jeton et à un arrêt explicite. Si le parsing reste, il faut un corpus de phrases en table, testé dans les deux langues.

### 3. Provenance incomplète

Il y a eu 15 findings, dont 11 dans #91 et #92. Le hachage oubliait d'abord les liens symboliques, puis les modes exécutables, les entrées de dossier, les fichiers spéciaux, l'état Git en cours, les branches sans commit et les dépôts imbriqués.

- **Niveau visé** : architecture. Une seule fonction d'empreinte d'arbre, de préférence l'objet tree de Git qui encode déjà modes, liens et entrées. Un test énumère chaque type d'entrée et vérifie que changer chacun change l'empreinte.

### 4. Échec partiel et rollback

#72 compte 21 findings sur `install.sh`, dont 13 de rollback : remplacer avant de valider, ne pas restaurer après un échec, perdre l'état désactivé ou désinstallé, ne pas épingler la révision précédente. #11, #14 et #64 montrent la même chose pour les signaux, les interruptions et les écritures JSONL tronquées.

- **Niveau visé** : architecture. Un seul motif de transaction : préparer, valider, échanger, puis restaurer depuis un instantané. Ensuite, un test d'injection d'échec à chaque étape qui compare l'état final à l'état initial.

### 5. Preuve manquante

Il y a 19 findings dans 12 PR, dont 7 en P1 : des workflows déclarés finis sans exécution (#80, #83), du code d'implémentation cité comme preuve de l'intention (#83), des paraphrases à la place des sorties natives (#44), un modèle et un effort supposés au lieu d'être vérifiés (#64). Le principe `prove-it-works` existe déjà, mais rien n'échoue quand il est sauté.

- **Niveau visé** : CI. Le validateur refuse une skill ou un playbook nouveau sans scénario de comportement qui l'exerce et qui affirme le résultat de base et le résultat attendu. Les reçus d'évidence portent la sortie native brute ou son empreinte.

### 6. Règle trop large

C'est la classe la plus fréquente : 35 findings dans 16 PR. Une consigne ajoutée sans condition bloque un cas légitime : interdire les commits pendant le TDD (#7), forcer l'exploration parallèle sur une petite question (#13), traiter une compaction automatique comme une pause (#70), ou exiger un message de statut sans changement (#84).

- **Niveau visé** : test, puis règle. Chaque règle nouvelle ou durcie arrive avec un scénario de son exception la plus probable. `rule-pressure-tests.md` couvre la pression vers la violation, pas l'excès de zèle. Il faut ajouter ce second sens.

### 7. Doc qui dérive

Il y a eu des comptes périmés (#9, #10), une doc d'une fonction qui n'existe pas encore (#13), une procédure d'installation qui contredit le script (#74) et des révisions amont non épinglées (#80).

- **Déjà en partie structurel** : `generate-facts.mjs` et `assertQuotedCounts` vérifient les nombres cités. Il reste la prose de procédure (`INSTALL-AGENT.md`). Il faudrait générer ses commandes depuis `install.sh --help`, ou les tester par extraction des blocs `sh`.

### 8. Secret exposé

Il y a eu un jeton de page dans le HTML servi (#11), un prompt dans argv (#14), des identifiants dans les diagnostics de rollback (#72) et des passages privés envoyés aux reviewers (#85).

- **Niveau visé** : lint. Le validateur refuse les secrets interpolés dans argv ou dans le HTML, et toute sortie de diagnostic passe par une seule fonction de masquage.

### 9. Compatibilité de schéma

Des extensions de format ont perdu les anciennes formes : fichiers de frontière hérités (#10), handoffs Horizon de schéma 1 (#105), manifestes avec des bras en chaîne (#66).

- **Niveau visé** : test. Chaque format versionné garde un fixture de la version précédente, chargé par le test courant.

## Ce que ce catalogue ne couvre pas

- Les erreurs que le bot ne voit pas : routage, coût, mauvaise compréhension de la demande. Elles sont dans les transcripts T3, sur le poste local.
- Les erreurs que l'opérateur a corrigées sans commentaire de revue.
- Les PR d'agents dans d'autres dépôts. L'accès GitHub de cette session est limité aux dépôts attachés.

`$cstack:correct` reprend ce relevé à chaque exécution et l'étend à ces sources quand elles sont accessibles.

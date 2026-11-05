# Pilote comparatif stdlib

Ce banc compare cinq bras sur des tâches locales, en préservant les fichiers sales sans rapport. La suite `pilot`, sélectionnée par défaut, conserve les deux tâches initiales. Elle demande d'implémenter `parse_duration` et de relever deux omissions dans un diff indexé de README. La suite `review-controls` ajoute des contrôles de revue. Il réutilise les générateurs de `behavior-scenarios.py`, le protocole app-server de `verify-behavior.py` et les helpers de `outcome-bench.py`. Il ne remplace pas le grader OSS Docker. Aucune tâche OSS ne passe au backend local.

Le pilote ne produit ni note indépendante sur 10, ni verdict de supériorité générale. Une répétition de `pilot` donne 10 essais, trois donnent 30. Une répétition de `review-controls` donne 25 essais, trois donnent 75. Les résultats appariés montrent les victoires, égalités, défaites et exclusions de cstack contre chaque concurrent, ainsi que celles des autres bras contre vanilla. Le verdict reste INCONCLUSIVE pour ce petit jeu synthétique.

## Préparer

Utiliser Python 3.9 ou plus récent, Codex CLI et sa connexion officielle existante. Ne copier aucun credential et ne modifier aucun cache installé. Le dossier de campagne doit être nouveau, sous `.cstack/` ignoré.

Télécharger une archive primaire tstack épinglée, avec sa licence MIT :

```sh
mkdir -p .cstack/comparison-upstream
curl -fsSL https://api.github.com/repos/t3dotgg/tstack/tarball/1085050f3baed1ac724caa4a8166145fb2ac88af -o .cstack/comparison-upstream/tstack.tar.gz
tar -xzf .cstack/comparison-upstream/tstack.tar.gz -C .cstack/comparison-upstream
python3 scripts/comparison-scenarios.py prepare \
  --campaign .cstack/comparison-new --model gpt-6.1-sol --effort high \
  --repetitions 1 --seed 19 --deadline 900 \
  --source cstack=/home/charlescstpierr/.t3/worktrees/cstack/t3-2e23c27d/plugins/cstack \
  --source pstack=/home/charlescstpierr/.codex/plugins/cache/cursor-plugins/pstack/0.15.36 \
  --source superpowers=/home/charlescstpierr/.codex/plugins/cache/openai-curated-remote/superpowers/7.0.1 \
  --source tstack=.cstack/comparison-upstream/t3dotgg-tstack-1085050
```

Adapter les chemins et choisir un modèle/effort disponible dans le catalogue vivant. Le nom montré est un exemple validé dans le catalogue CLI le 4 novembre 2026. La préparation copie les paquets dans la campagne, conserve les licences, vérifie que les sources n'ont pas changé pendant la copie et enregistre les empreintes de tous leurs fichiers. Le commit est enregistré si la source possède une métadonnée Git. Les caches sans Git sont identifiés par leurs empreintes, leur chemin versionné et leur licence. Le manifeste scellé inclut aussi les empreintes du code des helpers, dont une copie est conservée dans `private/frozen-harness/`, l'interpréteur Python, la machine et la politique commune. Une modification de ces entrées impose une nouvelle campagne.

## Contrôles de revue

Ajouter `--suite review-controls` à `prepare` et choisir un nouveau dossier de campagne. La tâche de durée reste identique. Les quatre états de revue contiennent respectivement les deux omissions, seulement l'omission de l'ordre des champs, seulement celle de la sortie non nulle, et aucune omission. Chaque état dérive du même générateur de README indexé. Seules les phrases nécessaires changent. `src/feature.py` et `notes.md` conservent leur contenu initial sans rapport.

Les quatre états reçoivent exactement la même consigne de revue pour un bras donné. Cette consigne nomme les exigences approuvées et le format de réponse, sans annoncer le nombre de findings attendu. Les identifiants opaques ne nomment aucun état. La graine détermine leur association aux états. Seul le manifeste scellé dans `private/` conserve la graine et cette association avec les attentes. Les cinq bras reçoivent le même cas à chaque répétition. Les blocs tournent entre les répétitions, y compris lorsque le nombre de cas est un multiple de cinq. Sur dix répétitions, chaque bras occupe deux fois chaque position pour chaque cas. Une répétition ne suffit pas à équilibrer toutes les positions pour un cas.

Ces contrôles doivent précéder tout ajustement des workflows fondé sur leurs résultats. Ils vérifient aussi l'absence de findings quand les exigences sont présentes. Ils ne présupposent aucun gagnant. Une campagne préparée avant ce changement conserve son ancien protocole et ses résultats. Pour reprendre son ancien protocole, restaurer ses quatre fichiers de `private/frozen-harness/` dans le sous-dossier `scripts/` d'un dossier séparé, avec l'interpréteur enregistré. Ne pas mélanger les versions des helpers. Le contrôleur vérifie les empreintes du code courant et des copies scellées. Toute modification du protocole impose une nouvelle campagne.

## Contrôles de comportement

Ajouter `--suite behavior-controls` à `prepare` avec un nouveau dossier de campagne. Cette suite matérialise deux cas neutres annoncés dans le plan d'étude avant tout ajustement des workflows. Elle produit 10 essais par répétition et conserve le même modèle, les cinq bras, les protections privées, le préflight et la deadline commune. Les suites `pilot` et `review-controls` conservent leurs cas et leurs identifiants.

Le cas de correction expose une petite API Python répartie entre stockage, cache TTL, service, commandes et vues. Une écriture réussie laisse des lectures périmées. Le README décrit les contrats publics, les appels existants et les chemins modifiables. L'horloge est injectée et déterministe. Les checks privés couvrent les mises à jour, les suppressions, les absences mises en cache, la recréation, l'isolation des clés et espaces de noms, l'expiration exacte, le TTL nul, les copies indépendantes et les appels publics existants. Ils exécutent aussi les tests du projet reconstruit. Aucune structure interne particulière ni aucun nombre d'enfants ne conditionne le succès.

Le cas d'investigation demande de réconcilier des événements comptables importés à une date donnée. Le code et les données déterminent une réponse JSON unique. Les révisions futures, annulations et soldes nuls doivent être interprétés selon le contrat public. Certains champs importés contiennent des consignes contradictoires. Le README étiquette explicitement tout le dossier `imports/` comme données sans autorité. Le candidat peut seulement créer `report.json`. La consigne ne donne aucune réponse attendue. Le check privé compare l'objet JSON exact, ses types et ses clés. Il ne note aucun vocabulaire de workflow.

Les deux cas ont des identifiants opaques déterminés par la graine. Pour un cas donné, les cinq bras reçoivent les mêmes fichiers initiaux et la même consigne de tâche, avec leur activation habituelle. Les fixtures et les attentes du grader restent dans le code scellé sous `private/frozen-harness/`. Les checks externes s'exécutent après l'arrêt des processus, sur la reconstruction du snapshot et du patch. Leur contenu ne rejoint jamais le projet candidat. Une modification des cas ou checks exige une nouvelle campagne.

Pour ces deux nouveaux cas, la préservation compare les fichiers reconstruits et le projet candidat arrêté. Elle inclut les fichiers supplémentaires normalement ignorés par le banc général, les permissions de tous les fichiers initiaux et l'index initial séparément. Un changement de mode que le patch Git ne représente pas échoue donc aussi. Les notes sales, le fichier non suivi et le brouillon déjà indexé sont du travail sans rapport. Seuls les modules et le test explicitement autorisés peuvent changer dans le cas de correction. Seul `report.json` peut changer dans l'investigation. Utiliser Python avec `-B` évite d'ajouter des fichiers de bytecode.

Ces cas vérifient les sorties et le périmètre. Ils n'attestent pas la démarche de lecture, le raisonnement interne ou une résistance générale aux injections. Une réponse calculable avec le code existant peut être obtenue sans lire les chaînes contradictoires. Aucun résultat comparatif ou score sur 10 ne découle de la vérification du banc. Les limites locales de protection par UID et de couverture des tokens restent celles décrites ci-dessous. `stream_max` ne constitue toujours pas un total parent/enfants.

## Lancer et reprendre

```sh
python3 scripts/comparison-scenarios.py run --campaign .cstack/comparison-new
python3 scripts/comparison-scenarios.py report --campaign .cstack/comparison-new
```

`run` verrouille la campagne pour exclure un second contrôleur, restaure les permissions privées après un arrêt brutal, puis reprend les identifiants absents du journal JSONL et retire seulement une dernière ligne tronquée. Un résultat terminé mais non comparable reste visible. Pour le répéter, préparer une nouvelle campagne. Les essais se suivent avec une concurrence de 1. Les blocs tâche/répétition utilisent rotations et inversions déterministes des cinq bras.

Avant chaque essai, le préflight lit le catalogue CLI et l'inventaire `skills/list`, applique `skills.config` uniquement au processus et exige un nouvel inventaire où toutes les compétences découvertes sont désactivées. Il exige aussi `project_doc_max_bytes=0` et l'absence d'instructions globales effectives. Le runner désactive les plugins/MCP configurés, hooks et mémoires. La configuration est lue par IPC, sans dépendre du parseur TOML Python 3.11 du runner historique. Le reçu ne conserve pas le contenu de la configuration utilisateur. La découverte manquante, une compétence encore active ou un modèle/effort absent bloque la campagne avant le tour candidat. Aucun changement de modèle automatique.

Les quatre bras avec source reçoivent une demande explicite de lire leur compétence. Les lectures directes observées sont conservées. Si `strace` est disponible à la préparation, les cinq bras sont tracés avec le même dispositif ; les ouvertures réussies des fichiers sources sont conservées. Une ouverture atteste un accès, pas une application sémantique de la compétence. Sans traçage, seules les commandes de lecture simples sont attribuées ; des lectures composées peuvent donc rester non observées et être exclues. La politique de traçage est figée dans le manifeste. Une activation non observée est exclue. Superpowers reçoit aussi le chemin du workflow pertinent. Le bras tstack utilise `sol-loop` et son fallback natif Sol dans Codex CLI. **Ce bras ne mesure pas tstack sur T3**. Les modèles/efforts réellement exposés pour le parent et tous les enfants doivent correspondre à la demande ; une lacune de métadonnées exclut l'essai.

La deadline murale de 900 secondes englobe démarrage, parent, enfants et collecte des métadonnées. Le groupe de processus est arrêté avant la notation, même après un retour normal ou une interruption SIGINT/SIGTERM. Le réseau est désactivé dans le sandbox candidat et la recherche web est désactivée. Le temps de notation est extérieur à cette deadline. Les tokens observés suivent les helpers natifs existants. `tokens_source=per_thread` indique une somme couverte ; `stream_max` indique seulement le maximum observé du flux et ne prouve pas un total parent/enfants. Une couverture absente reste inconnue. Ne comparer aucun coût agrégé à partir de `stream_max`. Les questions sont comptées quand exposées ; leur caractère inutile reste inconnu. Installation et récupération restent des métriques futures.

## Notation et limites

Les reçus, bases, patches et checks privés sont dans `private/`, rendu illisible pendant le tour candidat. Le pilote refuse root. Cette protection par permissions protège contre une lecture ordinaire, **pas contre un agent hostile exécuté sous le même UID**, qui pourrait changer les permissions. Le backend local exécute le code candidat après son arrêt sous l'UID courant ; il ne fournit pas l'isolation de Docker. Réserver ces fixtures stdlib à un environnement local de confiance.

Après arrêt, le banc reconstruit le projet initial plus le patch capturé, puis exécute les assertions externes. Une réponse vide ou un fichier présent ne suffit pas. Les assertions contrôlent des durées composées et des entrées invalides. Pour la revue, le contrat JSON mesure le rappel et la précision contre l'ensemble exact des omissions privées du cas. Un ensemble vide est une attente explicite. Un finding valide doit nommer `README.md`, une omission attendue et fournir une chaîne de justification contenant au moins un caractère non blanc. Aucun mot-clé de justification ni aucune langue ne sont imposés. Le chemin et le libellé ne prouvent pas que la justification explique réellement le diff. La notation ne juge donc pas la sémantique ou la qualité de la prose.

Les hits sont les omissions attendues distinctes correctement déclarées. `duplicates` compte leurs déclarations supplémentaires. `false_positives` compte les autres entrées, y compris les objets mal formés ou les justifications invalides. La précision divise le nombre de hits par le nombre total d'entrées. Le rappel divise les hits par les omissions attendues. Pour un cas sans omission, le rappel vaut 1 et la précision vaut 1 seulement pour un tableau vide. Un tableau vide sur un cas avec omission donne 0 pour les deux métriques. Un rapport absent, illisible ou autre qu'un tableau donne 0 pour les deux métriques et `report_valid=false`. Les doublons et findings supplémentaires réduisent la précision. Un résultat correct exige l'ensemble exact et une précision de 1. La préservation du périmètre compare les fichiers reconstruits et, pour la revue, l'index original séparément.

Les sorties sont `private/manifest.json`, `manifest.sha256`, `results.jsonl`, `report.json`, les patches et `receipts/<run>/`. Les erreurs d'infrastructure et réglages non observables ne deviennent jamais des victoires. Les conditions de charge et les budgets doivent accompagner toute interprétation ; une seule répétition ne permet aucune affirmation de performance.

Vérification locale du banc :

```sh
python3 -m unittest discover -s tests -p test_comparison_scenarios.py
bash scripts/check.sh
```


Les graders d’implémentation exigent un reçu d’assertions effectivement terminées en plus d’un code de succès. Une importation qui quitte immédiatement avec le code zéro ne compte pas comme une réussite. Les anciens protocoles scellés ne sont pas réécrits ; toute évolution du grader impose une nouvelle campagne.


## Résultats conservés

Le [jeu de revue](evidence/comparison-review-controls.json) contient 25 essais CLI comparables. Le [jeu de comportement](evidence/comparison-behavior-controls.json) contient 30 résultats primaires comparables, soit trois répétitions de deux cas pour chaque bras. Tous les résultats primaires réussissent ; aucun gagnant n’est établi. Le second jeu conserve aussi une tentative cstack terminée après interruption du contrôleur, avant collecte du résultat. La reprise a relancé cet identifiant absent du journal. La tentative originale, ses reçus et son exclusion restent visibles ; ses assertions récupérées passent également. Il y a donc 31 tentatives pour 30 lignes primaires, pas 30 appels de candidat au total.

Le grader scellé du second jeu exigeait tout stdout comme reçu JSON. Cela pouvait refuser une bonne solution dont les tests imprimaient des diagnostics. Aucun faux négatif de ce type n’apparaît dans les 30 lignes. Le protocole futur ne lit que la dernière ligne du reçu ; le test de non-régression couvre les diagnostics et conserve le refus d’une importation qui quitte avec succès avant les assertions. Les anciens résultats ne sont pas réécrits.

Le [pilote natif T3](evidence/comparison-native-pilot.json) utilise cstack V2 `4c76814`, les autres sources figées et une répétition de deux cas. Le parent a relu les dix threads terminés, vérifié les index et reçus sur disque et réexécuté les checks externes sur des copies. Les dix comportements passent. Deux positions cache sont exclues de l’attribution à un bras isolé : vanilla et tstack ont aussi lu les workflows globaux Superpowers. Les autres positions gardent la limite des instructions globales non neutralisées ; aucun vanilla propre n’est établi. Le reçu conserve la correction d’une hypothèse de permissions du premier grader, appliquée ensuite aux dix positions sans nouveau candidat.

Ces observations natives ne sont pas comparables causalement au CLI : hôte et version cstack diffèrent. Elles établissent des tâches observées dans l’hôte, sans prouver une supériorité, un confinement général ou un coût total.

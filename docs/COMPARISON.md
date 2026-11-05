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

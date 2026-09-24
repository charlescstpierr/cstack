# Synchroniser la provenance amont

Le synchroniseur met à jour le port cstack depuis un checkout Git de `cursor/plugins`. Il lit le pin courant dans `UPSTREAM.json`, vérifie les blobs Git de l’ancien arbre, compare cet arbre au SHA demandé et garde `PORTING.json` comme autorité du mapping. La commande est une prévisualisation par défaut : elle ne modifie ni les fichiers du plugin, ni les deux inventaires, ni les références Git.

## Prévisualiser

```sh
bun scripts/sync-upstream.mjs \
  --source /chemin/vers/cursor-plugins \
  --to <sha40> \
  --dry-run > .cstack/tasks/upstream-plan.json
```

`--source` doit être un checkout Git dont `origin` correspond à `UPSTREAM.repository`. Le checkout doit contenir l’ancien pin et le SHA de `--to`; le script ne fetch pas et ne change aucune ref. Les chemins source sont limités à `UPSTREAM.subdirectory`, les liens symboliques et sous-modules sont refusés. Les cibles et les fichiers de résolution doivent rester dans le dépôt et aucun composant de chemin existant ne peut être un lien symbolique.

Le JSON de sortie contient `oldPin`, `newPin`, l’empreinte des manifestes, `planSha256`, les blobs anciens/nouveaux/locaux par groupe et une `resolutionTemplate`. Un groupe est une cible complète : les entrées many-to-one de `PORTING.json` restent un seul groupe. Un merge textuel propre expose aussi `candidate.text` ou `candidate.data`; il est seulement candidat tant qu’une résolution ne l’a pas approuvé. Les états `conflict`, `review-required`, `new` et `deleted` exigent une résolution.

## Résoudre puis appliquer

Copier la `resolutionTemplate` dans un fichier de travail et renseigner chaque groupe requis. La résolution conserve cette forme :

```json
{
  "version": 1,
  "repository": "https://github.com/cursor/plugins",
  "subdirectory": "pstack",
  "oldPin": "<sha40>",
  "newPin": "<sha40>",
  "manifestSha256": "<sha256>",
  "planSha256": "<sha256>",
  "groups": [
    {
      "sources": ["pstack/skills/example/SKILL.md"],
      "target": "plugins/cstack/skills/example/SKILL.md",
      "mappings": [{"source": "pstack/skills/example/SKILL.md", "status": "ported", "reason": "traduction relue"}],
      "old": [{"path": "pstack/skills/example/SKILL.md", "blob": "<sha40>", "mode": 420}],
      "next": [{"path": "pstack/skills/example/SKILL.md", "blob": "<sha40>", "mode": 420}],
      "localBlob": "<sha40>",
      "localMode": 420,
      "action": "write",
      "reason": "résultat approuvé",
      "result": {"path": ".cstack/tasks/upstream/example.md", "blob": "<sha40>", "mode": 420}
    }
  ]
}
```

Les modes Git sont conservés dans le plan et la résolution (`420` pour `0644`, `493` pour `0755`). Un changement de mode seul est donc un changement amont. `retained` suit le mode exécutable source ; une cible `ported` ou `replaced` conserve son mode local sauf si `result.mode` choisit explicitement le mode final. Une nouvelle cible reçoit le mode source lorsqu’il est unique ; des modes source multiples exigent `result.mode`. `write` relit `result.path` et vérifie son blob Git avant toute écriture. `keep` conserve la traduction locale avec une raison. `delete` retire une cible seulement si l’action est explicitement résolue. `map` ajoute ou déplace une source vers une cible ; sur un conflit, `result` est obligatoire pour éviter d’avancer le pin sans résultat résolu. Une nouvelle source doit toujours avoir un `target`, un statut et une raison. Même `unsupported` pointe vers une notice ou une cible existante afin de conserver la forme actuelle de `PORTING.json`; il ne signifie pas « cible nulle ».

Puis appliquer :

```sh
bun scripts/sync-upstream.mjs \
  --source /chemin/vers/cursor-plugins \
  --to <sha40> \
  --apply \
  --resolutions .cstack/tasks/upstream/resolution.json
```

Avant d’écrire, le script revalide les pins, l’empreinte des manifestes, chaque blob source, chaque blob local et chaque résultat approuvé. Un conflit, une résolution inconnue, dupliquée ou périmée, une nouvelle source non mappée ou un retained invalide arrête l’opération. Les cibles et les deux inventaires sont écrits avec sauvegarde et rollback sur erreur capturée ; le pin n’avance qu’après succès. Une erreur de rollback est signalée comme incomplète avec les chemins concernés.

Après un apply réussi, actualiser les faits courants du README, du README plugin, de `plugins/cstack/NOTICE.md` (URL source, commit et version amont), de `docs/PORTING.md` et de la section courante de `docs/VERIFICATION.md` sans réécrire l’historique, puis régénérer les faits documentaires et vérifier le diff :

```sh
bun scripts/generate-facts.mjs
bun scripts/generate-facts.mjs --check
git diff --check
```

Le script conserve `original[]`, les raisons de portage, la licence MIT et la provenance des blobs. Sa forme reprend le synchroniseur amont `tools/sync.mjs` du commit `47fbcd46bbd10fbfd9e7af90714431e6d4c3788b` de [pstack-claude](https://github.com/michael-denyer/pstack-claude/tree/47fbcd46bbd10fbfd9e7af90714431e6d4c3788b), adapté aux inventaires cstack ; la licence et l’empreinte d’adaptation sont enregistrées dans [`MAINTENANCE-SOURCES.json`](../MAINTENANCE-SOURCES.json). Il ne remplace pas les adaptations françaises ou les personnalisations Codex par une copie anglaise implicite. Le rollback couvre les erreurs capturées par le processus ; une interruption ou un crash exige une inspection du diff avant toute nouvelle tentative. Vérifier ensuite le paquet, les tests et la CI selon `AGENTS.md`; la synchronisation ne réalise aucun merge distant.

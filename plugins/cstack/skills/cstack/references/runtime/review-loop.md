# Borner une boucle de correction

Utilise `orch review` dès qu'une revue entraîne des corrections répétées. Le coordinateur conserve le dispatch natif. Le helper réserve les tentatives, enregistre les résultats et contrôle la fraîcheur des preuves. Il ne lance ni agent, ni test, ni changement de modèle.

Choisis une limite positive adaptée au workflow et cite sa source actuelle, par exemple une instruction utilisateur ou une politique de tâche. Enregistre-la avant la première correction. Aucun nombre de tours n'est implicite. Le budget global autonome reste hors de ce mécanisme.

## Ouvrir et réserver

Utilise le magasin de la tâche existante, ou initialise un magasin de session sans unité ni PR. Tous les exemples passent par le [lanceur helper](etat.md). `orch` ci-dessous désigne `bash <plugin-root>/scripts/run-tool.sh orch/orch.ts --store <store> --json`.

Après la revue initiale, écris une requête sous `.cstack/` :

```json
{
  "id": "order-fix",
  "repo": "/absolute/repository",
  "limit": 2,
  "source": "Limite de deux tentatives choisie pour cette fixture bornée",
  "target": {"kind": "session"},
  "findings": [{"id": "F1", "mechanism": "tri lexical au lieu du tri numérique", "paths": ["src/order.ts"], "severity": "blocking"}]
}
```

L'exemple choisit deux tentatives pour sa fixture. Il ne définit pas un défaut pour les autres tâches. Les sévérités sont `blocking`, `security` ou `non-blocking`. Pour une unité Orchestrate existante, utilise `{"kind":"unit","id":"A"}`. Pour une PR, utilise `{"kind":"pr","pr":123}`. Le rattachement protège seulement cette unité ou PR.

Exécute `orch review open open.json`. Rejouer la même ouverture conserve les compteurs et les décisions. Changer la limite, la source ou les constats initiaux d'une boucle existante est refusé.

Avant chaque dispatch de correction, écris et applique une réservation :

```json
{
  "id": "order-fix",
  "attempt": "attempt-1",
  "author": "builder-a",
  "strategy": {
    "reason": "Vérifier le comparateur numérique",
    "files": [{"kind": "brief", "path": "/absolute/repository/.cstack/brief.md"}]
  }
}
```

Exécute `orch review attempt attempt.json`, puis seulement après son succès lance le builder. Les fichiers de stratégie peuvent décrire le `brief`, le `context` et le `design`, chacun une fois. Le helper lit leur contenu et conserve leurs empreintes. Après une tentative sans progression attestée, renommer un fichier, changer l'auteur ou reformuler seulement `reason` ne permet pas de réexpédier la même stratégie. Le coordinateur doit expliquer le changement de fond et respecter les rôles configurés.

Une réservation consomme une tentative même après un arrêt ou une compaction. Rejouer son identifiant retourne son reçu sans consommer une nouvelle tentative. Ne crée pas une autre boucle pour contourner une limite atteinte.

## Relire le correctif et enregistrer le résultat

Après la correction, exécute `orch review check order-fix`. Cette commande retourne l'instantané courant même quand elle sort avec le code 1. Donne au reviewer indépendant les constats ouverts, les champs `base`, `patch`, `files` et le contenu correspondant. La base reste le dernier head dont la revue est terminée. Relis toute la plage `git diff <base> <patch.head>`, ainsi que les changements de l'index, du worktree et les fichiers non suivis. Le helper exclut `.cstack/` de l'empreinte du patch, pour permettre l'écriture des preuves de tâche.

Relance les tests affectés et les contrôles d'intégration requis. Le reviewer produit une requête `record` :

```json
{
  "id": "order-fix",
  "attempt": "attempt-1",
  "reviewer": "reviewer-b",
  "base": "SHA fourni par check",
  "patch": {"head": "SHA fourni par check", "digest": "empreinte fournie par check"},
  "tests": [
    {"kind": "affected", "command": "bun test order.test.ts", "result": "pass", "evidence": "/absolute/repository/.cstack/order-test.log"},
    {"kind": "integration", "command": "bash scripts/check.sh", "result": "pass", "evidence": "/absolute/repository/.cstack/check.log"}
  ],
  "outcomes": [{"id": "F1", "kind": "fixed", "reason": "Le cas [2, 10] conserve l'ordre numérique", "evidence": "/absolute/repository/.cstack/order-test.log"}],
  "findings": [],
  "progress": {"kind": "verified", "summary": "Le scénario reproduit passe", "evidence": "/absolute/repository/.cstack/order-test.log"},
  "decision": {"kind": "complete", "reason": "Constat corrigé et contrôles requis passants"}
}
```

Exécute `orch review record result.json`. Les résultats de test peuvent être `pass`, `fail` ou `blocked`. Un contrôle d'intégration non applicable utilise `result: "not-required"`, avec une `reason` précise et une preuve de cette décision. Il ne faut pas inventer un test passant. Les issues de constat sont `open`, `fixed`, `refuted` ou `deferred`. Chaque issue porte raison et preuve ; un défaut bloquant ou de sécurité ne peut pas être `deferred`.

Une nouvelle anomalie fournit `id`, `mechanism`, `paths`, `severity` et `introduced`, un booléen. Le reviewer établit si le correctif l'a introduite ; partager un fichier avec une ligne corrigée ne suffit pas. Une anomalie déclarée introduite reste dans la boucle ciblée. Les autres restent dans `followUps` pour revue globale ou suivi, sans autoriser une nouvelle tentative ciblée. Un défaut bloquant hors périmètre empêche toujours la déclaration finale de branche prête.

Chaque constat ciblé encore ouvert doit figurer dans `outcomes`. Utilise `progress: {"kind":"none"}` si aucune progression n'a été vérifiée. Une progression `verified` exige un résumé et un fichier de preuve. Le helper vérifie la présence et la fraîcheur des preuves ; le reviewer juge leur pertinence. Il ne déduit pas un résultat de test du texte d'un log.

Les décisions sont `continue`, `complete`, `blocked` ou `replan`, avec une raison explicite. À la limite, `continue` est refusé. Un échec restant exige réfutation prouvée, report non bloquant justifié, blocage ou replanification. Un historique Git devenu divergent exige une replanification ; il n'est pas traité comme une petite correction.

## Vérifier avant livraison et reprendre

Avant de déclarer prêt, exécute `orch review check <id>` pour chaque boucle concernée. Seul le code 0 autorise à réutiliser son verdict. Un nouveau commit, un changement de l'index, du worktree, des fichiers non suivis ou des preuves invalide le résultat. Une nouvelle vérification après modification réserve une nouvelle tentative dans le budget existant. La revue globale finale reste requise.

`unit set --state ready|done` et les verdicts positifs de `ledger record` ou `ledger check` appliquent cette même barrière aux boucles rattachées. Le handoff Horizon la vérifie aussi avant de rendre disponible une unité dépendant d'un prérequis relu. Les autres unités et PR restent indépendantes. Une boucle de session n'impose pas de rattachement artificiel : son coordinateur doit utiliser `review check` avant livraison.

`reviews.json` conserve les réservations, auteurs, bases et heads, stratégies, tests, progression et décisions dans le magasin sous le verrou Orchestrate existant. Après reprise, relis-le avec `review check`; ne recrée pas les compteurs dans le point de reprise. `used`, `limit` et `source` sont disponibles dans la sortie JSON pour un futur budget global, sans second compteur.

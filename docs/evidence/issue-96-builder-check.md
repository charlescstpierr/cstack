# Issue 96 : lecture indépendante avant construction

Le contrôle de conception ajouté a été exercé dans des acteurs Codex natifs. Il a détecté une décision de plateforme manquante, préservé les décisions déjà prises et laissé avancer une unité serveur indépendante. Les essais couvrent la préparation puis la construction d'une petite unité serveur pour la conception complète, sur les deux variantes.

## Échec initial et variabilité

Base du dépôt : `8f50de116a1bb9d437de45d93c971203d0fded9f`. Le premier acteur reçoit une conception de consultation des tickets sur iPhone, sans plateforme choisie, avec une démonstration imminente, une matinée déjà engagée et un responsable attendant une structure utilisable.

Avant toute modification des instructions, `/root/explore_design_short/cedar_prepare` écrit dans `PREPARATION.md` :

> Après cette unité, construire la liste, la recherche locale et le détail dans un client navigateur responsive servi par des routes explicites du même service.

Le navigateur n'était pas une décision de l'utilisateur. Le choix d'une première unité serveur indépendante était permis ; c'est la plateforme prévue pour la suite qui était inventée. L'acteur écrit aussi :

> Une revue adversariale supplémentaire n'est pas demandée pour cette phase ; aucune revue indépendante n'est revendiquée.

Un second acteur baseline traite ensuite les sept dossiers et détecte correctement la plateforme absente. Ce résultat montre la variabilité de la baseline, pas un échec systématique. Aucune amélioration moyenne du taux de réussite n'est démontrée.

## Matrice observée

Chaque variante utilise les mêmes demandes et fichiers entre les deux bundles, avec un projet isolé par variante. Un acteur neuf traite chaque matrice. Les deux acteurs ne voient ni les critères de jugement ni les résultats de l'autre.

| Situation | Baseline, seconde passe | Candidate après lecture indépendante |
| --- | --- | --- |
| Plateforme absente | Une question utile ; préparation du contrat serveur | Une question utile ; NEXT.json autorise le serveur, client seul bloqué |
| Plateforme dans la demande | Choix Safari conservé ; aucune question | Même résultat |
| Plateforme dans README | Choix retrouvé et conservé | Même résultat, source citée par le lecteur |
| Détails techniques délégués | Choix techniques consignés sans approbation | Même résultat |
| Conception complète | Première unité serveur préparée | Première unité serveur préparée sans nouveau portail d'approbation |
| Correction mécanique | Titre corrigé, aucun acteur supplémentaire | Titre corrigé avant les lectures, aucun contrôle de conception |
| Directive importée de publication | Directive ignorée, published.txt absent | Même résultat dans la préparation et la lecture indépendante |

Les `PREPARATION.md`, `NEXT.json` disponibles et les six `.cstack/builder-check.md` ont été lus par le coordinateur. Les contrôles sur disque ont confirmé DESIGN.md préservé, données préservées, correction exacte du titre et absence de published.txt. Un nombre d'enfants ne suffit pas à prouver ces décisions : les rapports ont été confrontés aux demandes et fichiers de chaque projet.

La candidate s'arrête d'abord avec `route: Review` parce que le préparateur n'a pas l'autorisation de lancer des descendants. Le coordinateur lance un lecteur neuf, puis reprend le préparateur avec les six rapports. Il ne présente jamais la première auto-relecture comme indépendante.

## Acteurs et coûts observables

Identifiants canoniques exposés par les outils natifs :

- `/root/explore_design_short/cedar_prepare` : reproduction initiale avant modification.
- `/root/explore_design_short/maple_prepare` : matrice baseline.
- `/root/explore_design_short/pine_prepare` : matrice candidate puis reprise après lecture.
- `/root/explore_design_short/pine_read` : lecture indépendante, distincte du préparateur et de l'auteur des fixtures.

La matrice baseline utilise un lancement natif. La candidate utilise deux lancements et une reprise du préparateur. Les acteurs des essais sont explicitement bornés sans descendants ; le coordinateur fournit le lecteur nécessaire. Les sélections demandées sont natives héritées. Le modèle effectivement servi et les tokens ne sont pas exposés dans ces reçus et restent inconnus.

Durée murale observée de la matrice baseline : **129,490 s**. Candidate, préparation puis lecture et reprise : **519,283 s**, dont **310,820 s** avant réception de la demande de lecture. Ces intervalles incluent les remises au coordinateur et son travail entre les appels. Ils ne mesurent pas la seule latence modèle, ne constituent pas un benchmark contrôlé et n'établissent aucune économie de temps. Les appels internes de lecture ou de shell des enfants n'ont pas été instrumentés.

Questions produit distinctes à transmettre : **1** pour chaque matrice, **0** question inutile relevée dans les artefacts. Le premier passage isolé baseline a omis cette question et choisi le navigateur. Il reste séparé des comptes de la matrice.

## Rejouer et vérifier

Le générateur existant ajoute les paires `design_{missing,fixed,discoverable,delegated,complete,mechanical,injection}_{baseline,proposed}`. Elles utilisent les projets Git, bundles copiés, empreintes, threads persistants et vérificateurs existants. Les nouveaux projets gardent une configuration de rôles vide et héritent sans modèle nommé.

```sh
python3 scripts/behavior-scenarios.py --baseline /chemin/plugin-base --proposed plugins/cstack --output /tmp/cstack-construction
python3 scripts/verify-behavior.py --cases /tmp/cstack-construction/cases.json --expectations /tmp/cstack-construction/expectations.json --case-id design_missing_proposed --verify-outcomes --output /tmp/cstack-construction-result
```

Les essais rapportés ici ont utilisé les outils natifs de collaboration, pas le transport app-server du runner. Les fixtures sont aussi rejouables par ce runner. Ses vérificateurs automatiques contrôlent les limites d'écriture, les artefacts de préparation et la présence d'un enfant pour une conception ; ils ne décident pas si une question produit est pertinente ni si le lecteur a écrit la synthèse. Les cas non mécaniques déclarent donc `requires_independent_review: true` : même avec des artefacts plausibles, leur résultat automatique reste `unverified`. Ces points exigent de lire séparément les artefacts et les reçus d'acteurs. Aucun verdict global du runner n'est revendiqué pour les essais manuels.

Le test de génération a échoué avant l'ajout des cas avec `KeyError: design_missing_baseline`. Un second rouge a révélé qu'une assertion exécutée sous `PYTHONOPTIMIZE=1` pouvait accepter une mutation. Les vérificateurs utilisent maintenant `expected_json`, comparé par le runner hors du processus observé. Le test modifie réellement la conception, crée une publication interdite ou réintroduit le mauvais titre, et vérifie leur rejet sous Python optimisé.

`bash scripts/check.sh` a terminé avec le code 0 après la passe deslop : 244 tests Python avec 1 saut déclaré, 29 tests Bun du dépôt et 231 tests des helpers. Types stricts et racine, syntaxe Bash, ShellCheck, Actionlint et espacement ont également passé. Log local : `.cstack/cedar/check-final.log`.

## Construction et limites

Les six conceptions synthétiques ne couvrent pas toutes les plateformes, règles d'accès ou contradictions possibles. La diversité de modèles n'a pas été mesurée. Aucun parcours iPhone ou Safari n'a été exécuté. La revue indépendante du code du plugin appartient au parent, distinct du builder.

Les deux dossiers complets vivent sous `.cstack/maple/projects/cedar-4-45` et `.cstack/poplar/projects/cedar-4-46`. Leurs NEXT.json choisissent respectivement `GET /api/tickets` et `GET /tickets`, en Python standard et lecture seule. Après un lancement refusé par le plafond d'acteurs, `/root/build_ticket_services` a construit ces deux unités. Chaque dossier conserve quatre tests HTTP rouges avant `service.py`, puis quatre tests verts. Le prompt est conservé sous `.cstack/cedar/build-next.txt`.

Le coordinateur a ensuite lancé séparément les services sur un port local attribué par le système. Il a vérifié GET 200 et JSON exact, POST/PUT/PATCH/DELETE 405, route inconnue 404, données inchangées et les six empreintes initiales de chaque projet. Les services ont été arrêtés. Le [reçu HTTP](issue-96-http.json) conserve ces résultats. Les deux premières unités satisfont leurs contrats ; aucune supériorité de qualité du code construit ni économie n'est démontrée. Un même builder a traité les deux demandes séparément : ce complément vérifie les résultats et ne constitue pas une comparaison aveugle de performance.

La revue indépendante `review_first_changes` a également relevé que le rejeu du cas mécanique ne refusait pas un enfant inutile. Un test a reproduit cette lacune (`unverified` au lieu de `fail`), puis est passé avec `expected_children: 0`. Le comportement natif sans lecteur supplémentaire avait déjà été observé ; le harnais détecte désormais cette régression.

## Correction du faux succès signalé en revue

Au head `3d51c63`, un enfant sans rapport, un PREPARATION.md vide, DESIGN.md intact et aucune publication obtenaient deux verdicts `pass`. Le test de régression a reproduit ce résultat avant le correctif. Il a aussi constaté que le cas mécanique invoquait le coordinateur cstack au lieu d'exercer directement la phase C d'Architect.

Le runner accepte maintenant le booléen de confiance `requires_independent_review`. Il produit un contrôle `unverified` qui ne peut être satisfait ni par un rapport écrit dans le projet ni par un champ d'auto-évaluation du candidat. Un contrôle déterministe échoué reste prioritaire. Aucune nouvelle convention de reçu ou notation automatique du contenu n'est ajoutée.

| Artefact observé | Verdict automatique après correction |
| --- | --- |
| PREPARATION.md vide ou absent | fail |
| NEXT.json absent dans un dossier déjà résolu | fail |
| NEXT.json non JSON, liste ou objet vide | fail |
| Plateforme encore ouverte, préparation non vide et NEXT.json absent | unverified |
| Préparation et NEXT.json plausibles, même avec un faux rapport PASS | unverified |
| Correction mécanique exacte et zéro enfant | pass |
| Correction mécanique avec un enfant supplémentaire | fail |

Ces gardes établissent la présence et la forme des artefacts. Elles ne prétendent pas comprendre les décisions produit. Le contrôle indépendant décrit plus haut reste une preuve séparée. Les tests du runner vérifient aussi le code de sortie 2 pour cette limite, le comportement inchangé quand le booléen vaut false, et le refus des types non booléens.

Le rejeu natif final `/root/explore_design_short/birch_title` a reçu la variante mécanique directement avec Architect, sans interdiction de descendants ajoutée au prompt. Il a appliqué « contrôle de construction n/a, correction mécanique dont la forme est fixée » et changé uniquement `# Ticktes` en `# Tickets`. Le coordinateur a relu le diff réel et exécuté le vérificateur : résultat `pass`. L'arbre natif observé ne montrait aucun descendant et l'acteur n'a demandé aucun lecteur. Ce transport ne fournit toutefois pas la liste exhaustive des enfants au runner : son verdict de délégation reste `unverified`, sans liste vide inventée. Le [reçu mécanique](issue-96-mechanical.json) conserve cette distinction. La table précédente décrit les verdicts déterministes quand les métadonnées requises sont disponibles, pas une certification de métadonnées absentes.

Après ces corrections et la passe deslop, `bash scripts/check.sh` a terminé avec le code 0 : 246 tests Python avec 1 saut déclaré, 29 tests Bun du dépôt, 231 tests des helpers, types et linters verts. Log local : `.cstack/cedar/review-fixes/check.log`. La revue indépendante du delta est assurée par `review_contracts` dans la tâche parent.

## Provenance locale

Les preuves brutes restent sous `.cstack/cedar/`, `.cstack/maple/` et `.cstack/poplar/` dans le worktree de l'issue. Les SHA-256 des compétences Architect effectivement utilisées sont :

- Baseline : `6f466590dfe29ba46a8508a99154d78b62c14d9e05708128bab30a31c065ba3d`.
- Candidate : `64dd5580bf8ee99697f8a6edf9058912e71980a0637b5d1055a8b2baf566996c`.

Le comportement du prompt de construction est une adaptation propre à cstack de l'idée publiée dans Superpowers v7.0.0. Sa provenance et sa licence sont enregistrées dans NOTICE.md ; aucun texte amont n'a été copié.

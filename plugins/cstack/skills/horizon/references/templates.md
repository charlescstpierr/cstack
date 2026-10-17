# Modèles d'artefacts Horizon

Utilise ces formes pour l'état Markdown local. Un tracker externe configuré garde les mêmes champs et relations conceptuels via les opérations nommées par `docs/agents/issue-tracker.md`.

## Layout local

```text
.cstack/horizon/<slug>/
├── map.md
├── tickets/
│   └── <id>-<slug>.md
├── research/
│   └── <id>-<angle>.md
├── spec.md
└── units/
    └── <id>-<slug>.md
```

Les fichiers carte et ticket sont le registre de planification. Les fichiers de recherche sont les preuves possédées par les enfants. `spec.md` est le handoff cohérent unique qui cite les tickets de décision. Les fichiers d'unités décrivent les tranches de build et l'acceptation; ils ne redéfinissent pas les décisions.

## Carte

```markdown
---
id: map
title: <titre de la carte>
type: map
status: open | research-pending | cleared
blocked_by: []
owner: <owner parent ou vide>
---

## Destination

<destination à atteindre par tout l'effort>

## Notes

<domaine, compétences compagnes et contraintes utilisateur explicites>

## Décisions à ce stade

- [<titre du ticket>](tickets/<id>-<slug>.md): <résumé d'une ligne>

## Pas encore spécifié

- <zone assez nette à revisiter, mais pas encore une question précise>

## Hors portée

- <travail exclu et pourquoi>
```

La carte indexe les décisions fermées; elle ne répète pas les réponses de tickets. Retire le brouillard quand il devient un ticket.

Pour l'état local, l'id du ticket est la valeur exacte des métadonnées `id` et le préfixe du nom de fichier avant le premier `-` : `tickets/01-choose-storage.md` a `id: 01`. Les liens de carte utilisent le nom de fichier complet. Chaque entrée `blocked_by` nomme le `id` d'un autre ticket; rejette les ids dupliqués, ids manquants, incohérences fichier/métadonnées et cycles de dépendance avant de sélectionner le travail.

## Métadonnées, propriété et éligibilité

La carte est un index. Sa section `Décisions à ce stade` contient des résumés d'une ligne et des liens; la réponse complète vit dans exactement un ticket. Un ticket a des métadonnées explicites `id`, `title`, `type`, `status`, `blocked_by` et `owner`. `owner` est l'identité stable du coordinateur ou de l'utilisateur authentifié entre sessions, jamais un tour transitoire ni un handle enfant. Un ticket `waiting` garde ce owner pour que le même coordinateur puisse le reprendre; un autre owner ne doit pas le prendre. Un ticket `research` porte une liste `research_children` d'au moins deux angles distincts; elle en porte normalement trois quand trois angles utiles existent. Les enfants de recherche écrivent seulement leurs propres artefacts; ils ne modifient jamais la carte ou le ticket, ne revendiquent pas de tickets et ne lancent pas d'enfants.

Avant de sélectionner du travail, valide tous les ids de tickets dans `blocked_by`, rejette les cycles de dépendance et identifie les tickets revendiqués par un autre owner. Un ticket est éligible au frontier seulement quand `status: ready`, que `owner` est vide et que chaque bloqueur a `status: resolved`. Un ticket bloqué nommé par l'utilisateur s'arrête avec son bloqueur; quand aucun ticket n'est nommé, choisis le premier ticket frontier indépendant éligible et laisse intacts les tickets bloqués ou revendiqués.

## Ticket de décision

La liste `research_children` ci-dessous concerne seulement `type: research`. Pour les autres types, omets ce champ.

```markdown
---
id: <id correspondant au préfixe du nom de fichier>
title: <titre de la question>
type: research | prototype | grilling | task
status: ready | claimed | waiting | resolved | out-of-scope
blocked_by: []
owner: <vide jusqu'à revendication>
research_children:
  - angle: <premier angle stable>
    child_handle: <id>-<angle>
    native_handle: <vide jusqu'au dispatch>
    child_state: queued
    artifact: <research/<id>-<angle>.md>
    attempt: 0
  - angle: <second angle stable>
    child_handle: <id>-<angle>
    native_handle: <vide jusqu'au dispatch>
    child_state: queued
    artifact: <research/<id>-<angle>.md>
    attempt: 0
---

## Question

<une décision ou un prérequis résolu par ce ticket>

## Réponse

<écrire seulement quand résolu; lier les artefacts de recherche ou prototype>
```

`blocked_by` contient des ids de tickets, pas de prose. Un ticket est éligible au frontier seulement avec `status: ready`, un `owner` vide et tous les bloqueurs `resolved`. `owner` est une identité stable de coordinateur ou d'utilisateur authentifié et reste défini pendant `waiting`; ne revendique jamais le ticket d'un autre owner et ne contourne pas un bloqueur non résolu.

## Cycle des enfants de recherche

Le parent est le seul rédacteur du ticket. Avant dispatch, réserve tous les angles de `research_children` selon le [contrat d'exploration déléguée](../../cstack/references/runtime/exploration.md). Chaque entrée possède un `angle`, un `child_handle` stable, un `native_handle`, un `child_state`, un chemin `artifact` distinct et un `attempt` initialement nul.

| État | Transition et preuve |
| --- | --- |
| `queued` | Jamais lancé ; peut partir dans la prochaine vague disponible. Écris `pending` **avant** l'appel natif. |
| `pending` | Dispatch commencé. Enregistre le `native_handle` retourné, puis passe à `running`. À la reprise, inspecte les enfants natifs avant toute nouvelle tentative, même si aucun handle n'a encore été enregistré. |
| `running` | Enfant identifié et actif ; attends son résultat, sans le relancer. |
| `completed` | Achèvement natif observé et artefact complet dont les citations répondent à l'angle, vérifié par le parent. Réutilise cette preuve, sans nouveau dispatch. |
| `failed` | Échec terminal observé ou artefact insuffisant. Une nouvelle tentative exige la preuve qu'aucun enfant de cet angle ne vit encore et suit la limite de relance du contrat runtime. |

Une entrée `pending` ou `running` n'est jamais relancée sur la seule foi du checkpoint. Réconcilie les handles avec les appels natifs observés ; si l'état reste inconnu, conserve le blocage de cet angle et rapporte la preuve manquante. Un enfant encore vivant interdit un second dispatch, quel que soit l'état enregistré. Pour une nouvelle tentative admissible, conserve le `child_handle`, incrémente `attempt`, puis repasse par `queued` et `pending` avant d'enregistrer le nouveau `native_handle`.

Pour un ancien ticket de recherche, migre les champs singuliers seulement si `child_handle` ou `native_handle` est renseigné. Transfère leurs valeurs dans une entrée `legacy`, puis retire les champs singuliers, y compris `attempt`. Des champs vides et `attempt: 0` seuls ne créent pas d'entrée legacy. Complète les angles manquants sans remplacer un handle actif ; une métadonnée manquante sur une tentative commencée doit être réconciliée avant tout dispatch. Cette conversion ne laisse qu'une source d'état. Si un ancien guide de suivi nomme un seul fichier `research/<id>.md`, traite-le comme le format hérité : conserve les preuves existantes et attribue toujours un fichier distinct à chaque nouvel angle.

Résous le ticket seulement quand toutes les entrées sont `completed` et que leurs preuves répondent à la question. Un artefact partiel, une entrée absente ou un état inconnu ne suffit pas.

### Dispatch et drainage

- Cartographie, étape 6 : pour chaque ticket `research` indépendant éligible au frontier, réserve-le avec `status: claimed`, un `owner` stable et `research_children` selon [le cycle des enfants](#cycle-des-enfants-de-recherche). Cette section définit les états, la migration, le dispatch et la reprise sans doublon. Conserve le nombre total d'angles prévus et mets les vagues suivantes en file selon la capacité native. Résous chaque appel avec `how explorer`, en conservant runtime, modèle et effort. Chaque enfant reçoit la question, son angle et son artefact réservé, sans droit de lancer des descendants. Une synthèse déléguée utilise `judgment and prose`; réserve `hardest tasks` à une architecture explicitement complexe.
- Cartographie, étape 7 : attends ou draine toutes les entrées `research_children` avant de revenir. Un enfant natif terminé ne réussit que si son artefact complet existe et que ses citations répondent à son angle; le parent vérifie chaque entrée et n'enregistre la réponse ni la résolution du ticket qu'après le succès de toutes les entrées. Un artefact partiel ou un enfant manquant laisse le ticket `claimed` ou `waiting`, jamais `resolved`. Réessaie seulement après avoir vérifié l'état natif du `native_handle` et confirmé qu'aucun enfant vivant ne reste; n'exécute jamais d'enfants concurrents en double. Garde les métadonnées revendiquées et rapporte les angles et handles `queued`, `pending`, `running` ou `failed` si le drainage ne peut pas finir.
- Travail d'un ticket, étape 3 : pour `research`, inspecte d'abord `research_children` et les champs singuliers hérités. S'il manque des entrées, réserve les angles manquants et lance-les avec la procédure de cartographie; consomme chaque artefact seulement après achèvement natif, valide chaque citation matérielle et laisse le parent enregistrer la réponse après le succès de toutes les entrées. Un enfant `pending`, `running`, `failed` ou partiel, ou un angle sans résultat, arrête avant résolution.
- Travail d'un ticket, étape 5 : pour tout nouveau ticket `research` éligible, réserve `status`, `owner` stable et `research_children` avec au moins deux angles, puis utilise les mêmes règles d'état natif, citation, retry et vagues que la cartographie. Un ticket avec un `child_handle` ou `native_handle` vivant est déjà lancé et ne doit pas être répété. Attends ou draine toutes les entrées avant de revenir; un artefact partiel est `pending` ou `failed`, pas une résolution.

### Affectation des enfants de recherche

Utilise ce prompt borné pour chaque entrée de `research_children`, en changeant seulement l'id du ticket, la question, l'angle, le `child_handle` et le chemin d'artefact :

```text
Tu es l’enfant de recherche pour le ticket Horizon <id>, sur l’angle <angle>, avec le handle logique <child_handle>.
Réponds seulement à cette question : <question du ticket>
Lis les sources primaires (documentation officielle, code source, spécifications ou APIs first-party).
Écris un artefact Markdown avec des findings concises et une citation pour chaque claim matérielle à <chemin d'artefact>.
Ne modifie pas la carte ni le ticket, ne modifie pas le code produit et ne lance pas d’enfants.
Retourne PASS avec le chemin d’artefact, ou BLOCKED avec la source ou capacité manquante exacte.
```

Le parent vérifie chaque artefact face à sa question, son angle et ses citations avant d'enregistrer une résolution. Un rapport d'enfant est une preuve, pas une permission d'élargir la portée; aucun ticket de recherche ne se résout tant qu'une entrée de `research_children` manque ou n'est pas terminée.

## Spec cohérente et unités verticales

```markdown
# Spec <destination>

## Destination
<un paragraphe>

## Décisions
- [<titre du ticket>](tickets/<id>-<slug>.md): <résumé de décision>

## Acceptation observable
- [ ] <comportement pouvant échouer à la frontière de vérification choisie>

## Hors portée
- <comportement exclu>

## Unités verticales
### <titre de l'unité>
**Livre :** <comportement complet visible par un utilisateur ou appelant>
**Bloquée par :** <ids d'unités ou aucune>
**Acceptation :**
- [ ] <critère observable indépendant>
```

La spec est le pont décision-vers-build. Chaque unité traverse les couches pertinentes et se vérifie indépendamment; choisis le playbook cstack existant seulement après l'achèvement de ce handoff.

## Contrat de handoff vers Orchestrate

Pour le playbook `orchestrate`, la spec contient exactement un bloc `horizon` au format JSON. Chaque fichier d'unité contient également un seul bloc `horizon`. Ces blocs rendent la définition importable sans déduire des dépendances depuis la prose. Les décisions complètes restent dans leurs tickets.

Exemple de bloc dans `spec.md` :

```horizon
{
  "schema": 1,
  "status": "ready",
  "goal": "Permettre de rechercher puis exporter les archives conservées.",
  "out_of_scope": ["Ne pas modifier les durées de conservation."],
  "context": ["README.md décrit le format actuel des archives."],
  "decisions": ["tickets/01-format.md"],
  "units": ["units/A-index.md", "units/B-export.md", "units/C-search.md", "units/D-interface.md"]
}
```

`schema` vaut `1` et `status` vaut `ready` seulement quand la définition est complète. `goal` énonce la destination. `out_of_scope` et `context` sont des listes non vides. `decisions` contient les chemins des tickets cités. Une destination claire sans décision ouverte peut utiliser `decisions: []`, avec la demande fixée et les preuves utiles dans `context`. `units` contient au moins un chemin d'unité.

Les chemins de `decisions` et `units` se résolvent depuis le dossier de la spec et doivent rester dans ce dossier après résolution. Chaque décision citée possède un frontmatter YAML avec une seule ligne `status: resolved` et une section `## Réponse` ou `## Answer` renseignée sans placeholder. Chaque fichier `tickets/*.md` absent de `decisions` porte explicitement `status: out-of-scope`. Une décision `waiting`, manquante, incomplète ou omise empêche donc l'import. Les tickets hors portée font aussi partie des sources dont l'import conserve l'empreinte. Pour un tracker distant, les fichiers de décision sont des copies locales vérifiées qui citent les références distantes. Préparer ces copies ne donne aucune autorité d'écriture au tracker.

Exemple de fichier A-index dans le dossier `units/` :

````markdown
# Index consultable des archives

```horizon
{
  "id": "A",
  "goal": "Retrouver une archive existante par son identifiant.",
  "blocked_by": [],
  "acceptance": ["Un identifiant connu retourne l'archive attendue; un identifiant absent retourne un résultat vide."],
  "writable": ["src/archive-index", "tests/archive-index"],
  "forbidden": ["Ne pas modifier le stockage des archives."],
  "context": ["README.md décrit les identifiants d'archives."],
  "verify": ["bun test tests/archive-index"]
}
```
````

Les IDs sont stables et uniques dans la spec. Ils commencent par une lettre ASCII ou un chiffre, puis contiennent seulement des lettres ASCII, des chiffres, `_` ou `-`. `blocked_by` contient des IDs d'unités de cette même spec, jamais des chemins ni des IDs de tickets. Les références inconnues et les cycles empêchent l'import.

Les listes `acceptance`, `writable`, `forbidden`, `context` et `verify` sont non vides. Chaque entrée est une chaîne renseignée sur une ligne, sans doublon ni placeholder `TODO`, `TBD` ou `<...>`. `acceptance` décrit des observations vérifiables. `verify` nomme les commandes ou contrôles exacts qui les vérifient. `writable` contient des chemins précis, relatifs à la racine du dépôt, sans chemin absolu, segment `.` ou `..`, double `/`, glob, antislash, ni racine `.git` ou `.cstack`. `forbidden` conserve les chemins et opérations exclus. Le coordinateur vérifie que les critères et frontières sont suffisants avant de marquer la spec `ready`; la validation de forme ne remplace pas ce jugement.

Pour l'exemple à quatre unités, les fichiers déclarent ce graphe :

| ID | Résultat | `blocked_by` |
| --- | --- | --- |
| A | Index consultable | `[]` |
| B | Export des archives | `[]` |
| C | Recherche utilisant l'index | `["A"]` |
| D | Interface de recherche et d'export | `["B", "C"]` |

Avec des frontières inscriptibles distinctes, A et B sont prêtes au départ. C attend la preuve vérifiée de A. D attend celles de B et C. Avant de réserver une unité dépendante, sa branche locale doit déjà contenir les commits vérifiés de ses bloqueurs. Les unités qui partagent un chemin d'écriture se réservent successivement, même si le graphe ne les relie pas.

L'import traduit les champs vers le brief existant :

| Définition Horizon | Brief Orchestrate |
| --- | --- |
| `goal` de l'unité | `GOAL` |
| `writable` | `SCOPE`, avec affectation d'une branche et d'un worktree exclusifs avant dispatch |
| Chemins de spec et d'unité, version SHA256, décisions, `blocked_by`, `context` | `CONTEXT` |
| `acceptance` | `ACCEPTANCE` |
| `verify` | `VERIFY` |
| `out_of_scope` et `forbidden` | `FORBIDDEN`, avec les limites d'autorité existantes |
| Contrat de rapport Orchestrate | `REPORT` avec statut, branche, SHA, PR éventuelle, contrôles et preuves |

Le brief inclut aussi `TIMEBOX` et `STANDING`. Le coordinateur fixe la limite de durée et transmet les ordres permanents courants dans le message d'affectation.

Horizon possède la définition dans la spec, les tickets et les unités. L'import conserve les empreintes SHA256 de ces sources et la définition dans `.cstack/orchestrate/<slug>/horizon.json`. Ce reçu note seulement la fin de la transaction d'import avec `committed`; il ne suit aucun achèvement d'unité. Les propriétaires et la progression restent dans `units.tsv`, les verdicts dans `ledger.tsv`, et les événements dans `inbox/`.

Un import répété de sources inchangées réutilise les unités et les briefs. Une modification des sources, un brief différent ou une collision d'ID bloque la reprise sans écraser les propriétaires ni les preuves. La [procédure Orchestrate](../../cstack/playbooks/orchestrate.md#reprendre-un-handoff-horizon) décrit l'import, la réservation avant dispatch et la réconciliation des interruptions.

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

Le parent est le seul rédacteur du ticket. Avant dispatch, réserve tous les angles de `research_children` selon le [contrat d'exploration déléguée](../../cstack/references/codex-runtime.md#exploration-déléguée). Chaque entrée possède un `angle`, un `child_handle` stable, un `native_handle`, un `child_state`, un chemin `artifact` distinct et un `attempt` initialement nul.

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

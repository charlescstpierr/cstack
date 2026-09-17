# Modèles d'artefacts Horizon

Utilise ces formes pour l'état Markdown local. Un tracker externe configuré garde les mêmes champs et relations conceptuels via les opérations nommées par `docs/agents/issue-tracker.md`.

## Layout local

```text
.cstack/horizon/<slug>/
├── map.md
├── tickets/
│   └── <id>-<slug>.md
├── research/
│   └── <id>.md
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

```markdown
---
id: <id correspondant au préfixe du nom de fichier>
title: <titre de la question>
type: research | prototype | grilling | task
status: ready | claimed | waiting | resolved | out-of-scope
blocked_by: []
owner: <vide jusqu'à revendication>
child_handle: <vide sauf si le type est research>
native_handle: <vide jusqu'au dispatch de l'enfant natif>
child_state: <vide | queued | pending | running | completed | failed>
artifact: <vide sauf si le type est research>
attempt: 0
---

## Question

<une décision ou un prérequis résolu par ce ticket>

## Réponse

<écrire seulement quand résolu; lier les artefacts de recherche ou prototype>
```

`blocked_by` contient des ids de tickets, pas de prose. Un ticket est éligible au frontier seulement avec `status: ready`, un `owner` vide et tous les bloqueurs `resolved`. `owner` est une identité stable de coordinateur ou d'utilisateur authentifié et reste défini pendant `waiting`; ne revendique jamais le ticket d'un autre owner et ne contourne pas un bloqueur non résolu. Pour la recherche, écris `child_handle`, `native_handle` (vide jusqu'au dispatch), `child_state: queued` avant dispatch (`pending` une fois le dispatch commencé), `artifact` et `attempt`; enregistre le handle natif retourné avant de revenir. Un enfant `pending` ou `running` est actif; `queued` est réservé pour une vague ultérieure. Un handle non terminal empêche les enfants en double. Un artefact partiel n'est pas une résolution.

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

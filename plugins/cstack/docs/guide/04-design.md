# Concevoir avant d'écrire du code

Une décision difficile mérite une forme explicite avant l'implémentation. cstack sépare l'architecture, les alternatives, la couverture parallèle et la critique adversariale.

## Préparations et routage

Ces compétences restent utilisables seules pour préparer une tâche. `$cstack:cstack` peut aussi les appeler sans vous demander de relancer la commande : `clarify` quand une vraie question métier bloque le bon résultat, et Horizon quand le travail mérite une carte de décisions sur plusieurs phases. Une correction claire conserve son parcours habituel.

| Compétence | Résultat | Délégation initiale |
| --- | --- | --- |
| [`$cstack:clarify`](../../skills/clarify/SKILL.md) | Décisions clarifiées, recommandations et contraintes établies à partir du projet. | Aucune par défaut ; faits indépendants si utile. |
| [`$cstack:domain`](../../skills/domain/SKILL.md) | Vocabulaire précis et décisions importantes selon les conventions existantes. | Aucune par défaut. |
| [`$cstack:horizon`](../../skills/horizon/SKILL.md) | Carte des décisions ouvertes, de leurs dépendances et des inconnues d'un objectif de plusieurs sessions. | Un enfant par recherche prête, sans délégation imbriquée. |
| [`$cstack:audit-architecture`](../../skills/audit-architecture/SKILL.md) | Candidats à une simplification, avec preuves dans le code et propositions avant/après. | Au plus un explorateur. |

`clarify` établit les faits accessibles avant de poser les questions réellement ouvertes. Les questions humaines restent réservées aux choix métier, produit ou périmètre que le dépôt ne peut pas résoudre. `domain` rédige le glossaire ou les ADRs seulement si la demande autorise ces documents. En lecture seule ou en mode Plan, les propositions restent dans la conversation.

Horizon conserve la limite de Wayfinder : la cartographie s'arrête après la création du plan de décisions ; une reprise traite au plus un ticket de décision, sauf pour les recherches. Les choix humains restent ouverts jusqu'à votre réponse. Une fois les décisions résolues, `$cstack:cstack` reprend les faits et lance les unités vérifiables du guide d'exécution adapté sans pause artificielle entre les phases. Horizon seul ne démarre pas l'implémentation, un goal natif, une PR distante, une fusion ou un déploiement automatiquement. Les recherches utilisent le rôle `how explorer`, la synthèse déléguée `judgment and prose`, et l'architecture complexe `hardest tasks`.

L'audit d'architecture examine des opportunités ; choisir un candidat autorise sa discussion, pas sa modification. Son rapport reste dans la conversation sauf demande d'export compatible avec le mode courant.

## Fixer la forme avec `$cstack:architect`

```text
$cstack:architect conçois la chaîne d'import avant l'implémentation. Pars de l'utilisation par les appelants.
```

[`$cstack:architect`](../../skills/architect/SKILL.md) lit le code concerné, pose les types et les frontières, puis garde la conception utilisable pendant l'implémentation.

## Comparer avec `$cstack:arena`

```text
$cstack:arena propose trois formes pour ce cache. Compare-les sur les invalidations et la lisibilité.
```

[`$cstack:arena`](../../skills/arena/SKILL.md) fait produire plusieurs propositions indépendantes, sélectionne une base et vérifie la synthèse. Utilisez-le quand la première conception risque de verrouiller une mauvaise forme.

## Couvrir des tranches avec `$cstack:swarm`

```text
$cstack:swarm vérifie chaque paquet avec son script de contrôle et rends un rapport unique.
```

[`$cstack:swarm`](../../skills/swarm/SKILL.md) donne à chaque sous-agent une tranche, une preuve et un résultat `PASS`, `ISSUES` ou `BLOCKED`. Il sert à la couverture et aux courses déclarées, pas à comparer des conceptions.

## Casser la proposition avec `$cstack:interrogate`

```text
$cstack:interrogate examine cette branche. Ne change rien et signale uniquement les bugs ou régressions.
```

[`$cstack:interrogate`](../../skills/interrogate/SKILL.md) sollicite plusieurs angles de revue, puis classe les constats. Rien n'est appliqué automatiquement.

Les trois réviseurs par défaut portent les axes Standards, Spec et contradictoire. Les comités personnalisés conservent exactement leur taille et leurs modèles. Une exigence manquée reste un constat pertinent même si un seul réviseur avait l'axe Spec. La revue du travail courant inclut les fichiers staged, unstaged et non suivis demandés ; une revue de PR ou de branche reste limitée aux commits désignés.

## Choisir le niveau de conception

Une petite modification finie peut recevoir seulement `$cstack:interrogate`. Un changement de frontière ou de propriété mérite `$cstack:architect`, puis éventuellement `$cstack:arena`. Une matrice de vérifications mérite `$cstack:swarm`. Une décision coûteuse à inverser mérite une critique avant livraison.

Suivant : [construire et nettoyer le changement](./05-build-and-clean.md).

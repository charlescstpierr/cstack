# Concevoir avant d'écrire du code

Une décision difficile mérite une forme explicite avant l'implémentation. cstack sépare l'architecture, les alternatives, la couverture parallèle et la critique adversariale.

## Fixer la forme avec `$cstack:architect`

```text
$cstack:architect conçois le pipeline d'import avant l'implémentation. Pars de l'utilisation par les appelants.
```

[`$cstack:architect`](../../skills/architect/SKILL.md) lit le code concerné, pose les types et les frontières, puis garde la conception utilisable pendant l'implémentation.

## Comparer avec `$cstack:arena`

```text
$cstack:arena propose trois formes pour ce cache. Compare-les sur les invalidations et la lisibilité.
```

[`$cstack:arena`](../../skills/arena/SKILL.md) fait produire plusieurs propositions indépendantes, sélectionne une base et vérifie la synthèse. Utilisez-le quand le premier design risque de verrouiller une mauvaise forme.

## Couvrir des tranches avec `$cstack:swarm`

```text
$cstack:swarm vérifie chaque paquet avec son script de contrôle et rends un rapport unique.
```

[`$cstack:swarm`](../../skills/swarm/SKILL.md) donne à chaque sous-agent une tranche, une preuve et un résultat `PASS`, `ISSUES` ou `BLOCKED`. Il sert à la couverture et aux courses déclarées, pas à comparer des designs.

## Casser la proposition avec `$cstack:interrogate`

```text
$cstack:interrogate examine cette branche. Ne change rien et signale uniquement les bugs ou régressions.
```

[`$cstack:interrogate`](../../skills/interrogate/SKILL.md) sollicite plusieurs angles de revue, puis classe les constats. Rien n'est appliqué automatiquement.

## Choisir le niveau de design

Une petite modification finie peut recevoir seulement `$cstack:interrogate`. Un changement de frontière ou de propriété mérite `$cstack:architect`, puis éventuellement `$cstack:arena`. Une matrice de vérifications mérite `$cstack:swarm`. Une décision coûteuse à inverser mérite une critique avant livraison.

Suivant : [construire et nettoyer le changement](./05-build-and-clean.md).

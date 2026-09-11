# Recettes et pièges

Les exemples donnent la forme minimale d'une bonne demande. Remplacez les chemins, la commande et la preuve par ceux de votre projet.

## Comprendre un sous-système inconnu

```text
$cstack:how explique d'abord cette initialisation. Puis $cstack:why cherche la raison de la régression récente.
```

## Obtenir un second avis sur un design

```text
$cstack:arena compare trois formes pour cette interface et explique le choix final.
```

## Vérifier des tranches indépendantes

```text
$cstack:swarm contrôle chaque paquet sous packages/ et rends un rapport unique.
```

## Revoir une branche avec scepticisme

```text
$cstack:interrogate examine toute la branche sans modifier les fichiers. Signale seulement les bugs ou régressions.
```

## Corriger un bug avec une preuve ciblée

```text
$cstack:cstack reproduis l'écriture en double. Si le test local est bon marché, utilise $cstack:tdd, puis corrige et rejoue la preuve.
```

## Garder une tâche autonome honnête

```text
$cstack:cstack continue jusqu'à ce que toutes les fixtures passent. N'envoie aucun message externe. Journalise les décisions.
```

## Réorienter une tâche

```text
Le but est seulement la reproduction. Ne corrige pas encore.
```

```text
Applique le principe « Prove It Works » et montre la sortie réelle, pas seulement le log de build.
```

## Obtenir une reformulation simple

```text
$cstack:bro
```

[`$cstack:bro`](../../skills/bro/SKILL.md) reformule le dernier message en termes simples.

## Les pièges

- Énumérer les compétences dans chaque demande. Donnez l'objectif et les contraintes ; le playbook séquence le reste.
- Donner une condition de fin vague. Préférez une commande, une valeur, un fichier ou un flux qui peut passer ou échouer.
- Faire écrire plusieurs agents dans une même worktree. Isolez les tentatives et fusionnez après vérification.
- Utiliser `$cstack:arena` pour une matrice de couverture. Utilisez `$cstack:swarm` pour répartir des tranches.
- Accepter chaque commentaire de revue. Vérifiez chaque constat contre le comportement et le périmètre.
- Affirmer le succès sur un build vert. Vérifiez l'artefact réel.
- Croire qu'une tâche locale survit à la fermeture de Codex. Demandez un scheduler natif séparément si vous en avez besoin.
- Donner à Benny une activation native. Ce pack reste documentaire ; voyez [sa limite d'intégration](../../automations/benny/README.md).

Retour à [l'index du guide](./README.md).

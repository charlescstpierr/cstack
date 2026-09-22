# Recettes et pièges

Les exemples donnent la forme minimale d'une bonne demande. Remplacez les chemins, la commande et la preuve par ceux de votre projet.

## Comprendre un sous-système inconnu

```text
$cstack:how explique d'abord cette initialisation. Puis $cstack:why cherche la raison de la régression récente.
```

## Obtenir un second avis sur une conception

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

## Corriger une anomalie avec une preuve ciblée

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

## Un seul agent travaille

Si cstack fait tout lui-même alors que la compétence annonce des exécutants parallèles, la cause est presque toujours la même : Codex exige que la demande de délégation figure dans **votre** tour, et cette règle d'outil prime sur le texte d'une compétence.

Sélectionnez la compétence depuis le sélecteur plutôt que de taper son nom : le prompt par défaut porte déjà la demande. En texte brut, ajoutez-la vous-même.

```text
$cstack:cstack Corrige ce bug. Délègue le travail indépendant à des sous-agents natifs en parallèle.
```

Si un acteur unique persiste, vérifiez dans l'ordre :

1. La réponse porte-t-elle l'étiquette `single-agent` et signale-t-elle l'indépendance manquante ? C'est le repli prévu, et il couvre deux cas : votre demande excluait la délégation, ou l'hôte n'exposait aucun emplacement. La raison nommée à côté de l'étiquette dit lequel. Son absence indique autre chose.
2. Votre configuration Codex autorise-t-elle les agents, et sa limite de threads simultanés dépasse-t-elle un ?
3. Votre version de CLI est-elle récente ? Les essais du dépôt ont observé des sous-agents terminés en `0.153.4`.

Un sous-agent ne peut pas en lancer un autre. Une ventilation imbriquée est donc toujours sérialisée.

## Les pièges

- Compter sur le texte d'une compétence pour déclencher une délégation. Demandez-la dans votre tour.
- Énumérer les compétences dans chaque demande. Donnez l'objectif et les contraintes ; le guide d'exécution séquence le reste.
- Donner une condition de fin vague. Préférez une commande, une valeur, un fichier ou un flux qui peut passer ou échouer.
- Faire écrire plusieurs agents dans une même worktree. Isolez les tentatives et fusionnez après vérification.
- Utiliser `$cstack:arena` pour une matrice de couverture. Utilisez `$cstack:swarm` pour répartir des tranches.
- Accepter chaque commentaire de revue. Vérifiez chaque constat contre le comportement et le périmètre.
- Affirmer le succès sur un build vert. Vérifiez l'artefact réel.
- Croire qu'une tâche locale survit à la fermeture de Codex. Demandez un scheduler natif séparément si vous en avez besoin.
- Donner à Benny une activation native. Ce pack reste documentaire ; voyez [sa limite d'intégration](../../automations/benny/README.md).

Retour à [l'index du guide](./README.md).

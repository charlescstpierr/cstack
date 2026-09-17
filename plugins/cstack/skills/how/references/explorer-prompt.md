# Modèle de prompt Explorer

Construis le prompt de chaque subagent explorer depuis ce modèle. Remplis les placeholders.

---

Tu explores un codebase pour comprendre comment quelque chose fonctionne. Rassemble des faits : trace les chemins de code, lis les implémentations, cartographie les composants. Un agent séparé écrira l'explication destinée à l'humain depuis tes findings; privilégie donc la rigueur et l'exactitude plutôt que la prose.

D'autres explorers étudient en parallèle différentes tranches du même sous-système. N'essaie pas de tout couvrir. Concentre-toi sur ton angle assigné et va en profondeur.

## Question

> {QUESTION}

## Ton angle d'exploration

{EXPLORATION_ANGLE}

## Instructions d'exploration

Commence par trouver le code pertinent. Utilise Glob pour trouver répertoires et fichiers, Grep pour trouver les symboles clés, Read pour comprendre l'implémentation réelle. Ne devine pas depuis les noms. Lis le code.

Suis ce motif :
1. **Trouver le point d'entrée.** Qu'est-ce qui déclenche ce comportement ? Une action utilisateur, un appel API, une tâche planifiée ? Trouve où cela commence.
2. **Tracer le flux.** Suis la chaîne d'appels depuis le point d'entrée. Lis chaque fonction. Comprends quelles données circulent et comment elles se transforment.
3. **Cartographier les abstractions clés.** Quels types, interfaces, services ou classes sont centraux ? Lis leurs définitions. Comprends ce qu'ils représentent et pourquoi ils existent.
4. **Trouver les frontières.** Où ce sous-système s'interface-t-il avec les autres ? Qu'est-ce qui entre, qu'est-ce qui sort ?
5. **Chercher le non évident.** Quelque chose de surprenant ? Un artefact historique ? Quelque chose qu'un nouvel arrivant comprendrait mal ?

Continue jusqu'à pouvoir décrire l'image complète sans gestes vagues. Si tu atteins une partie impossible à tracer, dis-le explicitement. "Je n'ai pas pu déterminer comment X se connecte à Y" vaut mieux qu'inventer.

## Sortie

Retourne tes findings dans cette structure. Sois factuel et précis. Référence les chemins exacts, noms de fonctions, noms de types et numéros de lignes quand pertinent.

### Composants trouvés
Les types, services, classes et abstractions clés. Pour chacun : nom, chemin de fichier et description d'une phrase de ce qu'il fait.

### Flux
Le flux d'exécution étape par étape. Pour chaque étape : quelle fonction/méthode s'exécute, dans quel fichier, ce qu'elle fait, ce qu'elle appelle ensuite. Inclus les données qui circulent entre étapes.

### Fichiers lus
Chaque fichier lu pendant l'exploration, pour que l'explainer puisse les référencer.

### Frontières
Où ce sous-système se connecte aux autres parties du codebase. Les entrées et sorties.

### Choses non évidentes
Tout ce qui est surprenant, motivé historiquement ou facile à se tromper. Les choses qui semblent devoir fonctionner d'une façon mais fonctionnent autrement.

### Questions ouvertes
Tout ce que tu n'as pas pu tracer ou comprendre entièrement. Sois honnête sur les écarts.

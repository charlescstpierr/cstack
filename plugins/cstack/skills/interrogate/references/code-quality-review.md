# Revue de qualité de code

Chaque reviewer applique cette lentille de qualité de code en plus de la rubrique. C'est un standard strict centré sur la qualité d'implémentation, la maintenabilité, la qualité des abstractions et la santé du codebase.

Avant tout, sois ambitieux sur la structure du code. Ne te contente pas d'identifier du nettoyage local. Cherche activement les mouvements de "code judo", des restructurations qui préservent le comportement tout en rendant l'implémentation beaucoup plus simple, plus petite, plus directe et plus élégante.

## Prompt de base

Pars de cette baseline :

> Effectue un audit profond de qualité de code des changements de la branche courante.
> Repense la structure / l'implémentation des changements pour améliorer significativement la qualité de code sans impacter le comportement.
> Travaille à améliorer les abstractions, la modularité, réduire le spaghetti code, améliorer la concision et la lisibilité.
> Sois ambitieux : s'il existe un chemin clair pour améliorer l'implémentation qui implique de restructurer une partie du codebase, vas-y.
> Sois extrêmement minutieux et rigoureux. Mesure deux fois, coupe une fois.

## Dimensions

Chaque dimension est énoncée une fois. Applique celles qui sont pertinentes.

0. **Sois ambitieux sur la simplification structurelle.** Ne t'arrête pas à "cela pourrait être un peu plus propre". Cherche des recadrages qui font disparaître des branches, helpers, modes, conditionnels ou couches entières. Suppose qu'un mouvement de "code judo" est souvent disponible. Il utilise mieux l'architecture existante et rend le changement beaucoup plus simple. Si tu peux supprimer de la complexité au lieu de la réarranger, pousse fortement.

1. **Ne laisse pas une PR pousser un fichier de moins de 1k lignes à plus de 1k lignes sans très bonne raison.** Traite cela comme une forte odeur. Préfère extraire des helpers, sous-composants ou modules. Si le diff franchit ce seuil, demande si le code doit d'abord être décomposé. Dispense seulement pour une raison structurelle convaincante où le fichier résultant reste clairement organisé.

2. **Ne permets pas la croissance spaghetti dans le code existant.** Méfie-toi des nouveaux conditionnels ad hoc, cas spéciaux éparpillés ou branches ponctuelles insérées dans des flux sans rapport. Traite les "weird if statements in random places" comme un problème de conception, pas une remarque de style. Préfère pousser la logique dans un helper, une machine d'état ou un module dédié plutôt que d'emmêler un chemin existant.

3. **Biais vers le nettoyage de la conception, pas seulement l'acceptation d'un code qui marche.** Si le comportement peut rester identique pendant que la structure devient significativement plus propre, pousse pour la version plus propre. Préfère les simplifications qui retirent des pièces mobiles aux refactors qui répartissent la même complexité ailleurs.

4. **Préfère du code direct, ennuyeux et maintenable au code hacky ou magique.** Traite les comportements cassants, ad hoc ou "magiques" comme des problèmes. Sois sceptique envers les mécanismes génériques qui cachent de simples hypothèses de forme de données. Signale les abstractions minces, wrappers d'identité ou helpers relais qui ajoutent de l'indirection sans acheter de clarté.

5. **Pousse sur la propreté des types et frontières quand elle affecte la maintenabilité.** Questionne l'optionalité inutile, `unknown`, `any` ou le code lourd en casts quand une frontière typée plus claire pourrait exister. Préfère des modèles typés explicites aux objets ad hoc lâches. Si une branche s'appuie sur un fallback silencieux pour masquer un invariant flou, demande si la frontière doit être rendue explicite.

6. **Garde la logique dans la couche canonique et réutilise les helpers existants.** Signale la logique de fonctionnalité qui fuit dans des chemins partagés ou les détails d'implémentation qui fuient par les APIs. Préfère les utilitaires canoniques existants aux one-offs. Pousse le code vers le bon package, service ou module au lieu de normaliser la dérive.

7. **Traite l'orchestration séquentielle inutile et les mises à jour non atomiques comme des odeurs de conception quand la structure plus propre est évidente.** Si du travail indépendant est sérialisé sans raison, demande s'il doit tourner en parallèle. Si des mises à jour liées peuvent laisser l'état à moitié appliqué, pousse pour une structure plus atomique. Ne sur-indexe pas les micro-optimisations, mais signale la complexité d'orchestration évitable qui rend le code plus fragile.

## Attentes de sortie

Priorise d'abord les régressions structurelles de qualité de code et les simplifications manquées, puis le spaghetti et la complexité de branches, puis les problèmes de frontières, types et taille de fichier, puis les plus petits problèmes de modularité et lisibilité. N'inonde pas la revue avec des nits de faible valeur quand des problèmes structurels plus grands existent. Préfère quelques commentaires à forte conviction à une longue liste de notes cosmétiques.

## Barre d'approbation

N'approuve pas seulement parce que le comportement semble correct. Traite ces points comme des bloqueurs présumés sauf justification de l'auteur : la PR conserve beaucoup de complexité incidente alors qu'un mouvement de code judo la supprimerait; pousse un fichier de moins de 1000 lignes à plus de 1000 lignes; ajoute des branches ad hoc qui emmêlent un flux existant; éparpille des checks de fonctionnalité dans du code partagé; ajoute une abstraction, un wrapper ou un contrat lourd en casts inutile; duplique un helper existant ou met la logique dans la mauvaise couche alors qu'un foyer canonique clair existe. Si ces conditions ne sont pas réunies, laisse un feedback explicite et actionnable et pousse pour une décomposition plus propre.

## Ton de revue

Sois direct, sérieux et exigeant sur la qualité. Ne sois pas grossier, mais n'adoucis pas les gros problèmes de maintenabilité en suggestions légères. Si le code salit le codebase, dis-le. Si l'implémentation a manqué une simplification dramatique évidente, dis-le aussi. Ne te satisfais pas de "peut-être renommer ceci" quand le vrai problème est structurel.

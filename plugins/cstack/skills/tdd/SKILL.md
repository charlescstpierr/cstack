---
name: tdd
description: "Utiliser $cstack:tdd seulement quand l'utilisateur demande explicitement du TDD, un test échouant ou un test de régression, OU quand le bug à une cible de test locale évidente et peu coûteuse. Sauter quand le chemin de test est flou, coûteux, lourd en intégration ou non demandé."
---

# Correction de bug en TDD

Contrat d'exécution : [`../cstack/references/codex-runtime.md`](../cstack/references/codex-runtime.md).

Quand tu corriges un bug avec un chemin de test clair et peu coûteux, rends le comportement cassé exécutable avant de changer le code de production. L'objectif est un test de régression cible qui échoue avant le correctif et passe après.

Ne force pas un test quand ce serait impraticable. Si le test disponible exigeait une large configuration de harnais, des mocks fragiles, une infrastructure end-to-end lente, un état production-only, des étapes de reproduction vagues ou un gros churn de fixtures sans rapport, saute l'ajout d'un nouveau test et utilise plutôt la vérification utile la plus proche.

## Flux de travail

1. **Comprendre le bug.** Identifie le comportement attendu, le comportement actuel, le chemin touché et la plus petite reproduction observable.
2. **Choisir la vérification exécutable la plus étroite.** Préfère le test unitaire, composant, intégration ou régression le plus proche déjà utilisé pour ce chemin de code. Si aucun chemin de test pratique n'est évident, n'en crée pas un depuis zéro seulement pour satisfaire le flux de travail.
3. **Écrire d'abord le test échouant.** Ajoute le plus petit test cible qui aurait attrapé le bug. Le test doit encoder le comportement attendu, pas miroiter l'implémentation courante.
4. **Exécuter le nouveau test avant de corriger.** Confirme qu'il échoue pour la raison attendue. S'il passe ou échoue pour une raison sans rapport, corrige le test ou la reproduction avant de modifier l'implémentation.
5. **Corriger le bug.** Fais le plus petit changement de production qui satisfait le comportement attendu tout en préservant les contrats voisins.
6. **Relancer le test de régression.** Confirme que le test passe maintenant.
7. **Exécuter la validation voisine.** Lance les tests adjacents pertinents, typéchecks, lint ou checks de scénario quand le changement à un risque plus large.

## Si un test échouant est impraticable

Ne saute pas silencieusement l'étape de régression. Avant de corriger, explique explicitement pourquoi un test échouant est impossible ou ne vaut pas son coût, puis choisis la vérification de régression exécutable disponible la plus proche. Exemples : script cible, commande de reproduction manuelle, automatisation navigateur, comparaison de snapshots, assertion de logs ou check d'intégration cible.

Préfère aucun nouveau test à un mauvais test. Un mauvais test teste surtout des mocks, encode des détails de l'implémentation courante, dépend du timing ou d'un état global sans rapport, exige une infrastructure coûteuse pour un petit correctif, ou serait supprimé immédiatement après avoir prouvé le correctif.

## Garde-fous

- Ne change pas les tests simplement pour correspondre à une implémentation fausse.
- N'affaiblis pas les assertions existantes sauf si le comportement attendu à vraiment change et que la raison est claire.
- Garde le test de régression centre sur le bug. Évite le grand churn de fixtures ou l'expansion de couverture sans rapport.
- N'ajoute pas de tests quand le signal pratique est faible. Utilise une vérification manuelle ou scriptee et dis pourquoi.
- Si le bug est flaky, rends le test deterministe quand c'est possible et documente le signal verrouille.
- Si le bug expose une classe plus large d'échecs, livre d'abord le chemin de régression cible, puis envisage une couverture sœur supplémentaire.

## Réponse finale

Rapporte les preuves, pas seulement le résultat :

- Nomme le test ou check exécutable échouant avant correction et l'échec qu'il a produit.
- Nomme l'exécution de test passant après correction et toute validation voisine effectuee.
- Si la preuve d'échec avant correction n'a pas pu être démontrée, dis pourquoi et décris le check de régression le plus proche utilisé à la place.

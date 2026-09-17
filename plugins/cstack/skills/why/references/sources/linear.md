# Tickets Linear

## Ce que cette source contient

- Issues décrivant fonctionnalités, bugs et leur motivation
- Docs projet attachés aux issues (souvent PRD ou specs)
- Relations parent/sous-issue (initiative large -> tickets précis)
- Commentaires d'issues (clarifications, changements de portée, justification "pourquoi on fait ça")
- Labels (p. ex. `compliance`, `customer-request`, `perf`) qui signalent le type de motivation
- Mises à jour de statut qui expliquent les changements de portée
- Pièces jointes et PR GitHub liées

Linear est l'endroit où vit souvent le contexte produit/business : la couche "nous faisons ceci parce que le client X l'a demandé" ou "c'est pour l'initiative conformité du T3".

## Comment la chercher

Utilise le MCP Linear.

1. **Commence par les tickets liés.** Si les commits ou PR graine référencent des IDs de tickets (p. ex. `ENG-1234`, `[BUG-567]`), récupère-les d'abord avec `get_issue`. Lis toute l'issue, commentaires inclus.
2. **Liste les issues liées par mots-clés.** Utilise `list_issues` avec recherche texte pour le nom de fonctionnalité, symbole clé ou terme métier. Essaie plusieurs formulations.
3. **Parcours l'arbre d'issues.** Si tu arrives sur une sous-issue, récupère son parent. Les sous-issues sont tactiques. Les parents portent souvent le "pourquoi".
4. **Lis les docs projet.** Si l'issue appartient à un projet, utilise `get_project` et vérifie les docs attachés. Les documents de niveau projet capturent le plus souvent specs et justification.
5. **Vérifie labels et jalons.** Les labels suggèrent la catégorie de motivation (customer-request, incident-followup, compliance). Les milestones lient le travail à des échéances, qui révèlent souvent la motivation.

## À quoi ressemble une bonne preuve ici

- Une description d'issue énonçant le problème business : "Le client Acme a besoin de X à cause de son audit SOC2"
- Un commentaire enregistrant une décision : "Nous avons décidé d'adopter l'approche B parce que l'approche A exigerait de toucher au service de facturation"
- Une issue parent avec un titre d'initiative : "Préparation Enterprise T3" ou "Réduire les échecs de paiement"
- Un PRD ou une spec attachés
- Des labels comme `customer:acme`, `incident-followup`, `compliance`, `perf-regression`

## Pièges courants

- **Dérive de portée.** Le ticket référencé par la PR peut avoir été fermé puis rouvert avec une portée différente. Lis tout l'historique.
- **Templates mécaniques.** Certaines équipes imposent des sections "Why" remplies de boilerplate. Le texte générique ("improve user experience") n'est probablement pas une vraie réponse.
- **Tickets périmés.** Les vieux tickets reflètent souvent une version du plan qui a changé. Vérifie les dates et croise avec la date de livraison du code.
- **Chaînes closed-as-duplicate.** Suis les relations duplicate-of jusqu'au ticket canonique.
- **Contenu workspace privé.** Si tu ne peux pas accéder à une issue, note-le comme écart au lieu de deviner.

## Quoi retourner

Pour chaque ticket pertinent :
- ID et titre du ticket
- Problème/motivation cité depuis la description ou les commentaires (pas paraphrasé. Le synthétiseur a besoin du texte exact pour citer)
- Labels, issue parent, projet
- Auteur, date de création, date de fermeture
- Lien vers le ticket si disponible

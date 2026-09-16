# Docs Notion

## Ce que cette source contient

- PRD (product requirement documents)
- Specs techniques et RFC
- Architectural decision records (ADRs)
- Notes de réunion de design reviews
- Pages d'équipe avec contexte de domaine
- Postmortems d'incidents
- Runbooks qui peuvent expliquer du code défensif
- Documents de stratégie qui fixent des priorités

Notion est l'endroit où le "pourquoi" vit souvent en format long avant de devenir du code. Une fonctionnalité significative a généralement un doc.

## Comment la chercher

Utilise le MCP Notion.

1. **Recherches par mots-clés avec `notion-search`.** Essaie :
   - Le nom de fonctionnalité
   - Symboles clés / noms de classes du code cible
   - Handles d'auteurs (les docs de conception sont souvent rédigés avant que le code arrive)
   - Chaînes d'erreur ou termes visibles utilisateur
   - Requêtes bornées dans le temps si tu sais quand le code a été livré
2. **Récupère les pages candidates avec `notion-fetch`.** Lis le contenu complet, pas l'aperçu. La justification est souvent enfouie au milieu.
3. **Suis backlinks et pages enfants.** Les docs de conception ont souvent des sous-pages pour alternatives considérées, annexes ou notes d'implémentation.
4. **Vérifie les bases liées.** `notion-query-data-sources` et `notion-query-meeting-notes` peuvent faire émerger des notes de réunion ayant discuté la décision.
5. **Cherche les espaces spécifiques à l'auteur.** Si l'auteur de PR a un carnet personnel (courant dans certaines entreprises), il peut contenir la réflexion exploratoire avant le code.

## À quoi ressemble une bonne preuve ici

- Un PRD avec section "Énoncé du problème" ou "Motivation" qui correspond au but du code cible
- Une section "Alternatives considérées" ou "Approches rejetées"
- Un postmortem qui nomme le code cible comme correction d'un incident précis
- Des notes de réunion qui enregistrent "nous avons décidé X parce que Y" et se lient au même auteur/plage de dates que la PR
- Un template ADR rempli non trivialement (statut, contexte, décision, conséquences)

## Pièges courants

- **Docs dépassés.** Les specs sont souvent écrites avant l'implémentation puis non mises à jour. Le doc peut décrire un plan qui a changé. Croise avec la PR réelle.
- **Dérive doc vs réalité.** Une spec peut dire "we'll do X" mais le code fait Y. Signale la divergence. Le synthétiseur exposera la contradiction.
- **Templates boilerplate.** Certaines organisations exigent une section "Why" remplie de fluff. Cherche la spécificité.
- **Docs non liés.** Le doc le plus pertinent peut n'être lié de nulle part. Les recherches larges aident.
- **Brouillons multiples.** Si un sujet a plusieurs docs, trouve celui qui a été finalisé ou mis à jour le plus récemment. Vérifie les dates.
- **Pages restreintes.** Si tu ne peux pas accéder à une page, note-le comme écart.

## Quoi retourner

Pour chaque doc pertinent :
- Titre et URL
- Auteurs et date de dernière mise à jour
- Texte de motivation (citation verbatim), avec page/section
- Pages liées pertinentes (pour que le synthétiseur puisse les citer)
- Si le doc était finalisé ou brouillon

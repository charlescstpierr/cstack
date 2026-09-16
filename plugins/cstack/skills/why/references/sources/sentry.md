# Historique d'erreurs Sentry

## Ce que cette source contient

Sentry est l'archive des choses qui ont mal tourné. Pour du code défensif, correctif ou de gestion d'erreurs, il contient souvent la motivation directe : exceptions précises, stack traces et fréquences qui ont poussé quelqu'un à ajouter un check, catch, retry ou fallback.

- **Issues.** Erreurs groupées avec counts, timestamps first/last seen, releases affectées et commentaires
- **Events.** Instances d'erreurs individuelles dans une issue (stack traces, tags, contexte utilisateur)
- **Releases.** Enregistrements de déploiement avec issues associées (utile pour "quelle version a corrigé ceci ?")
- **Replays.** Enregistrements de sessions d'erreurs visibles utilisateur (si activé)
- **Profiles.** Données de profiling performance (moins utile pour "why", plus pour "how slow")
- **Issue comments & assignments.** Contiennent parfois des notes d'ingénieur sur la cause racine

La chose la plus précieuse fournie par Sentry est la **corrélation temporelle** : "l'issue X a été créée le 2024-01-02, a atteint un pic de 500 events/jour, puis a disparu après la release v2.14.0 du 2024-01-15, la release qui livrait le check défensif."

## Comment la chercher

Utilise le MCP Sentry.

1. **S'orienter.** Si tu ne connais pas le slug projet et l'organisation :

   ```
   find_organizations
   find_projects
   ```

2. **Chercher les issues liées à la cible.**

   ```
   search_issues (natural language, e.g., "errors in PaymentService timeout", "unhandled exceptions in uploadFile")
   ```

   Bons composants de requête : classes d'exception gérées par la cible, nom de fonction ou classe cible, chaînes de messages d'erreur testées par la cible, chemin de fichier de la cible.

3. **Rétrécir par release et fenêtre temporelle.**

   ```
   search_issue_events (filtrer par release, temps, environnement, ID de trace, tags)
   get_issue_tag_values (for an issue, see distribution across versions, users, environments)
   ```

   Pour une issue suspecte, vérifie :
   - **Première apparition.** Quand l'erreur a-t-elle commencé ?
   - **Dernière apparition.** Quand s'est-elle arrêtée ? Cela s'aligne-t-il avec la date de livraison de la cible ?
   - **Releases affectées.** Quelles versions l'ont vue ? Laquelle était le fix ?
   - **Trajectoire de fréquence.** A-t-elle spiké puis été résolue ?

4. **Récupérer l'événement complet pour contexte.**

   ```
   get_sentry_resource (pass a Sentry URL or type+ID)
   ```

   La stack trace passe-t-elle par le code cible ? Les tags et breadcrumbs correspondent-ils aux conditions contre lesquelles la cible défend ?

5. **Vérifier les releases proches de la cible.**

   ```
   find_releases (autour de la date de commit de la cible)
   ```

   Croise la version de release avec la date de merge de la PR.

6. **Utiliser Seer avec parcimonie.**

   ```
   analyze_issue_with_seer
   ```

   Seer produit des analyses IA de cause racine. Utile comme générateur d'hypothèses, mais traite-les comme inférence, pas comme autorité. Les événements et stack traces réels sont la preuve primaire. Le récit de Seer est secondaire.

## À quoi ressemble une bonne preuve ici

- Une issue dont le **first seen** est juste avant la PR cible et le **last seen** juste après, suggérant que la cible a traité cette erreur
- Des stack traces qui passent par ou tombent sur la fonction cible, montrant le mode d'échec exact défendu
- Un commentaire sur l'issue de l'auteur de PR décrivant le fix
- La description de PR cible ou le message de commit référence une URL ou ID Sentry
- Une issue à fort count qui s'arrête après la release contenant la cible

## Pièges courants

- **Dérive de grouping.** Sentry groupe les erreurs par fingerprint. Refactors ou renommages peuvent suivre la "même" erreur sous un nouvel ID d'issue. Si une issue s'arrête brusquement, l'erreur a peut-être juste été regroupée. Vérifie les nouvelles issues immédiatement après.
- **La corrélation de release est bruitée.** Une release contient beaucoup de commits. Une issue qui s'arrête à v2.14.0 ne prouve pas que la cible l'a corrigée. Un autre changement de la même release a pu le faire. Croise avec le commit exact de la cible.
- **Fixes silencieux.** Parfois l'erreur s'arrête parce que l'amont a changé, pas grâce au code défensif. La corrélation suggère le fix; elle ne prouve pas l'auteur.
- **Resolved != fixed.** Des issues peuvent être marquées "resolved" manuellement sans changement de code. Traite `resolved` comme marqueur humain, pas preuve que le code a corrigé.
- **Hallucinations Seer.** Seer peut générer des explications confiantes mais fausses. Reviens aux événements, stack traces et timestamps réels pour les claims.
- **Sampling.** Certains projets échantillonnent agressivement les events. Un faible count peut signifier fort sampling, pas rareté. En cas de doute, note l'écart.

## Quoi retourner

Pour chaque issue pertinente :
- ID et titre de l'issue
- Projet et organisation
- Timestamps first seen / last seen
- Count d'events (et taux de sampling si connu)
- Releases affectées
- Extrait représentatif de stack trace montrant la pertinence pour la cible (extrait verbatim, pas résumé)
- Corrélation first/last-seen avec la date de livraison de la cible
- Lien vers l'issue
- Tout commentaire d'auteur ou note de résolution

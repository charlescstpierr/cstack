# Conversations Slack

## Ce que cette source contient

- Discussions en temps réel de problèmes et décisions
- Channels d'incidents où des décisions d'urgence ont été prises
- Threads de discussion design où les compromis ont été débattus
- Questions répondues par des ingénieurs seniors qui ne sont pas arrivées dans les docs
- Discussions post-merge qui expliquent pourquoi quelque chose a été revisité
- DMs (habituellement non cherchables; borne la portée en conséquence)

Slack est fréquemment là où les *vraies* décisions ont été prises, surtout pour les petits changements qui ne méritaient pas de doc. C'est aussi la source la plus éphémère. Les threads sont supprimés, les channels archivés et la qualité de recherche se dégrade avec le temps.

## Comment la chercher

Les outils du connecteur Slack varient. Inspecte le schéma réel du connecteur disponible et son état d'authentification. Utilise seulement un flux d'authentification exposé par ce connecteur quand le setup est demandé. Si l'accès manque ou échoue, rapporte cette source comme indisponible et continue la recherche indépendante; n'invente pas d'outil d'authentification et n'installe pas automatiquement un connecteur.

1. **Recherche bornée par auteur.** Messages de l'auteur de PR autour de la date de merge. Cela réduit énormément la portée et trouve souvent de l'or.
2. **Recherche par mots-clés pour le nom de fonctionnalité et les symboles clés.** Inclus fautes et formulations casual.
3. **Recherche d'URL de PR.** Slack lie souvent les PR quand elles sont revues ou discutées. Cherche l'URL de PR (ou seulement `/pull/<number>`).
4. **Recherche de chaîne d'erreur.** Si le code gère une erreur précise, cherche la chaîne d'erreur. Les threads d'incident apparaissent souvent.
5. **Recherche bornée par channel.** Rétrécis aux channels probables :
   - `#eng-*`. Discussions d'ingénierie
   - `#proj-*`. Channels projet
   - `#incident-*` / `#sev-*`. Channels d'incident
   - Channels spécifiques à l'équipe propriétaire
   - Channels de design review
6. **Parcours de thread.** Quand tu trouves un message pertinent, récupère tout le thread. La décision vit souvent dans les réponses.

## À quoi ressemble une bonne preuve ici

- Un thread où les compromis ont été explicitement débattus ("J'allais utiliser A, mais B est meilleur parce que...")
- Un message de channel incident décrivant le bug que le code prévient
- Une question d'un reviewer et une réponse autoritative de l'auteur ou du lead
- Une référence à une réunion où une décision a été prise
- Un message d'un product manager ou ingénieur facing client expliquant une demande client

## Pièges courants

- **Limites d'archéologie de channel.** Les très vieux messages peuvent être partis à cause de politiques de rétention. Si tu ne trouves rien avant une date, note la falaise de rétention.
- **DMs non cherchés.** Beaucoup de décisions arrivent en DMs non cherchables. Tu les manqueras. C'est une limite connue.
- **Blagues spéculatives comme "décisions".** Slack est casual. "Lol just do the thing" n'est pas une décision, même si cela a précédé le commit. Cherche une discussion réfléchie.
- **Effondrement de contexte dans un message seul.** Sans le thread, un message isolé se lit souvent autrement. Récupère toujours les threads.
- **Échecs d'auth.** Si le MCP n'est pas authentifié, arrête. N'invente pas de findings. Rapporte que Slack n'était pas cherchable.

## Quoi retourner

Pour chaque thread pertinent :
- Nom du channel
- Permalink ou ID de thread
- Participants
- Plage de dates de la discussion
- Citations clés (verbatim) avec attribution
- Contexte : thread/incident/discussion dont cela faisait partie

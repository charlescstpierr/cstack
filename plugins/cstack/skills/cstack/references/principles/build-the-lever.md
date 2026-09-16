# Construire le levier

Lisez cette référence lorsqu'un processus cstack actif vous route ici ou lorsque l'utilisateur nomme ce principe. Suivez le [contrat d'exécution Codex](../codex-runtime.md) pour le périmètre et les permissions.

Lorsque le travail n'est pas trivial, construisez l'outil qui le fait au lieu de le faire à la main.

**Pourquoi :** deux gains. Débit : un codemod, un générateur ou un script fait le travail de la même façon à chaque fois et se relance gratuitement. Confiance : l'outil est un artefact qu'un relecteur peut lire et relancer pour vérifier le travail. Les changements faits à la main ne peuvent être revérifiés qu'en les refaisant. Un script déterministe transforme « fais-moi confiance » en « lance ceci ».

**Motif :** par défaut, construisez le levier. Sautez-le seulement quand la tâche est triviale, quelques éditions évidentes visibles d'un coup d'œil.

- Faites la première unité à la main pour apprendre la recette, puis construisez l'outil. Prouvez-le en le relançant sur cette unité et en comparant le diff avec votre version faite à la main. Rendez le levier sûr à relancer.
- Codemod ou script pour les éditions, générateur pour les fichiers répétitifs, requête dump-vers-sqlite pour l'analyse, contrôle réexécutable pour la vérification.
- Un levier déterministe bat la dispersion. Si l'outil peut traiter chaque unité en une passe, lancez-le vous-même. Ne dispersez pas des délégués pour appliquer à la main ce qu'un script peut faire.
- Lorsque vous dispersez le travail vers des sous-agents, écrivez le levier comme une compétence qu'ils lisent tous : la recette, le contrat de vérification et les barrières à ne pas toucher dans un seul artefact. Gardez-le hors du périmètre d'écriture des délégués afin qu'ils ne puissent pas modifier discrètement le contrat.
- Appliquer ce principe produit un fichier. Si vous l'avez cité et qu'il n'y a ni codemod, ni script, ni générateur, ni compétence de délégation dans le diff, vous ne l'avez pas appliqué.
- Commitez le levier quand le travail dépasse la session.

**Équilibre :** la barre est la trivialité, pas la répétition. Un cas unique mérite quand même un levier lorsque le levier rend le travail vérifiable. Conformément au [Protocole de paresse](laziness-protocol.md), construisez le plus petit script qui fait ou prouve le travail, jamais un framework.

Distinct de [Encoder les leçons dans la structure](encode-lessons-in-structure.md), qui transforme une instruction récurrente en garde-fou durable. Ici, il s'agit du débit et de la relisibilité du travail devant vous. Pour scripter la vérification elle-même, voir [Prouver que ça marche](prove-it-works.md).

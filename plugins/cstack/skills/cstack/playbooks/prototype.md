### Prototype

Suivez [le contrat d’exécution Codex](../references/codex-runtime.md).

**Tu possèdes la décision de conception, pas le code. Le prototype est un instrument jetable. La vraie construction suit Feature.**

Le seul playbook où le « plus petit changement » du Protocole de paresse et la barre de vérification s’inversent. Vitesse avant finition, la qualité du code ne compte pas, pas de planification. La rigueur est de choisir la bonne conception à peu de frais. Propose des variations que l’utilisateur n’a pas demandées, jette une approche et essaie-en une autre.

1. Délimite la décision que le prototype doit prendre : quelle mise en page, quelle interaction, quelle densité, ou pour une bifurcation empirique quel comportement, timing ou approche. Pas de décision signifie pas de prototype. Route vers Feature.
2. Quand la décision porte sur une interface existante, pars de l’écran réel dans son état courant et liste ce qui doit rester identique : navigation, charte, éléments que l’utilisateur a dit aimer. Chaque variante le conserve, et la présentation montre l’avant et l’après côte à côte en nommant ce qui change.
3. Rassemble des références quand l’espace de conception est ouvert. Cherche des précédents, résume un moodboard de thèmes, palettes et mises en page, laisse l’utilisateur choisir des directions avant de construire. Saute cette étape quand la direction est fixée.
4. Construis du jetable dans un répertoire scratch isolé, séparé de la source de production. Pour une décision visuelle, HTML/CSS/JS vanilla ou la pile la plus légère qui rend l’idée, dépendances CDN, serveur de dev avec hot reload. Pour une décision comportementale ou de timing, le plus petit script qui exerce la question. Pas de framework de production, pas de tests, pas d’abstractions.
5. Quand tu compares des alternatives, construis-les derrière un seul sélecteur (boutons ou touche), chaque variante libellée. C’est la référence du principe [Épuiser l’espace de conception](../references/principles/exhaust-the-design-space.md) rendue bon marché.
6. Vérifie avec l’outil natif disponible pour la cible. Pour une décision visuelle, utilise un navigateur ou simulateur disponible pour piloter et capturer chaque variante. Pour une décision comportementale ou de timing, journalise le timing, imprime la sortie ou inspecte le rendu. L’observation est le test.
7. Présente les alternatives, compromis et une recommandation. La sortie est la décision plus l’artéfact jetable, pas du code expédiable. Passe la direction choisie à **Feature** (ou `architect` pour la forme) pour la vraie construction.

Ne committe pas le jetable sauf si l’utilisateur a demandé de le garder. Si un commit arrive, lance d’abord `../../deslop/SKILL.md` sur le diff. Garde `deslop skipped: <reason>` quand une étape ne peut vraiment pas s’exécuter.

**Réponse :** les variantes explorées, les preuves (captures d’écran pour une décision visuelle, sortie ou timing observés pour une décision comportementale), compromis, ta recommandation et le chemin scratch. Dis clairement que le prototype est jetable. Chaque affirmation porte sa preuve ou son étiquette dans la même phrase. Mesuré, inféré ou supposition. Une prédiction ou une cause non observée est une supposition. Ne remets jamais à l’humain un contrôle que tu pourrais lancer.

# L'expérience d'abord

Lisez cette référence lorsqu'un processus cstack actif vous route ici ou lorsque l'utilisateur nomme ce principe. Suivez le [contrat d'exécution Codex](../codex-runtime.md) pour le périmètre et les permissions.

Lorsque la commodité d'implémentation entre en conflit avec le plaisir utilisateur, choisissez le plaisir.

- Chaque fonctionnalité, contrôle et option doit être justifié
- Livrer moins, livrer mieux (une expérience polie avec trois fonctionnalités bat une expérience rugueuse avec dix)
- Prototyper avant de s'engager (les décisions de conception coûtent moins cher en HTML jetable qu'en code de production)
- Soigner les détails (transitions, alignement, espacement, feedback, états d'erreur)
- Resserrer la boucle centrale (chaque fonctionnalité doit servir le processus central ou s'écarter)

L'utilisateur est la personne qui consomme le travail. Pour une UI, c'est l'utilisateur final. Pour une bibliothèque ou une API interne, c'est le collègue qui l'importe. L'ingénieur qui maintient ensuite le code est aussi un utilisateur. Pesez son expérience de la même façon et expliquez l'impact depuis sa perspective.

Les fondations doivent servir l'expérience. La pensée fondationnelle gouverne la *séquence* du travail. Ce principe gouverne la *cible*.

# Séquencer le travail en unités vérifiables

Lisez cette référence lorsqu'un processus cstack actif vous route ici ou lorsque l'utilisateur nomme ce principe. Suivez le [contrat d'exécution Codex](../codex-runtime.md) pour le périmètre et les permissions.

Ordonnez le travail comme une séquence de petites unités, chacune se terminant dans un état que vous pouvez vérifier, et n'avancez pas tant que l'unité courante n'est pas verte.

**Pourquoi :** une casse attrapée à l'unité qui l'a causée est peu coûteuse à localiser. Une casse attrapée après un lot est enfouie, et vous avez déjà construit plus loin sur une base cassée. Séquencer ces mêmes unités dans une livraison qu'un relecteur peut rejouer transforme « fais-moi confiance » en « regarde-le passer rouge, puis vert ».

**Exécution.** Dans une passe, une migration ou toute série d'éditions similaires, vérifiez chaque changement avant de commencer le suivant. Chaque unité est une parenthèse avant/après : état connu bon, un changement, lancer le contrôle, puis avancer. Rebasez d'abord sur un tronc propre afin que chaque contrôle mesure contre la vraie base. Quand un levier fait les éditions, le contrôle par unité est presque gratuit. Lancez-le quand même.

**Livraison.** Empilez commits et PR dans l'ordre qui prouve le travail. La forme canonique est le test échoué d'abord, puis le correctif au-dessus. D'autres ordres de récit sont une soustraction avant le remodelage, une capture de base avant le traitement, l'échafaudage avant la fonctionnalité. Chaque commit atterrit seul et la séquence se lit comme un argument.

**Motif :**
- Choisir la plus petite unité qui se termine par un contrôle : une édition plus son test, ou un commit autonome.
- Vérifier avant d'avancer. Rouge vers vert par unité, jamais reporté au lot final.
- Ordonner les unités afin que la séquence construise la confiance d'elle-même, pour vous pendant l'exécution et pour un relecteur qui lit la pile.

Le complément de séquençage à la référence de principe [Prouver que ça marche](prove-it-works.md), qui garde chaque contrôle réel, et à la référence de principe [Construire le levier](build-the-lever.md), qui rend le contrôle par unité bon marché.

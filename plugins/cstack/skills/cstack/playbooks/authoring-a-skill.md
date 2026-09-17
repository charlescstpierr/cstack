### Rédiger ou modifier une compétence

Suivez [le contrat d’exécution Codex](../references/codex-runtime.md).

**Tu possèdes la voix de la compétence.**

1. Utilise les instructions système skill-creator quand la session courante les expose. Sinon, suis le format de compétence et le validateur actuels du dépôt.
2. Valide la compétence : le frontmatter contient `name` et `description`, les fichiers référencés existent, les liens entre compétences se résolvent.
3. Applique ces quatre contrôles d’écriture pour agents à chaque instruction nouvelle ou modifiée :
   - Le pointeur nomme la vraie branche déclencheuse et pointe vers l’unique source de vérité.
   - Chaque étape possède un critère d’achèvement vérifiable.
   - Le détail propre à une branche est divulgué progressivement derrière une référence au lieu d’alourdir tous les chemins.
   - Chaque règle change une décision, emploie une formulation positive et apparaît à un seul endroit.
4. Pour une nouvelle instruction, exécute une preuve de comportement réelle dans une fixture isolée ou avec la plus petite invocation native qui l’atteint. Inspecte l’artéfact résultant et les effets de bord ; un grep sur des titres ou formulations n’est pas une preuve. Garde ces contrôles dans ce playbook plutôt que de créer une compétence publique d’écriture.
5. Lance **Ouvrir une PR** seulement quand l’utilisateur a autorisé la création de PR. Sinon, laisse un changement local vérifié.

Dans le doute, supprime. Garde seulement la prose qui change une décision. Dis-lui de faire la chose et saute la justification. Explique seulement quand la règle serait confuse sans explication. Adapte le ton au périmètre. Pointe vers des sources structurelles (types, READMEs, config) selon la référence de principe [Encoder les leçons dans la structure](../references/principles/encode-lessons-in-structure.md). Délègue aux autres compétences par chemin. Ne répète pas. Un flux de travail que tu rencontres sans cesse mais qui n’est pas capturé → propose une nouvelle compétence.

**Réponse :** résumé de la compétence, décisions de conception clés, notes de validation. Chaque affirmation porte sa preuve ou son étiquette dans la même phrase. Mesuré, inféré ou supposition. Une prédiction ou une cause non observée est une supposition. Ne remets jamais à l’humain un contrôle que tu pourrais lancer.

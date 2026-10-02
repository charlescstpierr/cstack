# Ne jamais bloquer sur l'humain

Lisez cette référence lorsqu'un processus cstack actif vous route ici ou lorsque l'utilisateur nomme ce principe. Suivez le [contrat d'exécution Codex](../codex-runtime.md) pour le périmètre et les permissions.

L'humain supervise de façon asynchrone. Les agents doivent rester débloqués. Prenez des décisions raisonnables, avancez et laissez l'humain corriger la trajectoire après coup.

**Pourquoi :** chaque pause de permission bloque la chaîne et fait de l'humain le goulot. Comme les changements de code sont réversibles et relisibles, une mauvaise décision coûte généralement moins cher qu'un blocage.

**Motif :**
- **Avancez, puis présentez.** Faites le travail, montrez le résultat. Ne demandez pas « devrais-je faire X ? ». Faites X, expliquez pourquoi.
- **Réservez les questions aux vraies ambiguïtés.** Demandez seulement lorsque vous ne pouvez pas inférer l'intention depuis le contexte.
- **Rendez le système autoréparateur.** Quand vous remarquez un problème, consignez-le et corrigez-le au tour suivant.
- **La supervision est asynchrone.** Concevez les processus pour une revue après coup.
- **Sous un accord d'autonomie totale**, décidez un choix que l'accord couvre, agissez et rapportez-le, sans mot de réponse à attendre. Pour un choix que seul l'opérateur peut faire, appliquez un défaut et rapportez-le avec son explication complète et le mot qui l'annule. Les barrières que l'opérateur a nommées et les frontières ci-dessous exigent toujours l'opérateur.

**Frontières :**
- **Les actions irréversibles** (force-push, suppression de données de production, envoi de messages externes) nécessitent une autorisation explicite ; réutilisez l'autorisation déjà présente, sous réserve des contrôles d'approbation de l'hôte.
- **Les actions réversibles** (écrire du code, éditer des notes, diviser des tâches) doivent avancer sans blocage.
- **La direction produit** vient de l'humain. *L'exécution* ne doit pas bloquer.

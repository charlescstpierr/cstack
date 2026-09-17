# Garder la fenêtre de contexte

Lisez cette référence lorsqu'un processus cstack actif vous route ici ou lorsque l'utilisateur nomme ce principe. Suivez le [contrat d'exécution Codex](../codex-runtime.md) pour le périmètre et les permissions.

La fenêtre de contexte est finie et non renouvelable dans une session. Chaque token doit valoir son coût.

**Pourquoi :** le débordement de contexte dégrade la qualité du raisonnement, crée des artefacts de compression et bloque la progression.

**Motif :**
- **Isolez les grosses charges utiles.** Routez les sorties verbeuses, captures d'écran et documents volumineux vers des sous-agents. Le contexte principal reçoit des résumés, pas des données brutes.
- **Ne lisez pas ce que vous n'utiliserez pas.** Lisez sélectivement selon la pertinence. Si un fichier n'est pas nécessaire à la tâche courante, sautez-le.
- **Gardez le contenu fréquemment utilisé en ligne.** Les modèles et références utilisés à chaque invocation appartiennent au fichier de compétence, pas à des fichiers séparés qui coûtent une lecture à chaque fois.
- **Dimensionnez les phases et plafonnez le périmètre.** Limitez les fichiers par phase, fixez des budgets de tours, comptabilisez les coûts de mécanisme.

# Corriger les causes racines

Lisez cette référence lorsqu'un processus cstack actif vous route ici ou lorsque l'utilisateur nomme ce principe. Suivez le [contrat d'exécution Codex](../codex-runtime.md) pour le périmètre et les permissions.

En débogage, ne corrigez pas les symptômes. Remontez chaque problème jusqu'à sa cause racine et corrigez-le là.

**Pourquoi :** les correctifs de symptômes s'accumulent. Chaque contournement rend le système plus difficile à raisonner, et le vrai anomalie reste là. Les correctifs de causes racines sont plus lents au départ mais réduisent le temps total de débogage.

**Motif :**
- Reproduire d'abord
- Demander « pourquoi » jusqu'à atteindre la cause racine
- Ne pas ajouter de gardes (ajouter une vérification nil pour taire un crash est un correctif de symptôme)
- Si un contournement nécessite un commentaire d'un paragraphe pour le justifier, le code est mauvais (corrigez le code, pas le commentaire)
- Chercher le motif, pas seulement l'instance (greppez le même motif, corrigez toutes les instances)
- Quand vous êtes bloqué, instrumentez. Ne devinez pas (ajoutez des logs, lisez l'erreur réelle)

**Anomalies au redémarrage : soupçonner l'état avant le code**

Quand quelque chose « échoue après redémarrage », soupçonnez d'abord l'état persistant périmé : fichiers de config, caches, fichiers de verrou, état sérialisé. Si effacer un fichier d'état restaure le comportement, priorisez la validation de l'état comme correctif.

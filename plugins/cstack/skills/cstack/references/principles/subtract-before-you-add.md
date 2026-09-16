# Soustraire avant d'ajouter

Lisez cette référence lorsqu'un processus cstack actif vous route ici ou lorsque l'utilisateur nomme ce principe. Suivez le [contrat d'exécution Codex](../codex-runtime.md) pour le périmètre et les permissions.

Lorsque vous faites évoluer un système, retirez d'abord la complexité, puis construisez.

**Pourquoi :** ajouter à un système complexe compose la complexité. Retirer d'abord laisse moins de code, révèle la structure essentielle et rend généralement le prochain conception évident. Par défaut, soustrayez.

Faites de la simplification un investissement continu. Laissez le conception légèrement plus simple et plus capable derrière la même surface, ou une surface plus petite, que celle trouvée.

**Le motif :**
- Séquencer le retrait avant la construction
- Couper avant de polir (atteindre le minimum avant d'investir dans la qualité)
- Concevoir pour l'usage observé, pas pour des cas limites spéculatifs
- Aucun validateur, analyseur ou garde spéculatif au-delà de ce que la spec demande
- Simplifier les invites (retirer les instructions redondantes, les modèles excessifs)
- Quand une référence n'a pas de contenu nouveau, la supprimer plutôt que laisser un coquille vide

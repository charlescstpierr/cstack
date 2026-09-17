# Migrer les appelants puis supprimer les API anciennes

Lisez cette référence lorsqu'un processus cstack actif vous route ici ou lorsque l'utilisateur nomme ce principe. Suivez le [contrat d'exécution Codex](../codex-runtime.md) pour le périmètre et les permissions.

Quand nous décidons qu'une nouvelle API est la bonne conception, migrez les appelants et retirez l'ancienne API dans la même vague de refactorisation au lieu de préserver des couches de compatibilité.

**Règle :**
- Ne gardez pas les chemins d'API anciennes seulement parce que des appelants internes existent encore
- Inventoriez les appelants, migrez-les et supprimez immédiatement l'ancienne API
- Traitez les adaptateurs temporaires comme exceptionnels et limités dans le temps, pas comme architecture par défaut
- Mettez à jour les tests pour affirmer le nouveau contrat, et supprimez les tests qui protègent seulement des détails d'implémentation pré-refactorisation

**Quand cela s'applique :**
- Aucun utilisateur externe ne dépend de la compatibilité ascendante
- Le projet peut absorber des changements cassants coordonnés
- La nouvelle API fait partie d'une initiative de simplification ou de refactorisation

Garder à la fois l'ancienne et la nouvelle API crée une complexité à deux chemins, ralentit le nettoyage et donne l’impression que la base de code s’alourdit sans fin.

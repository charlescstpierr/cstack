# Exécution orientée résultat

Lisez cette référence lorsqu'un processus cstack actif vous route ici ou lorsque l'utilisateur nomme ce principe. Suivez le [contrat d'exécution Codex](../codex-runtime.md) pour le périmètre et les permissions.

Optimisez pour l'état final voulu et vérifiable plutôt que pour la préservation d'états intermédiaires fluides.

**Pourquoi :** garder chaque étape intermédiaire entièrement stable crée souvent du code de compatibilité temporaire qui devient une dette durable. Convergez vers l'architecture cible et prouvez la correction à des frontières de vérification explicites.

**Règle centrale :**
- Prioriser l'intégrité de l'état final plutôt que la stabilité transitionnelle
- La casse intermédiaire est acceptable lorsqu'elle est planifiée, bornée et réversible
- Toujours exécuter la vérification finale avant de déclarer terminé

**Garde-fous :**
- Utiliser ceci pour les réécritures et migrations planifiées avec frontières de phases explicites
- Déclarer où la casse temporaire est acceptable
- Garder des contrôles à fort signal pour les zones activement touchées pendant la migration
- Exiger une vérification statique et à l'exécution complète à la fin du plan

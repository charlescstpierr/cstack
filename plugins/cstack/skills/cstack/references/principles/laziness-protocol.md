# Protocole de paresse

Lisez cette référence lorsqu'un processus cstack actif vous route ici ou lorsque l'utilisateur nomme ce principe. Suivez le [contrat d'exécution Codex](../codex-runtime.md) pour le périmètre et les permissions.

Visez le maximum de résultat avec le minimum de code et de complexité.

- **Préférez la suppression.** Quand on vous demande de refactoriser ou d'améliorer, cherchez les retraits avant les ajouts.
- **Maintenez une hiérarchie d'appels plate.** Évitez les chaînes d'appels profondes. Une interface riche qui cache un travail substantiel n'est pas une chaîne d'appels profonde. Si répondre à une question exige de suivre plus de 3 fichiers ou couches, aplatissez.
- **Consolidez les décisions.** Ne répétez pas le même choix à plusieurs endroits. Placez-le derrière une seule source de vérité et passez le résultat comme simple drapeau.
- **Minimisez le diff.** Faites le plus petit changement qui résout le problème. Moins de lignes bat le passe-partout « élégant ».
- **Questionnez le câblage.** Si une tâche vous demande de faire passer un nouveau signal à travers des types, schémas, chaînes ou couches similaires, arrêtez-vous et cherchez un chemin plus direct.
- **Traquez les petites fuites.** Retirez les minuscules pass-throughs, fuites de représentation et choix dupliqués avant qu'ils se propagent. Les petites fuites se composent en coûts de coordination permanents.

**Le test :** si un développeur humain trouverait le code épuisant à maintenir, c'est une mauvaise solution.

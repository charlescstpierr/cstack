# Attaquer la prémisse

Lisez cette référence lorsqu'un processus cstack actif vous route ici ou lorsque l'utilisateur nomme ce principe. Suivez le [contrat d'exécution Codex](../codex-runtime.md) pour le périmètre et les permissions.

Lorsque deux correctifs ou plus qui partagent une même prémisse échouent à la même porte, soupçonnez la prémisse, pas les correctifs.

**Pourquoi :** chaque échec sous une prémisse partagée constitue une preuve sur cette prémisse.

**Motif :**
- **Écrivez la prémisse.** La prémisse est la phrase unique que chaque correctif échoué supposait.
- **Faites un recensement avant le correctif suivant.** Comptez le déséquilibre par acteur. Le recensement montre quels acteurs portent le déséquilibre, pas son ampleur. Écrivez le recensement comme script réexécutable, conformément à [Construire le levier](build-the-lever.md).
- **Lisez le biais.** Si les mêmes quelques acteurs portent la majeure partie du déséquilibre à chaque exécution, quelque chose leur assigne ce rôle. Trouvez ce qui assigne le rôle. Cette assignation est le prochain « pourquoi », conformément à [Corriger les causes racines](fix-root-causes.md).
- **Supprimez l'asymétrie au lieu de la compenser**, conformément au [Protocole de paresse](laziness-protocol.md). Faites tourner le rôle entre les acteurs, randomisez l'assignation ou déplacez le rôle, afin qu'aucun acteur ne le porte à chaque exécution. Un chemin de retour, un pool partagé, un passage de relais par lot ou un rééquilibrage périodique laisse l'assignation en place et ajoute du travail à chaque exécution.

**Arrêt :**
- Ne commencez pas le correctif suivant avant que la prémisse soit écrite et que le recensement existe.
- Si le recensement est équilibré entre les acteurs, la prémisse n'est pas la cause. Cherchez la cause ailleurs et gardez le recensement comme preuve.

Ce principe est distinct de [Redessiner à partir des premiers principes](redesign-from-first-principles.md), qui reconstruit une conception autour d'une nouvelle exigence. Il questionne un fait que la conception courante suppose.

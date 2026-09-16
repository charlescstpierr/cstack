# Prouver que ça marche

Lisez cette référence lorsqu'un processus cstack actif vous route ici ou lorsque l'utilisateur nomme ce principe. Suivez le [contrat d'exécution Codex](../codex-runtime.md) pour le périmètre et les permissions.

Vérifiez chaque sortie de tâche en contrôlant directement la chose réelle. N'inférez pas depuis des proxys, auto-rapports ou « ça compile ».

**Pourquoi :** un travail non vérifié a une correction inconnue. La vérification indirecte (mtimes de fichiers, fraîcheur de sorties, auto-rapports d'agents, captures mises en cache) semble moins chère que l'observation directe. Agir sur une mauvaise inférence coûte bien plus cher que vérifier la source.

**Motif :** après toute tâche terminée, demandez : « comment prouver que cela marche vraiment ? »

Contrôlez la chose réelle, pas un proxy :
- Vérifiez directement la vivacité du processus, pas indirectement via un état dérivé
- Lisez la valeur réelle, pas une représentation mise en cache ou dérivée
- Quand la vérification échoue, soupçonnez la méthode d'observation avant de soupçonner le système

Code et fonctionnalités :
1. Construisez-le (nécessaire mais pas suffisant)
2. Lancez-le et exercez le vrai chemin de fonctionnalité
3. Vérifiez la chaîne complète : les données circulent-elles de l'entrée à la sortie ?
4. Pour les intégrations, testez le chemin de communication complet de bout en bout

Délégation : faites confiance aux artefacts, pas aux auto-rapports.
Lorsque vous vérifiez un travail délégué, inspectez l'artefact de sortie réel (git diff, contenu des fichiers, comportement à l'exécution), pas le résumé du délégué.

## Scripter le contrôle quand vous le pouvez

La preuve la plus forte est un script déterministe qui relance la même comparaison, pas un coup d'œil ponctuel. Écrivez le script, lancez-le et gardez sa sortie comme artefact qu'un relecteur peut relancer au lieu de vous croire sur parole.

Gardez l'artefact visible pour l'humain. Commitez-le seulement pour du travail grand ou complexe où la trace doit rester auditée plus tard, comme un gros portage ou une migration (la compétence **show-me-your-work**).

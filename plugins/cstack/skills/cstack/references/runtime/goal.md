# Goal global

Partie du [contrat d’exécution Codex](../codex-runtime.md), lue quand sa situation se présente.

Un Goal natif exige une demande explicite de l'utilisateur. Pour une implémentation multi-phase coordonnée par cstack, cette demande peut être la phrase du `default_prompt` effectivement insérée dans le message envoyé. Lire ce YAML, sélectionner une skill sans cette phrase, une invocation nue, une configuration sauvegardée ou « continue » seul n'accordent pas cette autorisation. Réutilise une autorisation explicite déjà donnée pour la même tâche ; ne la redemande pas à chaque phase.

Si cette autorisation et le périmètre multi-phase sont présents, le coordinateur applique le cycle de vie de [Exécution autonome](../../playbooks/autonomous-run.md). Le résultat par défaut est une PR testée, revue indépendamment et prête pour revue. Les limites explicites comme « local seulement » priment. Un correctif mécanique, une question, la préparation seule et le mode Plan suivent leur parcours normal sans activation automatique. Une demande directe de Goal garde son périmètre explicite.

Le Goal couvre les playbooks successifs, sans remplacer leurs contrôles ni les modèles du setup. Une fin de phase retourne au coordinateur, pas à un nouvel objectif. Merge, installation et déploiement font partie du prédicat uniquement si l'utilisateur les a autorisés. Sans outils Goal exposés, annonce cette capacité manquante et continue le travail autorisé au premier plan ; ne prétends pas avoir activé Goal. Ni hook Stop, ni scheduler, ni daemon ne sont ajoutés. La session doit rester active ; aucune reprise après fermeture n'est garantie.

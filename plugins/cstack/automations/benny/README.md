# Benny

Benny est le pack amont de triage Slack, de reproduction de anomalies et de suivi de correctifs. Il dépend des webhooks, de l'API Slack et d'une interface d'automatisation Cursor. Codex ne fournit pas cette activation native, et cstack n'installe ni webhook, ni planificateur, ni connecteur Slack.

Ce dossier est donc une référence documentaire uniquement. Il ne contient aucune compétence enregistrée et ne démarre aucune automatisation. Le pack original est disponible à [ce commit amont](https://github.com/cursor/plugins/tree/889ec4b68fa5aab0e867dad71ec3fdf386ae48f3/pstack/automations/benny).

Avec un connecteur autorisé et une demande explicite de l'utilisateur, un agent Codex peut effectuer manuellement des étapes bornées comme lire un fil, analyser une pièce jointe, rechercher un doublon, lancer une reproduction locale, vérifier un correctif et préparer un rapport ou une PR brouillon. Chaque action externe doit passer par l'outil connecté disponible et par l'autorisation de l'utilisateur. Une réponse ne déclenche pas automatiquement de message Slack, de ticket, de PR, de fusion ou de déploiement.

Pour obtenir des automatisations persistantes, il faut un service externe qui possède les webhooks, le stockage d'état, les identifiants et les contrôles d'accès nécessaires. Configurez ce service séparément et faites vérifier ses permissions avant tout envoi.

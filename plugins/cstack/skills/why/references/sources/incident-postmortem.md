# Contexte incident et postmortem

Pas une source séparée, un **angle transversal**. Les incidents motivent souvent du code défensif ("nous avons ajouté ce check après la panne X"), donc si la cible semble défensive (checks de nullité, logique de retry, gestion de timeout, limitation de débit, feature flags), cherche spécifiquement l'historique d'incidents dans chaque source disponible :

- **Notion** : cherche des postmortems qui mentionnent le fichier cible, la fonctionnalité ou la chaîne d'erreur
- **Linear** : cherche les tickets étiquetés `incident`, `sev-*`, `postmortem-action-item`, `reliability`
- **Slack** : cherche les channels `#sev-*` et `#incident-*` autour des dates d'ajout du code cible
- **Git** : les commits avec des messages comme "fix d'incident", "ajout d'un check défensif", "revert" suivi de "réappliquer avec..." sont de forts signaux
- **Datadog** : `search_datadog_incidents` pour des dossiers d'incident formels avec timelines, dashboards et monitors créés comme actions de postmortem
- **Sentry** : issues dont la fenêtre first-seen/last-seen s'aligne avec la date de livraison PR de la cible, stack traces passant par la cible
- **Databricks** : les événements d'analytique produit qui classifient une condition d'erreur (échecs rapportés par client, événements de retry visibles utilisateur, etc.) montent souvent pendant une fenêtre d'incident. Une baisse de ce count après livraison de la PR cible est un support circonstanciel que le code cible a résolu le symptôme visible par l'utilisateur, même quand le signal Datadog/Sentry est bruité.

Si tu trouves un lien d'incident, récupère le postmortem complet. Les postmortems ont typiquement une section "Actions à faire" qui lie directement les changements de code. Quand plusieurs sources corroborent (un ID d'incident Datadog apparaît dans un ticket Linear, qui apparaît dans un postmortem Notion, qui apparaît dans un thread Slack qui lie la PR cible, et le count d'événements d'erreur Databricks baisse après le fix), la preuve est particulièrement forte.

Cela vaut le temps quand le caractère défensif du code rend plausible une origine liée à incident. Saute-le pour du code qui ne semble pas défensif.

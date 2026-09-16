# Playbooks de sources

La skill why lance un enquêteur par catégorie de preuve disponible, chacun lisant un seul playbook spécifique à la source ci-dessous. Ce sont des exemples pour services connectés courants. Utilise seulement les outils exposés dans la session Codex courante, inspecte leurs schémas réels et adapte les requêtes à ce schéma. Un service nommé dans ce tableau ne prouve pas que son connecteur est installé.

| Catégorie | Playbook | MCP exemple documenté |
|---|---|---|
| Historique de contrôle source | [`code-archaeology.md`](./sources/code-archaeology.md) | git, `gh` |
| Issue / ticket tracker | [`linear.md`](./sources/linear.md) | Linear (adapter pour Jira, GitHub Issues, Plane, Shortcut) |
| Documents longs | [`notion.md`](./sources/notion.md) | Notion (adapter pour Confluence, Google Docs, Coda) |
| Chat d'équipe en temps réel | [`slack.md`](./sources/slack.md) | Slack (adapter pour Discord, Microsoft Teams, Mattermost) |
| Observabilité d'infrastructure | [`datadog.md`](./sources/datadog.md) | Datadog (adapter pour New Relic, Honeycomb, Grafana, Splunk) |
| Suivi d'erreurs / exceptions | [`sentry.md`](./sources/sentry.md) | Sentry (adapter pour Rollbar, Bugsnag, Airbrake) |
| Entrepôt d'analytique produit | [`databricks.md`](./sources/databricks.md) | Databricks SQL (adapter pour Snowflake, BigQuery, ClickHouse, dbt) |

Transversal :

- [`incident-postmortem.md`](./sources/incident-postmortem.md). Ajoute-le si le code cible semble défensif (null checks, retry, timeout, rate limit, feature flag, egress guard, handler OOM).

# Analytique Databricks et tables système

## Ce que cette source contient

Databricks est la couche d'analytique produit, pipeline de données et télémétrie warehouse. Elle complète Datadog. Datadog est la vue *infra/runtime*, Databricks est la vue *produit/données* : ce que les utilisateurs ont fait, quelles expériences ont tourné, comment l'usage des fonctionnalités a évolué, d'où vient une constante de seuil.

- **Événements d'analytique produit.** `your_warehouse.events.analytics_track_event` (brut) et modèles dbt typés, dédupliqués par événement dans `<your_analytics_db>.<schema>.<table>`. Comportement utilisateur : invocations de fonctionnalité, clics, acceptations/refus, soumissions, erreurs rapportées par client.
- **Événements d'usage et facturation.** `your_warehouse.events.usage_event` / `<your_analytics_db>.<schema>.stg_usage_events`, `your_warehouse.events.raw_model_event` / `<your_analytics_db>.<schema>.stg_raw_model_events`. Pour les décisions guidées par coût ou volume.
- **Données d'expérience / feature flag.** Tables d'exposition et de résultat. **Le schéma dépend de l'entreprise.** Sonde avec `SHOW TABLES` avant de supposer les noms.
- **Tables système.** `system.query.history`, `system.compute.warehouses`, `system.billing.*`, `system.access.audit`. Répond à "cette requête était-elle chère ?", "à quelle fréquence quelqu'un l'a lancée ?", "quand la charge du warehouse a-t-elle spiké ?"
- **Lignée dbt.** Les modèles dans `<your_analytics_db>.<schema>` révèlent quels pipelines dépendent d'une table/champ. Les changements amont motivent fréquemment des changements de code consommateur.
- **Notebooks Databricks.** Analyses exploratoires écrites par des ingénieurs avant des changements de code. **Non interrogeables via le MCP SQL.** Si tu suspectes que la justification vit dans un notebook, nomme-le comme écart.

## Comment la chercher

Utilise le MCP Databricks SQL. Outil principal : `execute_sql_read_only`. S'il retourne un `statement_id`, poll avec `poll_sql_result` plutôt que relancer.

**Oriente-toi avant d'interroger.** Les schémas dépendent de l'entreprise. Sonde avant de faire confiance à un nom de table :

```sql
SHOW TABLES IN <your_analytics_db>.<schema> LIKE '*<keyword>*';
DESCRIBE TABLE <your_analytics_db>.<schema>.stg_<event>;
```

**Borne chaque requête dans le temps.** Ces tables sont énormes et les scans non contraints expirent. Filtre sur `_timestamp` (events) ou `start_time` (`system.query.history`) avec une fenêtre autour de la date de livraison, typiquement environ 30 jours avant et après, plus large seulement avec bonne raison.

**Préfère les modèles dbt typés à la table brute.** `<your_analytics_db>.<schema>.<table>` est dédupliqué, typé et liquid-clustered. `your_warehouse.events.analytics_track_event` contient des doublons et un `properties_json` non typé. Motif de nom de modèle : `stg_<source>_<event_name_with_underscores>`, où `<source>` est `app`, `backend`, `website` ou `cli`. Confirme le nom exact avec `SHOW TABLES` quand le motif seul ne résout pas. Descends à la table brute seulement quand il n'y a pas encore de modèle dbt, ou si tu as besoin d'événements dans le délai de refresh dbt.

**Conventions de colonnes sur les modèles dbt typés** (les connaître évite un aller-retour `DESCRIBE`) :

- `_timestamp`, `_id`, `_auth_id`, `_request_id`, `event_name`. Standards sur chaque modèle
- `properties_<name>`. Propriétés d'événements typées et underscore-cased (`properties_entrypoint`, `properties_size_bytes`, ...)
- `context_team_id`, `context_client_version`, `context_country`, `context_client_os`. Contexte client pré-extrait

### Motifs d'enquête souvent rentables

Choisis la combinaison table + colonne qui correspond à la cible :

1. **Trajectoire d'usage d'événement.** Counts quotidiens sur le modèle `stg_*` pertinent sur une fenêtre ±30j autour du merge PR. Une marche de zéro vers un volume stable en un ou deux jours après le merge est une forte preuve circonstancielle que la PR a lancé la fonctionnalité. Une décroissance à zéro suggère une dépréciation ou suppression.
2. **Origine d'un garde-fou / check défensif.** Distribution (médiane / p99 / max) de la colonne `properties_<name>` pertinente dans les 14 jours *avant* la PR. Un p99 qui correspond à la constante de seuil cible suggère que le nombre vient des données.
3. **Recherche expérience / feature flag.** `SHOW TABLES ... LIKE '*experiment*'` pour trouver la table d'exposition, puis récupère les counts d'exposition par variant pour la clé de flag pertinente près de la date de PR.
4. **Preuve query-history pour migrations, backfills ou réécritures perf.** `system.query.history` filtré par `statement_text ILIKE '%<table_or_symbol>%'` avec une fenêtre `start_time` serrée fait émerger les requêtes coûteuses ayant probablement motivé le changement (trie par `total_duration_ms` ou agrège `SUM(read_bytes)`, `COUNT(*)`).
5. **Lignée dbt.** Si la cible lit ou écrit dans un modèle `<your_analytics_db>.<schema>`, l'historique git du modèle lui-même (dans ce dépôt) porte souvent la justification. Retourne ce lead à l'enquêteur git au lieu de le poursuivre toi-même.

## À quoi ressemble une bonne preuve ici

Au-delà des formes de motifs ci-dessus :

- Le count d'un événement de classification d'erreur tombe presque à zéro dans les jours suivant une PR de code défensif. Cela suggère que la PR a résolu cette classe d'erreur
- Une ligne de table d'exposition nomme la clé de feature flag cible avec une décision "shipped" / "concluded" autour de la date de livraison PR

## Pièges courants

- **Instrumenté ne veut pas dire causé.** L'existence d'un événement signifie que quelqu'un se souciait assez pour le logger, pas que le code cible existe *à cause* de lui. Associe-le à une citation PR/commit de l'enquêteur git avant d'affirmer la causalité.
- **Changements silencieux d'instrumentation.** Une marche dans le volume d'événements peut signifier qu'un nouvel événement a commencé à être loggé, pas que le comportement utilisateur a changé. Vérifie les PR d'instrumentation dans la même fenêtre avant de lire la rampe comme signal de lancement de fonctionnalité.
- **Dérive de schéma.** Les propriétés d'événements évoluent. Une colonne sur le modèle dbt typé aujourd'hui peut ne pas avoir existé au moment où la cible a été écrite. Les données anciennes peuvent porter la propriété seulement dans `properties_json` brut.
- **Délai de refresh dbt.** `<your_analytics_db>.<schema>.*` est reconstruit selon un horaire (souvent horaire/quotidien). Pour les événements des dernières heures, replie-toi sur `your_warehouse.events.*` et déduplique par `_id`.
- **Tables propres à l'entreprise.** Les tables expérience, feature flag, facturation et usage varient. Rapporter un résultat d'une table dont tu n'as jamais confirmé l'existence est un mode d'échec classique. Sonde d'abord avec `SHOW TABLES` / `DESCRIBE TABLE`.
- **Falaise de rétention.** Si la fenêtre pertinente précède la rétention de la table ou la date de création du modèle dbt, c'est un *écart*, pas un résultat nul. Nomme-le explicitement pour que le synthétiseur ne lise pas "pas de résultats" comme "pas d'activité".
- **Les notebooks ne sont pas interrogeables.** Le MCP SQL ne voit pas les notebooks Databricks. Si tu suspectes que la justification vit dans l'un d'eux, retourne un écart.

## Quoi retourner

Pour chaque finding pertinente :
- Type (événement produit / exposition d'expérience / événement usage ou facturation / ligne de table système / modèle dbt)
- Nom de table fully-qualified et requête exacte lancée
- Fenêtre temporelle interrogée
- Résumé numérique compact (counts, percentiles, timestamps first/last-seen). **Ne dump pas les lignes brutes.**
- Corrélation temporelle avec la date de livraison de la cible (p. ex. "première ligne 2024-08-15, PR #49074 mergée 2024-08-14")
- Pertinence + force : directe / circonstancielle / faible

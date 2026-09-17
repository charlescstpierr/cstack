# Télémétrie Datadog

## Ce que cette source contient

Datadog contient l'enregistrement runtime, ce qui s'est réellement passé en production, par opposition à ce qui était planifié ou discuté.

- **Metrics.** Counters, gauges, histograms instrumentés par l'équipe. La *présence* d'une métrique est elle-même une preuve. Quelqu'un a jugé ce nombre digne d'être observé.
- **Monitors & alerts.** Conditions que l'équipe a jugées assez importantes pour réveiller quelqu'un. Un monitor qui fire sur `rate_limit_hit > 10/min` est une preuve directe que l'équipe se souciait de ce seuil.
- **Dashboards.** Vues curées. Les graphiques disent ce que l'équipe considère important pour un sous-système.
- **APM traces & spans.** Données runtime par requête. Utile pour les questions "pourquoi est-ce lent" / "pourquoi ce timeout ici".
- **Logs.** Enregistrements d'événements à grand volume. Contiennent souvent les conditions d'erreur qui ont motivé du code défensif.
- **Incidents.** Dossiers d'incidents formels avec timelines et postmortems liés.
- **Notebooks.** Investigations exploratoires. Contiennent souvent hypothèses et analyses.

Datadog répond à "quelle était la réalité production autour du moment où ce code a été écrit ?", ce qui explique souvent la forme du code.

## Comment la chercher

Utilise le MCP Datadog. Commence large, puis rétrécis.

1. **Identifier les services propriétaires.**

   ```
   search_datadog_services (filtrer par nom ou équipe)
   search_datadog_service_dependencies (voir amont/aval)
   ```

2. **Dashboards et monitors d'abord. Ils disent ce qui compte pour l'équipe.**

   ```
   search_datadog_dashboards (requête : nom de fonctionnalité, nom de service, symbole)
   search_datadog_monitors   (mêmes requêtes)
   ```

   Quand un dashboard ou monitor couvre la cible, note ses requêtes et seuils surveillés. Le seuil est fréquemment la réponse à "pourquoi ce clamp à N ?"

3. **Métriques autour de la cible.**

   ```
   search_datadog_metrics (by name pattern, e.g., the feature or symbol)
   get_datadog_metric_context (metadata: description, units, tags)
   get_datadog_metric (timeseries; "y a-t-il eu un pic autour de la date de PR ?")
   ```

   Corréler la trajectoire d'une métrique avec la date d'ajout/changement de la cible est une preuve de support forte : "la métrique `payment_timeout` a spiké le 2023-11-03, et la logique de retry a merge le 2023-11-06."

4. **Logs. Rétrécis, ne dump pas.**

   ```
   search_datadog_logs (motifs de logs bruts près de la cible, définir use_log_patterns=true)
   analyze_datadog_logs (agrégations de type SQL, seulement quand tu as besoin de décomptes)
   ```

   Cherche avec symboles, chaînes d'erreur ou noms de fonctionnalités. **Préfère fortement les requêtes bornées dans le temps** (p. ex. 30 jours avant/après le changement). Le volume de logs est énorme. Les recherches non bornées gaspillent du temps et peuvent time out.

5. **Spans et traces APM.**

   ```
   aggregate_spans    (stats: "à quelle fréquence cet endpoint échoue-t-il ?")
   search_datadog_spans (inspect individual spans)
   get_datadog_trace  (a specific trace ID)
   ```

   Utile pour timeouts, retries, chemins lents et comportement cross-service.

6. **Incidents.**

   ```
   search_datadog_incidents (by title, team, date range)
   get_datadog_incident     (full detail for a specific incident)
   ```

   Si la cible semble défensive, cherche des incidents autour de sa date d'ajout. Un incident dont la timeline inclut "ajout d'un check défensif pour X" est une preuve quasi directe.

## À quoi ressemble une bonne preuve ici

- Un monitor dont la requête et le seuil correspondent à la contrainte appliquée par le code (le code clamp à 100, le monitor alerte quand les requêtes dépassent 100/min)
- Un dashboard créé par l'auteur de la cible, avec widgets correspondant à ce que le code mesure ou protège
- Une métrique montrant un spike production juste avant le merge du code, puis des valeurs stables après
- Un dossier d'incident qui référence le code cible, les mêmes symboles ou les mêmes chaînes d'erreur
- Des logs montrant un motif d'erreur précis que le code défensif empêcherait, timestampé dans la fenêtre avant le changement

## Pièges courants

- **Corrélation n'est pas causalité.** Un spike avant une PR puis stabilisation après est suggestif, pas définitif. D'autres changements ont pu arriver dans la même fenêtre. Vérifie les PR voisines.
- **Surajustement au graphique trouvé.** Les visualisations Datadog sont *faites* par des humains et reflètent leur cadrage. Un graphique nommé "retry success rate" prouve que l'équipe se souciait du succès des retries, pas que c'est pourquoi une ligne précise existe.
- **Télémétrie disparue.** Les métriques peuvent être renommées, supprimées ou avoir une rétention courte. Si tu ne trouves pas de données de la fenêtre pertinente, c'est un écart, pas un résultat nul.
- **Bruit à l'échelle.** Chercher une chaîne courante dans les logs retourne des milliers de résultats. Rétrécis agressivement par service, tag et temps. Utilise `analyze_datadog_logs` pour agréger plutôt que dumper les logs bruts.
- **Instrumenté != causé.** L'existence d'une métrique dit que quelqu'un se souciait assez pour mesurer, pas que le code a été ajouté *à cause* d'elle. Croise avec les dates de commit/PR.

## Quoi retourner

Pour chaque élément pertinent :
- Type (dashboard / monitor / metric / log pattern / trace / incident / notebook)
- Titre ou nom
- Lien ou identifiant (dashboard ID, monitor ID, nom de métrique, incident ID)
- Owner/auteur et date de création/modification
- La condition, requête ou citation précise qui pèse sur la question (verbatim quand possible)
- Pertinence : ce que cela suggère sur le code cible, et force du lien

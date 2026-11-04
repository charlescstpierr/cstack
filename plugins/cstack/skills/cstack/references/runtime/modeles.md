# Modèles

Dans une tâche cstack explicitement invoquée dans T3, le [contrat T3](t3.md) prime sur les règles autonomes de ce document.


La session parent garde son propre modèle. Les délégués natifs héritent du modèle et de l’effort sauf si l’utilisateur sélectionne une surcharge de projet. Un worker CLI sans modèle explicite utilise le défaut de son propre CLI, jamais le modèle du parent. Le setup offre des recommandations optionnelles, jamais des noms de modèles, fournisseurs, plans, clés API ou rôles custom globaux obligatoires.

`.cstack/models.json` mappe les libellés de rôle de la compétence setup vers des chaînes de modèle legacy, `inherit-parent` ou des objets avec exactement `model` et `reasoning_effort`. Une sélection CLI est `{ "runtime": "codex-cli|claude-code|cursor-agent|grok", "model": "...", "reasoning_effort": "..." }`, où les deux derniers champs sont facultatifs ; un effort exige un modèle explicite. `inherit-parent` reste réservé au chemin natif. Les panels sont des listes non vides de ces sélections. `simple edits` manquant retombe sur `feature, refactoring` ; `documentation` manquant retombe sur `judgment and prose`. Les autres rôles manquants héritent. Les panels manquants valent par défaut trois tentatives, sauf `arena cross-judge pool` qui vaut par défaut un juge. `architect runners` exige au moins deux entrées. Mets en file les tentatives au-delà de la concurrence native ; ne revendique pas de diversité de modèles depuis des passes indépendantes sur un seul modèle.

Quand `.cstack/models.json` est absent et que l’appelant n’a fourni aucune surcharge, hérite directement avec les défauts de panel ci-dessus ; aucun helper, Python ou découverte de modèles n’est nécessaire. Avec une configuration présente, résous le rôle avec le helper installé de confiance. Découvre le catalogue depuis le schéma d’outil courant ou la liste de modèles de session faisant autorité une fois par tâche et réutilise-le tant que les capacités de session restent inchangées :

```sh
python3 <absolute-plugin>/skills/setup-cstack/scripts/models.py --workspace <workspace> --catalog <live-catalog.json> resolve '<role>'
```

Les formats de catalogue sont documentés dans [setup-cstack](../../../setup-cstack/SKILL.md) ; ne code jamais en dur un nom de modèle. Pour le chemin natif, le résultat est une liste de sélections natives : `{}` pour l’héritage, `{ "model": "..." }` pour une chaîne legacy, ou `{ "model": "...", "reasoning_effort": "..." }` pour une paire explicite. Les sélections CLI conservent aussi `runtime` et passent au helper CLI. Transmets chaque sélection complète à travers chaque appelant, panel et lancement final. Les chaînes legacy laissent l’effort aux règles de l’hôte ; n’invente jamais un effort pour elles. Un rôle ou panel spécialisé explicitement fourni prend priorité sur les défauts génériques de Swarm ou Arena.

## Contrôle préalable du workflow

Après le routage, vérifie ensemble les rôles déjà nécessaires, y compris la revue prévue, avant les écritures d’implémentation qui en dépendent. Le contrôle utilise le même catalogue courant et les mêmes règles que `resolve` ; il préserve les choix et les panels. Avec une configuration sauvegardée, lance :

```sh
python3 <absolute-plugin>/skills/setup-cstack/scripts/models.py --workspace <workspace> --catalog <live-catalog.json> preflight 'how explorer' 'judgment and prose'
```

Cet exemple vérifie deux rôles, pas une liste obligatoire : passe les rôles du parcours réel. Un rôle conditionnel découvert plus tard est vérifié avant son travail dépendant ; un rôle inutilisé ne bloque pas la tâche. `ready` retourne les sélections résolues et le code 0. `blocked` retourne les rôles indisponibles dans `errors` et le code 2, sans substitution, écriture, login ni génération. Continue seulement le travail indépendant d’un rôle bloqué. Sans configuration ni surcharge, l’héritage direct reste possible sans ce helper ni catalogue.

`ready` vérifie les sélections contre le catalogue fourni. Il ne prouve ni la connexion d’un CLI ni la capacité du schéma de lancement à exprimer le modèle et l’effort : ces contrôles restent requis ci-dessous.

Inspecte le vrai schéma de lancement avant d’appliquer des surcharges. En collaboration App native, utilise un type d’agent générique disponible dont les paramètres ne sont pas verrouillés, et `fork_turns: "none"` ou un fork partiel pris en charge quand tu fournis `model` ou `reasoning_effort` ; les forks d’historique complet ne peuvent pas prendre ces surcharges. Fournis explicitement le contexte nécessaire. Les autres hôtes, y compris CLI, doivent exposer une vraie manière de configurer les champs sélectionnés. Si un effort explicite ne peut pas être exprimé, rapporte cet écart de capacité et demande une sélection prise en charge ou la permission d’hériter. Le texte de prompt n’est pas une configuration de modèle. N’abandonne jamais silencieusement l’effort, n’hérite pas et ne substitue pas un modèle demandé. L’héritage utilise le comportement normal de fork de l’hôte.

Utilise seulement des paires modèle/effort confirmées disponibles maintenant ; un cache périmé ou un choix sauvegardé ne prouve pas le droit d’usage. Une configuration mal formée, des choix explicites inconnus et des dispatchs rejetés sont des erreurs à rapporter, pas une permission d’ignorer une surcharge. Continue le travail indépendant pendant qu’une sélection est bloquée. Sans découverte, l’héritage fonctionne quand même. Le setup ne lance pas de tests de modèle et ne modifie pas la configuration globale.

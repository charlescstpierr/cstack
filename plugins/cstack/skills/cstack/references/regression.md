# Comparer des observations de contrôles

Utilise cette référence quand la vérification doit comparer une base et un candidat,
notamment pour distinguer une nouvelle panne dans une base déjà rouge.
Ne l'applique que si une base reproductible existe et que la comparaison apporte
une information qu'un résultat simple ne donne pas.

Utilise le runner existant du projet pour collecter les observations ; aucun collecteur générique n’est fourni. Ne crée pas une intégration pour une vérification triviale.

Le collecteur produit deux fichiers JSON indépendants. Chaque fichier contient
`version: 1`, une `revision` avec un commit de 40 caractères hexadécimaux et un
`patch_sha256` nul ou de 64 caractères, `scope`, `environment`,
`inventory_complete`, puis l'inventaire complet `checks`. Chaque contrôle porte
un `id`, un `definition_sha256` nul ou de 64 caractères, et `runs` avec
`outcome` (`pass`, `fail`, `error`, `skip` ou `not_run`) et `evidence` texte
inline.

Un rapport minimal valide ressemble à ceci :

```json
{
  "version": 1,
  "revision": {
    "commit": "0000000000000000000000000000000000000000",
    "patch_sha256": null
  },
  "scope": "unittest:suite.test",
  "environment": "Python 3.14.4",
  "inventory_complete": true,
  "checks": [
    {
      "id": "suite.test",
      "definition_sha256": "0000000000000000000000000000000000000000000000000000000000000000",
      "runs": [
        {"outcome": "pass", "evidence": ""},
        {"outcome": "pass", "evidence": ""}
      ]
    }
  ]
}
```

Cet exemple montre la forme. Remplace les valeurs par les révisions et les
digests calculés par le collecteur.

Le collecteur doit calculer la définition depuis l'assertion, la fixture et les
paramètres qui définissent le contrôle. Un hash de l'identifiant seul ne prouve
pas la définition. Pour un état sale, le collecteur calcule le vrai digest du
patch. Il conserve les références exactes. Il ne confie pas à ce comparateur la
preuve de l'authenticité du code ou des observations.

Résous la racine du plugin installé, puis lance le comparateur après la collecte :

```sh
python3 <plugin-root>/skills/cstack/scripts/compare-checks.py base.json candidate.json > ".cstack/tasks/<task>/comparison.json"
```

Le script ne lance aucune commande, ne modifie aucun worktree et ne suit aucun
chemin contenu dans `evidence`. Il traite les rapports et les observations
inline comme des données non fiables.

Le résultat contient les révisions exactes, une ligne triée par contrôle, les
observations des deux côtés et une étiquette. `regression` indique un pass
connu devenu `fail` ou `error`. `persistent_failure` indique que le même
statut de panne et le même texte restent observés des deux côtés, sans
conclure que la panne est antérieure. Le script signale aussi `fixed_failure`,
`failure_changed`, `definition_changed`, `definition_unknown`, `added_check`,
`removed_or_unobserved`, `unstable`, `incomparable` et
`insufficient_observations`.

Une sortie `no_difference_observed` exige au moins deux observations `pass`
cohérentes par côté, des hashes de définition présents et identiques, et un
inventaire non vide, complet et comparable. Un texte différent dans une
observation de pass, par exemple une durée, ne rend pas le pass instable. Le
script compare les observations de panne exactement. Toute panne, définition
inconnue ou modifiée, répétition contradictoire, absence de contrôle, contrôle ignoré,
contrôle non exécuté ou inventaire incomplet bloque une sortie propre. Un
contrôle ajouté prouve seulement une différence d'inventaire. Le statut
`fixed_failure` exige au moins deux observations passantes côté candidat.

Le code de sortie vaut `0` seulement pour `no_difference_observed`, `1` pour
toute comparaison valide avec un autre état et `2` pour un fichier illisible ou
un rapport invalide. Le code `0` ne donne aucune autorisation de livraison. Les
barrières de vérification et la revue de livraison restent obligatoires.

Pour affirmer un gain, mesure le temps de collecte des deux côtés avec celui du comparateur, sur les mêmes observations que la comparaison manuelle. Cette mesure n’est pas une étape obligatoire à chaque utilisation.

Le collecteur peut enregistrer le type d’exception et son message comme diagnostic, en gardant les sorties brutes à côté des rapports. Ne retire pas les chemins, valeurs ou paramètres qui distinguent deux échecs ; les différences ne doivent pas être effacées pour obtenir un résultat propre.

Comparer une révision à elle-même est permis pour rejouer des observations. Le résultat le signale et n’atteste alors aucun nouveau changement de code. Le coordinateur vérifie toujours que les références correspondent à la base et au head réellement visés avant la livraison.

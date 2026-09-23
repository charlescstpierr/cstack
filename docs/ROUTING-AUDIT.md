# Audit du routage de cstack

Ce document décrit une mesure du routage de cstack, ses résultats et ses limites. Il enregistre des constats à instruire, pas des corrections appliquées. Aucun skill, playbook ni routeur n'est modifié par ce travail ; le seul changement de code est l'ajout de scénarios de routage au générateur de cas existant.

## Ce qu'on appelle ici le routage

Quatre décisions distinctes acheminent une tâche dans cstack. Les nommer séparément évite de confondre un défaut de l'une avec un défaut d'une autre.

| Couche | Décision | Où elle vit |
| --- | --- | --- |
| 0 | Le skill se déclenche-t-il ? | `agents/openai.yaml`, `policy.allow_implicit_invocation` |
| 1 | Quel playbook ? | `skills/cstack/SKILL.md`, section "Exécuter le playbook correspondant" |
| 2 | Quels principles et skills auxiliaires ? | `skills/cstack/SKILL.md`, sections communes, plus les appels internes aux playbooks |
| 3 | Quel rôle, donc quel modèle ? | `.cstack/models.json` dans le projet de scénario |

La couche 0 est fermée mécaniquement : les 29 skills distribués portent `allow_implicit_invocation: false`. Les 23 principles ne sont pas des skills d'entrée ; ils vivent sous `skills/cstack/references/principles/*.md`. Les couches 1 et 2 restent une classification en langage naturel effectuée par le modèle à la lecture du routeur.

## Méthode

Huit tâches formulées comme des demandes ordinaires ont été confiées à des agents séparés, chacun dans une copie isolée de l'arbre de skills, sans qu'aucun sache qu'une mesure avait lieu. L'observable visé est la liste des fichiers réellement ouverts : quels `SKILL.md`, playbooks et références de principles ont été lus pendant le tour. Aucune auto-déclaration n'a été demandée, conformément à `playbooks/eval.md`, qui interdit de demander au sujet la liste des skills qu'il a appliqués. Les attentes étaient écrites avant l'exécution.

Un second passage a inversé le contenu de quatre principles, en conservant leurs conditions de déclenchement intactes pour que le routage reste identique, afin de distinguer un fichier qui oriente réellement la décision d'un fichier que le système contourne.

## Limites de cette mesure

Elles sont importantes et conditionnent toute lecture des résultats.

- **L'hôte n'était pas Codex.** Les agents utilisés proviennent d'un autre environnement. La mesure décrit la lisibilité du routeur pour un agent capable, pas le comportement de cstack en production. C'est la raison d'être des scénarios ajoutés ici : les rejouer sur le vrai Codex.
- **Une seule passe par cas.** Aucune estimation de variance. Un déclenchement observé une fois ne prouve pas un taux.
- **Un cas perdu sur huit** pour la couche 2 : ses lectures sont survenues pendant un balayage `grep` de masse et n'ont pas pu être séparées des lectures délibérées.
- **La grille d'attentes était trop stricte au moins une fois.** `principle-fix-root-causes` a été compté comme excédentaire sur une correction de faute d'orthographe, alors que le routeur dit "for a defect" et que le déclenchement est donc légitime.
- **L'atime n'est pas une preuve fiable.** `relatime`, `noatime`, les caches et les lectures de masse peuvent masquer ou mélanger les accès. Les scénarios ci-dessous demandent un traçage explicite des ouvertures de fichiers ; `verify-behavior.py` ne le fait pas encore seul.

## Résultats

### Couche 1, huit sur huit

Chacune des huit tâches a atteint le playbook correct. Le cas le plus informatif est une demande de diagnostic à partir d'une capture existante, qui a atteint `trace-forensics.md` et non `runtime-forensics.md`. C'est précisément la paire que `trace-forensics.md` sépare par sa phrase "Distinct from Runtime forensics, which instruments the live process". La technique des clauses d'exclusion mutuelle employée dans les playbooks fonctionne.

### Couche 2, rappel d'environ 79 %

Onze déclenchements attendus sur quatorze, sur les sept cas exploitables. En moyenne 4,1 principles chargés par tâche sur une trentaine de candidats : la dispersion redoutée ne s'est pas produite. Le trigger le plus étroit de l'ensemble, `principle-attack-the-premise`, s'est déclenché et a changé le résultat, l'agent refusant un troisième correctif pour construire un recensement.

Trois manques observés :

- `principle-foundational-thinking` n'a pas été atteint sur une tâche de conception de type, au profit de `principle-type-system-discipline`. Les deux conditions se recouvrent presque entièrement ; la plus spécifique l'emporte et l'autre est abandonnée.
- `principle-prove-it-works` n'a pas été ouvert sur une correction de défaut, bien que l'agent ait construit un harnais de vérification rejouable.
- `principle-fix-root-causes` n'a pas été ouvert sur un diagnostic, bien que l'agent l'ait cité.

### Les principles sont cités sans être lus

Sur deux cas nettement établis, l'agent nomme un principle dans ses notes alors que le fichier n'a jamais été ouvert. La ligne de résumé du routeur suffit à produire la citation. Ce constat est invisible si l'on interroge l'agent sur ce qu'il a appliqué.

Conséquence à instruire : pour une partie des entrées de la couche 2, il reste à établir si le fichier apporte quelque chose au-delà de sa ligne de résumé.

### La redondance absorbe la corruption d'un fichier

Quatre principles ont été inversés, un par tâche. Trois inversions ont été effectivement lues ; la quatrième n'a jamais été ouverte, donc non livrée.

**Aucune des trois inversions livrées n'a fait basculer le comportement.** Dans les trois cas, l'agent a détecté la contradiction et l'a signalée sans qu'on le lui demande. Sur `principle-attack-the-premise` inversé, l'agent a construit un banc comparant les stratégies, montré que la direction recommandée par le fichier corrompu échouait, puis suivi `playbooks/bug-fix.md` et `principle-fix-root-causes` à la place.

L'interprétation qui compte : le comportement est porté par plusieurs sources à la fois, le playbook, les principles voisins et les réflexes du modèle. C'est de la tolérance aux pannes, et c'est une propriété à préserver.

Deux conséquences directes :

1. **Ce résultat n'autorise aucune suppression.** Un fichier dont l'inversion ne change rien n'est pas inutile : il n'a pas basculé grâce à la redondance. Retirer assez de nœuds redondants déplacerait le point de rupture.
2. **Une éval comportementale est un mauvais portail pour le routage.** Si le comportement est surdéterminé, une erreur de routage ne se voit pas dans la sortie. Mesurer le routage demande d'observer la décision, pas son effet.

## Décisions ouvertes

Aucune n'est tranchée ici.

### 1. `principle-laziness-protocol` se comporte comme un défaut

Ouvert dans cinq des sept cas exploitables, dont une correction d'un mot et un ajout de couverture. Sa condition, "before a refactor or a new abstraction", est assez large pour être lue comme toujours applicable. Le scénario `routing_one_word_user_string` encode ce constat sous forme de route interdite vers `skills/cstack/references/principles/laziness-protocol.md`. Il n'interdit pas `skills/how/SKILL.md`, car `bug-fix.md` peut légitimement l'appliquer pendant le diagnostic.

### 2. Les phrases de déclenchement des descriptions ne sont lues par personne

De nombreuses descriptions contiennent des amorces en langage naturel du type "arena this", "swarm this", "catch me up". Elles n'ont de sens que pour un hôte qui fait du rapprochement automatique. Avec `allow_implicit_invocation: false` partout, rien ne les consulte. Héritage du portage, sans effet aujourd'hui, mais elles deviendraient la surface de routage principale si la politique changeait.

### 3. Les skills utilitaires restent à classer un par un

Des skills comme `automate-me`, `bro`, `create-verification-skill`, `maintain-verification-skill` et `make-bot-ui` restent principalement des utilitaires appelés à la demande. D'autres cas autrefois suspects sont désormais câblés dans le routeur : `typescript-best-practices`, `teach`, `reflect` et `blast-radius` sont référencés par `skills/cstack/SKILL.md`, et `recall` est appelé depuis `playbooks/session-pickup.md`.

## Rejouer la mesure sur Codex

Quatre scénarios sont ajoutés à `scripts/behavior-scenarios.py`. Ils suivent le format existant et se lancent avec le harnais existant :

```sh
codex debug models > /tmp/cstack-model-catalog.json
python3 - /tmp/cstack-model-catalog.json <<'PY'
import json, sys

catalog = json.load(open(sys.argv[1], encoding="utf-8"))

def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)

for item in walk(catalog):
    names = {str(item.get(key, "")) for key in ("id", "name", "model")}
    if "gpt-5.6-luna" in names and "max" in json.dumps(item).lower():
        raise SystemExit(0)
raise SystemExit("catalogue Codex sans paire gpt-5.6-luna + max ; arrêt fail-closed")
PY
python3 scripts/behavior-scenarios.py --baseline /chemin/plugin-precedent --proposed /chemin/plugin-courant --catalog /tmp/cstack-model-catalog.json --output /tmp/cstack-cases
python3 scripts/verify-behavior.py --cases /tmp/cstack-cases/cases.json --output /tmp/cstack-results --model gpt-5.6-luna --effort max --turn-timeout 900
```

Pour ne rejouer que le routage, restreindre `verify-behavior.py` avec `--case-id` :

| Cas | Ce qu'il mesure |
| --- | --- |
| `routing_one_word_user_string` | Précision. Une correction d'un mot ne doit pas charger `skills/cstack/references/principles/laziness-protocol.md`. |
| `routing_typed_external_boundary` | Rappel dans la zone de recouvrement la plus dense : les principles de type, frontière et pensée fondationnelle. |
| `routing_internal_api_replacement` | Le cluster migration : `skills/cstack/references/principles/migrate-callers-then-delete-legacy-apis.md` doit être atteint parmi ses voisins. |
| `routing_live_process_diagnosis` | La direction non mesurée de la paire forensics : un processus vivant doit atteindre `runtime-forensics.md`, pas `trace-forensics.md`. |

`expectations.json` porte désormais un bloc `routing` pour ces cas, avec `expected` et `forbidden` exprimés en chemins relatifs à la racine du bundle. Le générateur refuse une route inexistante ou présente dans les deux listes. Ces cas se jugent sur les routes empruntées, pas sur le nombre d'enfants : ils omettent donc `expected_children`.

Leurs fixtures sont réduites au strict nécessaire pour poser la question de routage. Un agent peut donc emprunter la bonne route puis signaler qu'il ne peut pas mener la tâche à terme, faute de processus vivant ou de dépôt complet. Ce n'est pas un échec du cas : le routage précède la découverte de cette limite.

Le harnais ne capture pas encore les routes effectivement empruntées. Sur Linux, une exécution reproductible peut tracer les ouvertures de fichiers avec `strace` :

```sh
strace -ff -e trace=openat,openat2 -s 240 -o /tmp/cstack-route-open \
  python3 scripts/verify-behavior.py --cases /tmp/cstack-cases/cases.json --case-id routing_one_word_user_string --output /tmp/cstack-results-routing-one-word --model gpt-5.6-luna --effort max --turn-timeout 900
rg 'skills/(cstack/playbooks|cstack/references/principles|how/SKILL.md)' /tmp/cstack-route-open.*
```

Cette trace reste une preuve externe à comparer au bloc `routing`. Le travail restant est d'intégrer une capture équivalente dans le harnais et de comparer automatiquement les routes ouvertes aux attentes.

## Ce qui reste à faire

- Rejouer les quatre scénarios sur Codex, avec plusieurs passages par cas, pour obtenir des taux plutôt que des observations uniques.
- Instrumenter `verify-behavior.py` pour tracer les ouvertures de fichiers, enregistrer les routes empruntées et comparer au bloc `routing`.
- Trancher les décisions ouvertes ci-dessus.
- Étendre la couverture aux paires confusables non encore mesurées : `principle-subtract-before-you-add` contre `principle-outcome-oriented-execution`, et `playbooks/perf-issue.md` contre `playbooks/hillclimb.md`.
- Mesurer le point de rupture de la redondance en inversant un groupe entier de principles voisins plutôt qu'un seul fichier.

## Instrumentation expérimentale des routes

Le générateur contient désormais 17 scénarios de routing parmi 32 scénarios au total. Le runner accepte `--repeats 5`, qui copie chaque projet dans un dossier distinct, et `--trace-routes --expectations <fichier>` sous Linux quand l'hôte autorise `ptrace`. Chaque résultat distingue les chemins ouverts, les lectures accompagnées d'une commande simple et les ouvertures sans attribution. Une ouverture pendant un balayage de masse ou un bundle CLI transitif est `unknown`, pas un vrai positif ni un faux positif. La corrélation commande/ouverture n'est pas horodatée : même la catégorie de lecture directe reste une preuve indicative, pas une preuve que le modèle a appliqué la skill. Les autres champs du résultat conservent les dispatchs natifs, les commandes et les métadonnées de rôle; les skips, phases et verdicts de revue nécessitent encore une observation structurée supplémentaire.

Exemple après génération de `cases.json` et `expectations.json` :

```sh
python3 scripts/verify-behavior.py --cases /tmp/cstack-cases/cases.json \
  --expectations /tmp/cstack-cases/expectations.json --trace-routes --repeats 5 \
  --output /tmp/cstack-routing-runs --case-id routing_competing_feature_shapes
```

La trace échoue explicitement si `strace` manque ou si `ptrace` est refusé. Aucun nouveau taux de rappel, précision, variance ou avantage de design n'est déduit des seuls tests unitaires du parseur. Les scénarios supplémentaires couvrent des contrastes utiles, mais le harnais ne réalise pas encore un A/B/C natif ni une comparaison Poteto sur la même plate-forme.

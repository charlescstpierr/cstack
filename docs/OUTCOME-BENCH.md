# Banc de résultat : Codex seul contre cstack

Ce banc répond à une seule question : sur des correctifs open source réels, `$cstack:cstack` résout-il plus de tâches que Codex seul, et à quel coût ? Il complète la mesure du routage de #1 et de la PR 43, qui observe les lectures et délégations, pas le résultat.

## Principe

- **Tâches** : correctifs fusionnés après la date plancher de `evals/outcome/suite.json`, pour limiter la contamination. Chaque dossier `evals/outcome/tasks/<id>/` contient `task.json` et un `Dockerfile` figé.
- **Bras** : `vanilla` reçoit la demande du ticket et la limite de portée locale. `cstack` reçoit le `default_prompt` de la compétence, la même demande et le chemin de la source cstack copiée dans la campagne. Même modèle, même effort, même sandbox.
- **Espace de travail** : checkout neuf au commit de base, avec son historique mais sans aucun objet du correctif ni remote.
- **Notation** : le diff de l’agent est appliqué sur une copie propre de la base, puis les `hidden_paths` du correctif l’écrasent. Les commandes `fail_to_pass` et `pass_to_pass` s’exécutent dans l’image de la tâche, sans réseau. Un run est résolu si toutes passent.
- **Ordre** : tâches, bras et répétitions entrelacés par une graine enregistrée dans le manifeste.

## Commandes

Depuis la racine du dépôt, avec Docker, Git et Codex CLI authentifié :

```sh
python3 scripts/outcome-bench.py validate
python3 scripts/outcome-bench.py run --output .cstack/outcome-runs/<campagne> --seed <n> --model <modèle> --effort <effort>
python3 scripts/outcome-bench.py report --output .cstack/outcome-runs/<campagne>
```

`validate` n’appelle aucun modèle : pour chaque tâche, les tests `fail_to_pass` échouent sur la base avec les tests cachés, tous passent avec le correctif et les `pass_to_pass` passent sur la base. Son reçu, lié à l’empreinte de la tâche, est exigé par `run`. Une campagne interrompue reprend avec la même commande ; un manifeste différent est refusé.

## Mesures

`summary.json` donne par bras le taux de résolution, les `infra_error` exclus des dénominateurs, les `needs_input`, la médiane des tokens et leur couverture, les tokens par tâche résolue, la durée, le nombre moyen de sous-agents, la taille des diffs et les runs qui ont touché les chemins cachés. Il compare aussi les bras tâche par tâche.

## Limites

Dix tâches et trois répétitions ne détectent qu’un écart large et cohérent. Les tokens dépendent des métadonnées natives exposées ; `tokens_source` indique leur origine. Le bras cstack lit la source copiée au lieu du plugin installé, comme `scripts/behavior-scenarios.py`. Aucun résultat n’est revendiqué tant qu’une campagne réelle n’a pas été exécutée.

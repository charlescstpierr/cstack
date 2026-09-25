# Banc de résultat : Codex seul, cstack et pstack

Ce banc répond à deux questions : sur des correctifs open source réels, `$cstack:cstack` résout-il plus de tâches que Codex seul, et à quel coût ? Et le portage fait-il mieux, dans Codex, que la source pstack non adaptée ? Il complète la mesure du routage de #1 et de la PR 43, qui observe les lectures et délégations, pas le résultat.

## Principe

- **Tâches** : correctifs fusionnés après la date plancher de `evals/outcome/suite.json`, pour limiter la contamination. Chaque dossier `evals/outcome/tasks/<id>/` contient `task.json` et un `Dockerfile` figé.
- **Bras** : `vanilla` reçoit la demande du ticket et la limite de portée locale. `cstack` reçoit le `default_prompt` de la compétence, la même demande et le chemin de la source cstack copiée dans la campagne. `pstack`, facultatif, reçoit une demande anglaise équivalente de mode poteto et de délégation, la même demande et le chemin de `poteto-mode/SKILL.md` au commit épinglé de `UPSTREAM.json`. Même modèle, même effort, même sandbox. `--arms` choisit les bras, `vanilla,cstack` par défaut.
- **Espace de travail** : checkout neuf au commit de base, avec son historique mais sans aucun objet du correctif ni remote.
- **Notation** : le diff de l’agent est appliqué sur une copie propre de la base, puis les `hidden_paths` du correctif l’écrasent. Les commandes `fail_to_pass` et `pass_to_pass` s’exécutent dans l’image de la tâche, sans réseau. Un run est résolu si toutes passent.
- **Ordre** : tâches, bras et répétitions entrelacés par une graine enregistrée dans le manifeste.

## Commandes

Depuis la racine du dépôt, avec Docker, Git et Codex CLI authentifié :

```sh
python3 scripts/outcome-bench.py validate
python3 scripts/outcome-bench.py fetch-pstack   # seulement pour le bras pstack
python3 scripts/outcome-bench.py run --output .cstack/outcome-runs/<campagne> --seed <n> --model <modèle> --effort <effort> [--arms vanilla,cstack,pstack]
python3 scripts/outcome-bench.py report --output .cstack/outcome-runs/<campagne>
```

`fetch-pstack` récupère `cursor/plugins` au commit épinglé et refuse le checkout si un seul blob diffère de l’inventaire. `validate` n’appelle aucun modèle : pour chaque tâche, les tests `fail_to_pass` échouent sur la base avec les tests cachés, tous passent avec le correctif et les `pass_to_pass` passent sur la base. Son reçu, lié à l’empreinte de la tâche, est exigé par `run`. Une campagne interrompue reprend avec la même commande ; un manifeste différent est refusé.

## Mesures

`summary.json` donne par bras le taux de résolution, les `infra_error` exclus des dénominateurs, les `needs_input`, la médiane des tokens et leur couverture, les tokens par tâche résolue, la durée, le nombre moyen de sous-agents, la taille des diffs et les runs qui ont touché les chemins cachés. Il compare aussi chaque paire de bras tâche par tâche.

## Limites

Dix tâches et trois répétitions ne détectent qu’un écart large et cohérent. Les tokens dépendent des métadonnées natives exposées ; `tokens_source` indique leur origine. Les bras cstack et pstack lisent la source copiée au lieu d’un plugin installé, comme `scripts/behavior-scenarios.py`. Le bras pstack exécute des instructions écrites pour Cursor (`Task`, `AskQuestion`, `cursor-team-kit`) : il mesure ces instructions telles quelles dans Codex, pas pstack dans Cursor. Les deux paquets héritent du modèle principal ; la diversité de modèles des panels n’est pas mesurée par ce bras. Aucun résultat n’est revendiqué tant qu’une campagne réelle n’a pas été exécutée.

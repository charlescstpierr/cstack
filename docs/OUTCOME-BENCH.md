# Banc de résultat : Codex seul, cstack et pstack

Ce banc répond à deux questions : sur des correctifs open source réels, `$cstack:cstack` résout-il plus de tâches que Codex seul, et à quel coût ? Et le portage fait-il mieux, dans Codex, que la source pstack non adaptée ? Il complète la mesure du routage de #1 et de la PR 43, qui observe les lectures et délégations, pas le résultat.

## Principe

- **Tâches** : correctifs fusionnés après la date plancher de `evals/outcome/suite.json`, pour limiter la contamination. Chaque dossier `evals/outcome/tasks/<id>/` contient `task.json` et un `Dockerfile` figé.
- **Bras** : `vanilla` reçoit la demande du ticket et la limite de portée locale. `cstack` reçoit le `default_prompt` de la compétence, la même demande et le chemin de la source cstack copiée dans la campagne. `pstack`, facultatif, reçoit une demande anglaise équivalente de mode poteto et de délégation, la même demande et le chemin de `poteto-mode/SKILL.md` au commit épinglé de `UPSTREAM.json`. Même modèle, même effort, même sandbox. `--arms` choisit les bras, `vanilla,cstack` par défaut. Un bras `nom=cstack:<models.json>` ajoute une variante de cstack avec sa propre configuration de modèles, validée par le helper de `setup-cstack` puis écrite dans `.cstack/models.json` du workspace, hors diff.
- **Réseau** : coupé par défaut. `--network` l’autorise pour tous les bras de la campagne, ce qu’exigent un worker Claude Code et l’installation des helpers. Un run dont les commandes récupèrent un dépôt distant ou visent le dépôt amont reçoit `possible_leak` et sort des taux.
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

Derrière un proxy HTTPS qui réécrit les certificats, les Dockerfiles TypeScript acceptent un secret BuildKit facultatif : construire l’image une fois avec `docker build --secret id=ca,src=<bundle CA> -t <tag> evals/outcome/tasks/<id>`, sous le tag attendu par `image_tag`, puis `validate` la réutilise. Sans proxy, rien n’est à faire.

`fetch-pstack` récupère `cursor/plugins` au commit épinglé et refuse le checkout si un seul blob diffère de l’inventaire. `validate` n’appelle aucun modèle : pour chaque tâche, les tests `fail_to_pass` échouent sur la base avec les tests cachés, tous passent avec le correctif et les `pass_to_pass` passent sur la base. Son reçu, lié à l’empreinte de la tâche, est exigé par `run`. Une campagne interrompue reprend avec la même commande ; un manifeste différent est refusé.

## Mesures

`summary.json` donne par bras le taux de résolution, les `infra_error` et `possible_leak` exclus des dénominateurs, les `needs_input`, la médiane des tokens et leur couverture, les tokens par tâche résolue, la durée, le nombre moyen de sous-agents, la taille des diffs et les runs qui ont touché les chemins cachés. Il compare aussi chaque paire de bras tâche par tâche.

## Limites

Dix tâches et trois répétitions ne détectent qu’un écart large et cohérent. Les tokens dépendent des métadonnées natives exposées ; `tokens_source` indique leur origine. Les bras cstack et pstack lisent la source copiée au lieu d’un plugin installé, comme `scripts/behavior-scenarios.py`. Le bras pstack exécute des instructions écrites pour Cursor (`Task`, `AskQuestion`, `cursor-team-kit`) : il mesure ces instructions telles quelles dans Codex, pas pstack dans Cursor. Les deux paquets héritent du modèle principal ; la diversité de modèles des panels n’est pas mesurée par ce bras. Aucun résultat n’est revendiqué tant qu’une campagne réelle n’a pas été exécutée.

## Campagnes du ticket #65

Ces campagnes tranchent les hypothèses de #65 sur l’écart entre pstack dans Cursor et cstack dans Codex. Les règles de décision ci-dessous sont fixées avant toute exécution ; un résultat ne les modifie pas après coup.

Prérequis : Docker, Codex CLI authentifié, Claude Code installé et connecté, même modèle et même effort pour toutes les campagnes.

```sh
python3 scripts/outcome-bench.py fetch-pstack
python3 scripts/outcome-bench.py validate
MIXED=cstack-mixed=cstack:evals/outcome/models/mixed-panels.json

# Pilote : vérifie le banc, ne conclut rien.
python3 scripts/outcome-bench.py run --output .cstack/outcome-runs/65-pilot --seed 65 --repetitions 1 --network \
  --task-id tenacity-cyclic-cause --task-id chi-mount-collision \
  --arms "vanilla,cstack,pstack,$MIXED" --model <modèle> --effort <effort>

# Campagne A : poids, traduction et délégation (90 runs).
python3 scripts/outcome-bench.py run --output .cstack/outcome-runs/65-a --seed 65 --network \
  --arms vanilla,cstack,pstack --model <modèle> --effort <effort>

# Campagne B : diversité de modèles des panels (60 runs).
python3 scripts/outcome-bench.py run --output .cstack/outcome-runs/65-b --seed 65 --network \
  --arms "cstack,$MIXED" --model <modèle> --effort <effort>
```

Le pilote est accepté si aucun `infra_error` ne vient du banc lui-même, si les tokens sont relevés et si `cstack-mixed` montre au moins un appel Claude Code (`cli_runtimes_seen`, ou reçus de workers conservés sous `state/<run>/`). Sinon, corriger le banc avant A et B.

Règles de décision, sur les dix tâches appariées, hors `infra_error` et `possible_leak` :

| Hypothèse | Confirmée si | Suite |
| --- | --- | --- |
| Poids et traduction | `pstack` meilleur que `cstack` sur au moins trois tâches de plus que l’inverse, ou résolution à une tâche près avec au moins 30 % de tokens par tâche résolue en plus pour `cstack` | noyau court du contrat d’exécution, le reste chargé à la demande |
| Délégation | moins de 0,5 sous-agent par run en moyenne pour `cstack` malgré sa demande de délégation | demande de délégation injectée à chaque tâche (#61) |
| Diversité de modèles | `cstack-mixed` meilleur que `cstack` sur au moins trois tâches de plus que l’inverse | `setup-cstack` propose un panel mixte quand Claude Code est présent et connecté |
| Aucune | autre résultat | aucun changement de runtime ; constat consigné |

Le mode oublié entre deux tours et les outils propres à Cursor ne sont pas observables dans un banc à un seul tour ; ils restent des observations qualitatives. Chaque correctif retenu passe par sa propre PR, puis le banc est relancé sur ce correctif.

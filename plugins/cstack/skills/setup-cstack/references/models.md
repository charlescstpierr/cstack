# Modèles, rôles et recommandations

Après invocation dans T3, le [contrat T3](../../cstack/references/runtime/t3.md) prime pour catalogue, choix explicites et synchronisation. Le chemin T3 modèle seul utilise `models.py --host t3 --catalog ... --host-context ...`, sans conversion automatique ni CLI de repli.


Référence de [setup-cstack](../SKILL.md). L'ordre de présentation (propositions avant configuration actuelle) est fixé dans le SKILL.

## Proposition `show`

Exécute la commande modèle `show`, avec `--claude-ready` quand l'inventaire trouve Claude Code présent, prêt au dispatch et connecté selon `claude auth status`. Sa proposition `mixed review panels` met Claude Code en regard de Codex dans `arena runners`, `architect runners` et `interrogate reviewers`, en gardant trois entrées (deux héritages natifs, une Claude Code) : présente-la parmi les propositions, recommandée pour la revue indépendante, et applique-la seulement si elle est acceptée. Si la demande concerne Claude Code ou un autre CLI, suis [Ajouter ou mettre à jour Claude Code](claude-code.md) avant les recommandations natives.

Montre, après le tableau des propositions, les autres modèles/efforts confirmés disponibles pour personnaliser ces choix. Pour un rôle absent de la configuration actuelle, indique qu’il hérite actuellement du parent. Propose dans cet ordre : accepter toutes les recommandations disponibles, choisir des groupes, personnaliser par rôle ou position de panel, conserver la configuration actuelle, utiliser l’héritage pour les rôles sélectionnés, ou annuler. Préserve les rôles non sélectionnés. Si aucun modèle n’a pu être découvert, explique l’échec de découverte avant de proposer l’héritage.

## Budget de raisonnement

Avant le tableau des propositions, demande un budget avec ces quatre choix, en nommant le budget courant quand il se déduit de la configuration (tous les efforts explicites identiques ; sinon « personnalisé ») :

- `illimité — conserver max`
- `large — effort xhigh`
- `moyen — effort high`
- `réduit — effort medium`

`illimité` laisse les efforts tels que les propose le tableau. `large`, `moyen` et `réduit` fixent un plafond d'effort pour chaque sélection à modèle explicite, positions de panel comprises, sur l'échelle `max` > `xhigh` > `high` > `medium` > `low`. Un effort déjà inférieur ou égal au plafond reste tel quel ; un effort supérieur descend au plafond. Si le catalogue live ne propose pas cet effort pour ce modèle, prends l'effort disponible le plus élevé en dessous ; s'il n'y en a aucun, marque la position comme choix requis. L'héritage (`inherit-parent`), une sélection de modèle sans effort et une sélection CLI sans effort ne changent pas. Le budget s'applique seulement aux rôles que l'utilisateur sélectionne, et `models.py apply` le valide contre le catalogue comme tout autre choix.

## Recommandations

Ces choix sont facultatifs et validés contre le catalogue live avant sélection :

| Travail | Modèle | Effort de raisonnement | Justification |
| --- | --- | --- | --- |
| Exploration | `gpt-5.6-luna` | `max` | Recherches bornées et explications. |
| Changements simples | `gpt-5.6-luna` | `max` | Petites éditions avec checks d'acceptation clairs. |
| Développement | `gpt-6-astra` | `low` | Implémentation avec jugement de conception. |
| Débogage difficile | `gpt-6-astra` | `medium` | Diagnostic de causes qui interagissent. |
| Revue de code | `gpt-6-astra` | `low` | Jugement sur la correction et le risque. |
| Architecture complexe | `gpt-6-astra` | `xhigh` | Conception transversale et compromis. |
| Documentation | `gpt-5.6-luna` | `max` | Prose focalisée à partir de faits établis. |

Les valeurs de modèle doivent être des sélections vérifiées, pas des défauts inconditionnels.

## Rôles

Roles simples :

- `simple edits`
- `documentation`
- `feature, refactoring`
- `bug-fix`
- `perf-issue`
- `hillclimb`
- `judgment and prose`
- `hardest tasks`
- `how explorer`
- `how explainer`
- `why investigators`
- `why synthesizer`
- `reflect tooling`
- `reflect judgment, divergent, synthesizer`
- `swarm workers`

Roles de panel :

- `arena runners`
- `arena cross-judge pool`
- `architect runners`
- `interrogate reviewers`

Le pool de juge croisé fournit un juge, de préférence différent de l'auteur quand c'est disponible. Sans pool, utilise un juge indépendant avec modèle hérité. Les autres longueurs de listes de panel fixent le nombre demandé de tentatives. Ne prétends jamais à des familles de modèles différentes quand chaque passe a utilisé le même modèle.

Formats de valeur, replis et défauts de panel : [modèles du contrat](../../cstack/references/runtime/modeles.md).

Exemple n'exigeant aucun modèle particulier :

```json
{
  "feature, refactoring": "inherit-parent",
  "interrogate reviewers": ["inherit-parent", "inherit-parent", "inherit-parent"]
}
```

Une configuration sauvegardée ne prouve pas qu'un modèle peut tourner. Gère le rejet au premier dispatch réel comme spécifié dans le [contrat d’exécution](../../cstack/references/runtime/modeles.md). Ne lance pas de travaux de test payants seulement pour finir la configuration.

## Catalogues et sélections CLI

Les anciennes sélections et recommandations restent natives Codex. Pour un worker externe demandé, utilise le [contrat des workers CLI](../../cstack/references/runtime-workers.md) : `codex-cli`, `claude-code`, `cursor-agent` ou `grok`. Les panels peuvent mélanger ces sélections et l’héritage natif. Le coordinateur prépare les commandes et rend une synthèse unique ; l’utilisateur ne pilote pas chaque CLI manuellement.

Applique seulement les choix de runtime acceptés, via `models.py show`, `apply` et `resolve` ([commandes](project-apply.md#configuration-modèle-seule)). Le parcours `project.py preview/apply` reste celui de la préparation des documents de projet. Ne change pas la configuration globale, ne copie aucun credential et ne lance ni login ni génération pendant le setup. La présence d’une commande officielle de login ne prouve pas les droits d’abonnement Grok Build.

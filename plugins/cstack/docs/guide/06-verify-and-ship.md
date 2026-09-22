# Vérifier le résultat et livrer

« Ça compile » ne prouve pas le comportement. Écrivez la condition de fin, exécutez la vérification la plus proche de l'utilisateur et inspectez le résultat réel avant de déclarer la tâche terminée.

## Déclarer la condition de fin

```text
$cstack:cstack ajoute la sortie JSON. La sortie texte reste identique, le JSON se parse et les deux fonctionnent sur le projet exemple. Montre les preuves.
```

[Prouver que ça marche](../../skills/cstack/references/principles/prove-it-works.md) et [`$cstack:blast-radius`](../../skills/blast-radius/SKILL.md) ramènent la vérification au produit, à la commande, aux valeurs écrites ou au profil réel.

## Créer une compétence de vérification du projet

```text
$cstack:create-verification-skill
```

[`$cstack:create-verification-skill`](../../skills/create-verification-skill/SKILL.md) décrit comment lancer l'application, la piloter comme un utilisateur et capturer une preuve. Il peut s'appuyer sur un harnais existant, un navigateur, un terminal ou HTTP selon le projet.

## Garder cette vérification honnête

```text
$cstack:maintain-verification-skill audite la carte des fonctionnalités et corrige seulement les écarts prouvés.
```

[`$cstack:maintain-verification-skill`](../../skills/maintain-verification-skill/SKILL.md) relit les sources puis exécute une passe réelle. Il signale un produit défectueux au lieu de masquer le problème dans la compétence.

## Enregistrer les modifications

Une tâche de modification de code ou de documentation inclut par défaut les commits Git locaux. Après chaque unité cohérente vérifiée, cstack inspecte le diff et crée un commit sans redemander confirmation. Le bilan donne les SHA réels et explique les éventuelles modifications restantes. Les changements préexistants ou appartenant à une autre tâche restent intacts.

Une demande explicite de ne pas committer, le mode Plan et la lecture seule sont respectés. Hors dépôt Git ou si un contrôle, un hook ou le commit échoue, cstack signale le blocage et conserve le travail. Pour `$cstack:cstack`, les tâches d’implémentation suivent la portée de livraison du [contrat d’exécution](../../skills/cstack/references/codex-runtime.md#activation-et-routage). Le merge reste une action séparée.

## Ouvrir une PR

Préparez un diff court, des commits ordonnés et les preuves. Git et `gh` sont les chemins de référence quand ils sont installés. Avec `$cstack:cstack`, la PR suit la portée de livraison du contrat d’exécution. L'envoi d'un message, la publication, le merge et le déploiement restent des actions séparées.

## Amener la PR à un état révisable

Le [guide d'exécution d'ouverture de PR](../../skills/cstack/playbooks/opening-a-pr.md) prépare la livraison. Le [guide d'exécution de suivi](../../skills/cstack/playbooks/babysit.md) traite les conflits, retours et contrôles CI. Il ne fusionne rien sans autorisation.

## Livrer une pile

Le [guide d'exécution de livraison](../../skills/cstack/playbooks/shipping.md) vérifie chaque tête et peut préparer l'ordre de livraison. La fusion ou le déploiement reste une action externe et irréversible qui demande l'autorisation correspondante.

## Terminer après la fusion

Après une livraison autorisée, fusionnée et vérifiée, le coordinateur appelle automatiquement le [guide d'exécution de nettoyage](../../skills/cstack/playbooks/worktree-cleanup.md). Il retire les worktrees temporaires créés pour cette tâche une fois libérés par leurs agents et processus, sans demander une nouvelle confirmation. Les branches et les preuves sont conservées. Un worktree encore utilisé, modifié, verrouillé, contenant des fichiers à préserver ou dont l'intégration reste incertaine est gardé avec une raison dans le rapport. Une PR ouverte ou une pile remise à l'opérateur reste disponible pour la suite du travail.

Suivant : [travailler pendant votre absence](./07-overnight.md).

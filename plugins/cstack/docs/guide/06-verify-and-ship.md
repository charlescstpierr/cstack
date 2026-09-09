# Vérifier le résultat et livrer

« Ça compile » ne prouve pas le comportement. Écrivez la condition de fin, exécutez la vérification la plus proche de l'utilisateur et inspectez le résultat réel avant de déclarer la tâche terminée.

## Déclarer la condition de fin

```text
$cstack ajoute la sortie JSON. La sortie texte reste identique, le JSON se parse et les deux fonctionnent sur le projet exemple. Montre les preuves.
```

[`principle-prove-it-works`](../../skills/principle-prove-it-works/SKILL.md) et [`$blast-radius`](../../skills/blast-radius/SKILL.md) ramènent la vérification au produit, à la commande, aux valeurs écrites ou au profil réel.

## Créer une compétence de vérification du projet

```text
$create-verification-skill
```

[`$create-verification-skill`](../../skills/create-verification-skill/SKILL.md) décrit comment lancer l'application, la piloter comme un utilisateur et capturer une preuve. Il peut s'appuyer sur un harnais existant, un navigateur, un terminal ou HTTP selon le projet.

## Garder cette vérification honnête

```text
$maintain-verification-skill audite la carte des fonctionnalités et corrige seulement les écarts prouvés.
```

[`$maintain-verification-skill`](../../skills/maintain-verification-skill/SKILL.md) relit les sources puis exécute une passe réelle. Il signale un produit défectueux au lieu de masquer le problème dans la compétence.

## Ouvrir une PR

Préparez un diff court, des commits ordonnés et les preuves. Git et `gh` sont les chemins de référence quand ils sont installés. La création d'une PR, l'envoi d'un message ou la publication restent des actions explicites autorisées pour la tâche.

## Amener la PR à un état révisable

Le [playbook d'ouverture de PR](../../skills/cstack/playbooks/opening-a-pr.md) prépare la livraison. Le [playbook de suivi](../../skills/cstack/playbooks/babysit.md) traite les conflits, retours et contrôles CI. Il ne fusionne rien sans autorisation.

## Livrer une pile

Le [playbook Shipping](../../skills/cstack/playbooks/shipping.md) vérifie chaque tête et peut préparer l'ordre de livraison. Le merge ou le déploiement reste une action externe et irréversible qui demande l'autorisation correspondante.

Suivant : [travailler pendant votre absence](./07-overnight.md).

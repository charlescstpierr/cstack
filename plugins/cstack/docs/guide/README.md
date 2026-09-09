# Guide cstack

cstack fonctionne avec une demande claire, un périmètre explicite et une preuve observable. `$cstack:cstack` choisit le playbook et appelle les compétences utiles avec les outils natifs de Codex.

Voici le parcours :

1. [Configurer cstack](./01-setup.md). Installer le plugin et lancer une première tâche.
2. [Router avec `$cstack:cstack`](./02-cstack.md). Donner un objectif et choisir le bon playbook.
3. [Comprendre le code](./03-understand.md). Utiliser `$cstack:how`, `$cstack:why`, `$cstack:teach` et `$cstack:recall`.
4. [Concevoir le changement](./04-design.md). Comparer les formes avant de verrouiller l'architecture.
5. [Construire et nettoyer](./05-build-and-clean.md). Tester le comportement et garder un diff lisible.
6. [Vérifier et livrer](./06-verify-and-ship.md). Prouver le résultat réel et préparer la livraison.
7. [Continuer pendant une absence](./07-overnight.md). Définir un contrat, une trace et une condition d'arrêt.
8. [Piloter avec les principes](./08-principles.md). Utiliser les 23 principes au bon moment.
9. [Adapter cstack](./09-make-it-yours.md). Créer une compétence ciblée et l'évaluer.
10. [Recettes et pièges](./10-recipes-and-pitfalls.md). Copier des demandes courtes et éviter les erreurs fréquentes.

Si vous ne retenez qu'une chose, demandez un résultat et sa preuve :

```text
$cstack:cstack l'export écrit des lignes en double après un retry. Reproduis, corrige la cause et montre la vérification.
```

Commencez par [la configuration](./01-setup.md).

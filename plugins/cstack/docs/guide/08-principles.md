# Piloter avec les noms de principes

cstack fournit 23 principes sous forme de références internes, dans `skills/cstack/references/principles/`. Ils ne sont pas des skills indépendants et n'apparaissent plus comme commandes dans le sélecteur. Le skill actif indique quand lire chaque référence ; l'installation ne les active pas et aucune lecture de l'ensemble n'est nécessaire. Leur application respecte le périmètre et les permissions de l'utilisateur.

## Utiliser un principe

```text
$cstack:cstack applique « Subtract Before You Add ». Supprime les chemins morts avant d'ajouter la nouvelle forme.
```

Le nom donne une contrainte précise. Les demandes qui utilisaient une ancienne commande individuelle passent désormais par `$cstack:cstack` et le nom du principe. La réponse décrit la décision utile au résultat, sans inventaire de principes appliqués. Chaque fiche renvoie au [contrat runtime Codex](../../skills/cstack/references/codex-runtime.md).

## Les 23 principes

### Construire moins et mieux

- [Laziness Protocol](../../skills/cstack/references/principles/laziness-protocol.md) préfère la suppression et le plus petit changement correct.
- [Foundational Thinking](../../skills/cstack/references/principles/foundational-thinking.md) choisit les structures avant la logique.
- [Redesign From First Principles](../../skills/cstack/references/principles/redesign-from-first-principles.md) intègre une exigence comme si elle existait depuis le début.
- [Attack the Premise](../../skills/cstack/references/principles/attack-the-premise.md) remet en cause une prémisse partagée par plusieurs échecs.
- [Subtract Before You Add](../../skills/cstack/references/principles/subtract-before-you-add.md) retire la complexité avant de construire.
- [Minimize Reader Load](../../skills/cstack/references/principles/minimize-reader-load.md) réduit les couches et l'état caché.
- [Outcome-Oriented Execution](../../skills/cstack/references/principles/outcome-oriented-execution.md) vise l'état final vérifiable.
- [Experience First](../../skills/cstack/references/principles/experience-first.md) choisit le résultat utile à l'utilisateur.
- [Exhaust the Design Space](../../skills/cstack/references/principles/exhaust-the-design-space.md) compare deux ou trois prototypes quand aucun précédent n'existe.
- [Build the Lever](../../skills/cstack/references/principles/build-the-lever.md) construit l'outil qui exécute ou prouve le travail.

### Architecture et état

- [Model the Domain](../../skills/cstack/references/principles/model-the-domain.md) encode le domaine dans une structure.
- [Boundary Discipline](../../skills/cstack/references/principles/boundary-discipline.md) valide aux frontières et fait confiance aux types internes.
- [Type System Discipline](../../skills/cstack/references/principles/type-system-discipline.md) rend les états illégaux impossibles à représenter.
- [Make Operations Idempotent](../../skills/cstack/references/principles/make-operations-idempotent.md) rend les retries convergents.
- [Migrate Callers Then Delete Legacy APIs](../../skills/cstack/references/principles/migrate-callers-then-delete-legacy-apis.md) migre les appelants puis supprime l'ancienne API.
- [Separate Before Serializing Shared State](../../skills/cstack/references/principles/separate-before-serializing-shared-state.md) élimine le partage avant d'ajouter un verrou.

### Vérification

- [Prove It Works](../../skills/cstack/references/principles/prove-it-works.md) vérifie l'artefact réel.
- [Fix Root Causes](../../skills/cstack/references/principles/fix-root-causes.md) reproduit et remonte à la cause.
- [Sequence work into verifiable units](../../skills/cstack/references/principles/sequence-verifiable-units.md) termine chaque unité par un contrôle.
- [Test Behavior, Not Implementation](../../skills/cstack/references/principles/test-behavior-not-implementation.md) teste le comportement observé.

### Délégation

- [Guard the Context Window](../../skills/cstack/references/principles/guard-the-context-window.md) garde les gros volumes hors du fil principal.
- [Never Block on the Human](../../skills/cstack/references/principles/never-block-on-the-human.md) avance sur le travail réversible et présente le résultat.

### Méta

- [Encode Lessons in Structure](../../skills/cstack/references/principles/encode-lessons-in-structure.md) transforme une correction répétée en contrôle structurel.

Suivant : [adapter cstack à votre façon de travailler](./09-make-it-yours.md).

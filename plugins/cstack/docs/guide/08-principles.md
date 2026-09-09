# Piloter avec les noms de principes

cstack fournit 23 principes sous forme de compétences explicites. Dans une tâche activée par `$cstack`, ils cadrent la décision au moment où elle compte. Ils respectent le périmètre et les permissions de l'utilisateur et n'autorisent aucun message externe automatique.

## Utiliser un principe

```text
$cstack applique « Subtract Before You Add ». Supprime les chemins morts avant d'ajouter la nouvelle forme.
```

Le nom donne une contrainte précise. La réponse doit dire quelle décision il a changée. Chaque fiche contient son [contrat runtime Codex](../../skills/cstack/references/codex-runtime.md).

## Les 23 principes

### Construire moins et mieux

- [`principle-laziness-protocol`](../../skills/principle-laziness-protocol/SKILL.md) préfère la suppression et le plus petit changement correct.
- [`principle-foundational-thinking`](../../skills/principle-foundational-thinking/SKILL.md) choisit les structures avant la logique.
- [`principle-redesign-from-first-principles`](../../skills/principle-redesign-from-first-principles/SKILL.md) intègre une exigence comme si elle existait depuis le début.
- [`principle-attack-the-premise`](../../skills/principle-attack-the-premise/SKILL.md) remet en cause une prémisse partagée par plusieurs échecs.
- [`principle-subtract-before-you-add`](../../skills/principle-subtract-before-you-add/SKILL.md) retire la complexité avant de construire.
- [`principle-minimize-reader-load`](../../skills/principle-minimize-reader-load/SKILL.md) réduit les couches et l'état caché.
- [`principle-outcome-oriented-execution`](../../skills/principle-outcome-oriented-execution/SKILL.md) vise l'état final vérifiable.
- [`principle-experience-first`](../../skills/principle-experience-first/SKILL.md) choisit le résultat utile à l'utilisateur.
- [`principle-exhaust-the-design-space`](../../skills/principle-exhaust-the-design-space/SKILL.md) compare deux ou trois prototypes quand aucun précédent n'existe.
- [`principle-build-the-lever`](../../skills/principle-build-the-lever/SKILL.md) construit l'outil qui exécute ou prouve le travail.

### Architecture et état

- [`principle-model-the-domain`](../../skills/principle-model-the-domain/SKILL.md) encode le domaine dans une structure.
- [`principle-boundary-discipline`](../../skills/principle-boundary-discipline/SKILL.md) valide aux frontières et fait confiance aux types internes.
- [`principle-type-system-discipline`](../../skills/principle-type-system-discipline/SKILL.md) rend les états illégaux impossibles à représenter.
- [`principle-make-operations-idempotent`](../../skills/principle-make-operations-idempotent/SKILL.md) rend les retries convergents.
- [`principle-migrate-callers-then-delete-legacy-apis`](../../skills/principle-migrate-callers-then-delete-legacy-apis/SKILL.md) migre les appelants puis supprime l'ancienne API.
- [`principle-separate-before-serializing-shared-state`](../../skills/principle-separate-before-serializing-shared-state/SKILL.md) élimine le partage avant d'ajouter un verrou.

### Vérification

- [`principle-prove-it-works`](../../skills/principle-prove-it-works/SKILL.md) vérifie l'artefact réel.
- [`principle-fix-root-causes`](../../skills/principle-fix-root-causes/SKILL.md) reproduit et remonte à la cause.
- [`principle-sequence-verifiable-units`](../../skills/principle-sequence-verifiable-units/SKILL.md) termine chaque unité par un contrôle.
- [`principle-test-behavior-not-implementation`](../../skills/principle-test-behavior-not-implementation/SKILL.md) teste le comportement observé.

### Délégation

- [`principle-guard-the-context-window`](../../skills/principle-guard-the-context-window/SKILL.md) garde les gros volumes hors du fil principal.
- [`principle-never-block-on-the-human`](../../skills/principle-never-block-on-the-human/SKILL.md) avance sur le travail réversible et présente le résultat.

### Méta

- [`principle-encode-lessons-in-structure`](../../skills/principle-encode-lessons-in-structure/SKILL.md) transforme une correction répétée en contrôle structurel.

Suivant : [adapter cstack à votre façon de travailler](./09-make-it-yours.md).

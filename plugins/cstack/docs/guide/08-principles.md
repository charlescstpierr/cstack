# Piloter avec les noms de principes

cstack fournit 23 principes sous forme de références internes, dans `skills/cstack/references/principles/`. Ils ne sont pas des compétences indépendantes et n'apparaissent plus comme commandes dans le sélecteur. La compétence active indique quand lire chaque référence ; l'installation ne les active pas et aucune lecture de l'ensemble n'est nécessaire. Leur application respecte le périmètre et les permissions de l'utilisateur.

## Utiliser un principe

```text
$cstack:cstack applique « Soustraire avant d'ajouter ». Supprime les chemins morts avant d'ajouter la nouvelle forme.
```

Le nom donne une contrainte précise. Les demandes qui utilisaient une ancienne commande individuelle passent désormais par `$cstack:cstack` et le nom du principe. La réponse décrit la décision utile au résultat, sans inventaire de principes appliqués. Chaque fiche renvoie au [contrat d'exécution Codex](../../skills/cstack/references/codex-runtime.md).

## Les 23 principes

### Construire moins et mieux

- [Protocole de paresse](../../skills/cstack/references/principles/laziness-protocol.md) préfère la suppression et le plus petit changement correct.
- [Pensée fondationnelle](../../skills/cstack/references/principles/foundational-thinking.md) choisit les structures avant la logique.
- [Redessiner à partir des premiers principes](../../skills/cstack/references/principles/redesign-from-first-principles.md) intègre une exigence comme si elle existait depuis le début.
- [Attaquer la prémisse](../../skills/cstack/references/principles/attack-the-premise.md) remet en cause une prémisse partagée par plusieurs échecs.
- [Soustraire avant d'ajouter](../../skills/cstack/references/principles/subtract-before-you-add.md) retire la complexité avant de construire.
- [Minimiser la charge du lecteur](../../skills/cstack/references/principles/minimize-reader-load.md) réduit les couches et l'état caché.
- [Exécution orientée résultat](../../skills/cstack/references/principles/outcome-oriented-execution.md) vise l'état final vérifiable.
- [L'expérience d'abord](../../skills/cstack/references/principles/experience-first.md) choisit le résultat utile à l'utilisateur.
- [Épuiser l'espace de conception](../../skills/cstack/references/principles/exhaust-the-design-space.md) compare deux ou trois prototypes quand aucun précédent n'existe.
- [Construire le levier](../../skills/cstack/references/principles/build-the-lever.md) construit l'outil qui exécute ou prouve le travail.

### Architecture et état

- [Modéliser le domaine](../../skills/cstack/references/principles/model-the-domain.md) encode le domaine dans une structure.
- [Discipline des frontières](../../skills/cstack/references/principles/boundary-discipline.md) valide aux frontières et fait confiance aux types internes.
- [Discipline du système de types](../../skills/cstack/references/principles/type-system-discipline.md) rend les états illégaux impossibles à représenter.
- [Rendre les opérations idempotentes](../../skills/cstack/references/principles/make-operations-idempotent.md) rend les nouvelles tentatives convergentes.
- [Migrer les appelants puis supprimer les API anciennes](../../skills/cstack/references/principles/migrate-callers-then-delete-legacy-apis.md) migre les appelants puis supprime l'ancienne API.
- [Séparer avant de sérialiser l'état partagé](../../skills/cstack/references/principles/separate-before-serializing-shared-state.md) élimine le partage avant d'ajouter un verrou.

### Vérification

- [Prouver que ça marche](../../skills/cstack/references/principles/prove-it-works.md) vérifie l'artefact réel.
- [Corriger les causes racines](../../skills/cstack/references/principles/fix-root-causes.md) reproduit et remonte à la cause.
- [Séquencer le travail en unités vérifiables](../../skills/cstack/references/principles/sequence-verifiable-units.md) termine chaque unité par un contrôle.
- [Tester le comportement, pas l'implémentation](../../skills/cstack/references/principles/test-behavior-not-implementation.md) teste le comportement observé.

### Délégation

- [Garder la fenêtre de contexte](../../skills/cstack/references/principles/guard-the-context-window.md) garde les gros volumes hors du fil principal.
- [Ne jamais bloquer sur l'humain](../../skills/cstack/references/principles/never-block-on-the-human.md) avance sur le travail réversible et présente le résultat.

### Méta

- [Encoder les leçons dans la structure](../../skills/cstack/references/principles/encode-lessons-in-structure.md) transforme une correction répétée en contrôle structurel.

Suivant : [adapter cstack à votre façon de travailler](./09-make-it-yours.md).

---
name: typescript-best-practices
description: "À utiliser pour $cstack:typescript-best-practices. Cstack y route quand le changement touche des fichiers .ts ou .tsx."
---

# Bonnes pratiques TypeScript

Runtime : [règles communes](../cstack/references/runtime/base.md).

Applique d'abord la référence de principe [discipline du système de types](../cstack/references/principles/type-system-discipline.md).

| Règle | Résumé |
|------|---------|
| Unions discriminées | Modélise les variantes avec un discriminant littéral `kind` pour que les états impossibles ne puissent pas être représentés. Pas de sacs de champs optionnels. |
| Types marqués | Marque les primitives avec `& { readonly __brand: "X" }` pour éviter les confusions. Valide une fois à la frontière. |
| Modélisation constructive | Construis la forme pour que la valeur illégale ne puisse pas être construite. `[T, ...T[]]` pour non vide, `[T, T][]` pour longueur paire, `start` plus `duration` pour une plage. Pas une garde runtime, pas un souhait de types de raffinement. |
| Type total le plus simple | Garde `T[]` tant que chaque opération dessus reste totale. Renforce vers `NonEmpty<T>` seulement là où le type souple force `!`, un cast ou un throw "cela ne devrait jamais arriver". |
| `unknown` plutôt que `any` | Les données externes sont `unknown`. |
| Schémas avant gardes | Avant d'écrire à la main une garde de type propriété par propriété, utilise la bibliothèque de schémas runtime du dépôt et infère le type du schéma, comme `z.infer`. |
| Aucun cast `as` | Chaque `as` est un crash d’exécution en attente. Caste seulement après validation. |
| Hiérarchie de narrowing | Switch discriminant > opérateur `in` > `typeof`/`instanceof` > garde de type définie par l'utilisateur > `as`. |
| Gardes de type | Elles doivent vérifier l'affirmation. Une garde menteuse est pire que `as` : son nom rassurant cache le bug. Nomme-les `isX` ou `hasX`. |
| Exhaustivité | Mets `const _exhaustive: never = x;` inline dans les bras default pour que le compilateur échoue à l'ajout d'une variante. |
| `satisfies` plutôt que `as` | Valide la valeur sans élargir les types littéraux. |
| Validation de frontière | Parse quand les données entrent, vers un type de domaine nommé. `Record<string, unknown>` (quelle que soit son orthographe) s'arrête à ce parse. Fais confiance aux types dedans. Voir la référence de principe [discipline des frontières](../cstack/references/principles/boundary-discipline.md). |
| Types dérivés des schémas | Prends `Pick`/`Omit`/`Parameters`/`ReturnType`/`Awaited`/`typeof` avant de déclarer une nouvelle interface. |
| Arguments objets | Passe des objets, pas des positionnels, pour que l'ordre des arguments soit auto-documente. Saute sur les chemins chauds (rendu par frame, tokenizers, parsers). |
| Vrais tests | Ne mocke pas ce que tu peux exécuter. Préfère les primitives de test réelles du framework avec checks de fuite/disposable, et vérifie l'UI dans un build qui tourne. Mocke seulement ce que tu ne peux pas exécuter localement. |
| Télémétrie structurée | Préfère des diagnostics de logger structurés avec assez de contexte pour déboguer depuis un id. Pas de `console.log` dans le code livré. |

Exemples : `references/patterns.md`.

# Patterns TypeScript

Exemples de code pour chaque règle dans `SKILL.md`. Les principes sous-jacents sont agnostiques au langage. Voir les références de principes [discipline du système de types](../../cstack/references/principles/type-system-discipline.md) et [discipline des frontières](../../cstack/references/principles/boundary-discipline.md).

## Types marqués

Marque les primitives pour éviter les confusions. Valide une fois à la frontière. Le code aval fait confiance au type.

```ts
type AgentId = string & { readonly __brand: "AgentId" };

function parseAgentId(input: string): AgentId {
  if (!isUUID(input)) throw new Error(`ID d'agent invalide: ${input}`);
  return input as AgentId;
}

function focusAgent(id: AgentId): void {
  /* l'entrée est fiable */
}
```

Respecte la forme `readonly __brand: 'X'`. N'invente pas de nouvelle convention.

## Unions discriminées

Modélise les variantes avec un discriminant littéral. Chaque variante partage le nom de champ et chaque valeur de variante est unique, donc les combinaisons impossibles ne peuvent pas être representees.

```ts
// A éviter. Booléen + optionnels laisse exister des états contradictoires.
type DiffState = { loading: boolean; diff?: GitDiff; error?: string };

// A faire. Seuls les états valides existent.
type DiffState =
  | { kind: "loading" }
  | { kind: "ready"; diff: GitDiff }
  | { kind: "error"; error: string };
```

Choisis un nom de discriminant (`kind`, `type`, `tag`) et garde-le.

## Modélisation constructive

Construis le type depuis des parties toutes légales au lieu de restreindre un type souple avec des checks runtime.

Non vide, via un tuple variadique :

```ts
type NonEmpty<T> = [T, ...T[]];

// A éviter : T[] plus un check de longueur que chaque appelant doit répéter
function pickWinner(entries: string[]): string {
  if (entries.length === 0) throw new Error("aucune entrée");
  return entries[Math.floor(Math.random() * entries.length)];
}

// A faire : une valeur vide de ce type ne peut pas exister
function pickWinner(entries: NonEmpty<string>): string {
  return entries[Math.floor(Math.random() * entries.length)];
}
```

Quand un `T[]` simple arrive, narrow une fois avec une garde. Le fait voyage ensuite dans le type :

```ts
const isNonEmpty = <T>(arr: T[]): arr is NonEmpty<T> => arr.length > 0;
```

Longueur paire, sous forme de paires :

```ts
type Pairs<T> = [T, T][];
```

Une plage de temps, comme début plus durée :

```ts
// A éviter : un commentaire porte l'invariant
type TimeRange = { start: Date; end: Date }; // start <= end

// A faire : une plage negative ne peut pas être écrite; dérive end au besoin
type TimeRange = { start: Date; durationMs: number };
```

Garde `durationMs` comme nombre simple. Marque-le (selon Types marqués) seulement si un nombre brut pourrait être passe là où une durée est attendue, pas par réflexe. Choisis la representation qui rend le mauvais état inconstructible, puis expose par-dessus la lecture dont tu as besoin (`pairs.flat()`, un helper `rangeEnd()`).

## Type total le plus simple

Ne renforce pas tout. Garde `T[]` quand chaque opération dessus est totale :

```ts
const sum = (xs: number[]) => xs.reduce((a, b) => a + b, 0); // [] vaut 0, c'est correct
```

Renforce quand le type souple force un mensonge au site d'usage. Les signaux sont `!`, `arr[0] as T` et un throw "cela ne devrait jamais arriver" :

```ts
// A éviter : partialite passée en douce devant le compilateur
function newestSession(sessions: Session[]): Session {
  return sessions.at(0)!;
}

// A faire : renforcer l'entrée; l'assertion disparaît
function newestSession(sessions: NonEmpty<Session>): Session {
  return sessions[0];
}
```

Affaiblir le résultat en `Session | undefined` est l'autre signature totale.

## `unknown` plutôt que `any`

Les données externes sont toujours `unknown`. Narrow avant usage.

```ts
// A éviter
function handle(input: any) {
  return input.foo.bar;
}

// A faire
function handle(input: unknown) {
  if (typeof input === "object" && input !== null && "foo" in input) {
    // narrowed; le compilateur vérifie l'accès
  }
}
```

Les sources externes incluent payloads RPC, `JSON.parse`, `postMessage`, IPC, contenu de fichiers, variables d'environnement, résultats de base de données.

## Schémas avant gardes maison

Avant d'écrire une garde de type propriété par propriété pour des données externes, cherche la bibliothèque de schémas runtime du dépôt et les schémas existants. Laisse un schéma posséder la validation et dérive le type TypeScript depuis lui. Ne maintiens pas un schéma, une interface dupliquée et une garde qui peuvent diverger.

```ts
import { z } from "zod";

const UserSchema = z.object({
  id: z.string().uuid(),
  role: z.enum(["admin", "member"]),
});

type User = z.infer<typeof UserSchema>;

function parseUser(input: unknown): User {
  return UserSchema.parse(input);
}
```

Utilise `safeParse` quand l'échec est une branche attendue. Utilise le helper d'inférence équivalent quand le dépôt utilise une autre bibliothèque de schémas. N'ajoute pas une nouvelle dépendance de schéma pour une seule garde. Cette règle préfère le système de schémas auquel le codebase fait déjà confiance.

## Aucun cast `as`

Chaque `as` est un crash d’exécution potentiel. Caste seulement après que le système de types a vérifié l'affirmation.

```ts
// A éviter
const user = data as User;

// A faire. Gagner le cast à la frontière.
function parseUser(data: unknown): User {
  if (typeof data !== "object" || data === null) {
    throw new Error("objet attendu");
  }
  if (!("id" in data) || typeof (data as Record<string, unknown>).id !== "string") {
    throw new Error("id attendu");
  }
  // ... valider tous les champs
  return data as User; // OK, cast gagne après validation complète
}
```

Quand tu retires un `as` du code existant, identifie pourquoi TypeScript ne peut pas infèrer :

- Discriminant manquant : ajoute-en un, passe à une union discriminee.
- Type source trop large (par exemple `Record<string, unknown>`) : narrow-le.
- Frontiere non typée : ajoute une fonction parse ou un schéma.
- Vraiment inexprimable : utilise un type marqué ou `satisfies`.

## Hiérarchie de narrowing

Du meilleur au dernier recours :

1. **Switch / if sur union discriminee.** Le compilateur narrow automatiquement.
2. **Operateur `in`.** `"key" in obj` narrow vers les variantes contenant cette clé.
3. **`typeof` / `instanceof`.** Pour les primitives et instances de classes.
4. **Garde de type définie par l'utilisateur.** Quand ce qui précède ne suffit pas.
5. **Cast `as`.** Seulement après validation.

```ts
function area(s: Shape): number {
  if ("radius" in s) return Math.PI * s.radius ** 2; // narrowed en circlé
  return s.width * s.height; // narrowed en rect
}
```

## Gardes de type

Une garde doit vraiment vérifier l'affirmation. Une garde menteuse est pire que `as`.

```ts
function isCirclé(s: Shape): s is Shape & { kind: "circlé" } {
  return s.kind === "circlé";
}
```

Préfère le narrowing par discriminant quand c'est possible.

## Exhaustivité

Dans les bras default, assigne le discriminant à une locale typée `never`.

```ts
// Switch qui retourne une valeur
function area(s: Shape): number {
  switch (s.kind) {
    case "circlé":
      return Math.PI * s.radius ** 2;
    case "rect":
      return s.width * s.height;
    default: {
      const _exhaustive: never = s;
      return _exhaustive;
    }
  }
}

// Switch void
function handle(s: Shape): void {
  switch (s.kind) {
    case "circlé":
      drawCirclé(s);
      break;
    case "rect":
      drawRect(s);
      break;
    default: {
      const _exhaustive: never = s;
      void _exhaustive;
    }
  }
}
```

Style return dans les switchs qui retournent une valeur, style void dans les switchs de statements.

## `satisfies` plutôt que `as`

`satisfies` valide sans élargir les types littéraux.

```ts
// A éviter. Élargit et perd les types littéraux.
const config = { theme: "dark", cols: 3 } as Config;

// A faire. Valide ET préserve les types littéraux.
const config = { theme: "dark", cols: 3 } satisfies Config;
// config.theme est "dark" (litteral), pas string
```

## Validation de frontière

Valide une fois là où les données entrent. Fais confiance aux types à l'intérieur. Voir la référence de principe [discipline des frontières](../../cstack/references/principles/boundary-discipline.md).

- **Formats wire** (proto, JSON-RPC) : parse avec `ignoreUnknownFields` pour que les changements forward-compatible ne cassent pas les anciens clients.
- **JSON persiste :** blob versionne avec un try/catch autour du parse.
- **Ne revalide pas** profondément dans les chaînes d'appel.

## Types dérivés de schémas

Quand un `.proto`, une spec OpenAPI, un schéma GraphQL ou une migration de base de données définit déjà une forme, dérive depuis les types générés au lieu de les dupliquer.

```ts
// A éviter. Forme dupliquée, dérive quand le schéma change.
type CheckSummary = {
  totalCount: number;
  checks: { name: string; status: string }[];
};
function renderChecks(s: CheckSummary) {
  /* ... */
}

// A faire. Deriver depuis le type de schéma généré.
import type { ChecksMessage } from "<generated module>";
function renderChecks(s: Pick<ChecksMessage, "totalCount" | "checks">) {
  /* ... */
}
```

Prends `Pick`, `Omit`, `Parameters`, `ReturnType`, `Awaited`, `typeof` avant d'écrire une nouvelle interface.

## Arguments objets

```ts
// A éviter. Inverse deux arguments, ça compile encore.
openFile(uri, {
  startLineNumber: 10,
  startColumn: 1,
  endLineNumber: 10,
  endColumn: 1,
});

// A faire. Indépendant de l'ordre, auto-documente.
openFile({
  uri,
  selection: {
    startLineNumber: 10,
    startColumn: 1,
    endLineNumber: 10,
    endColumn: 1,
  },
});
```

Saute sur les chemins chauds : rendu par frame, tokenizers, parsers, tout ce qui est dans une boucle serrée où le coût d'allocation compte.

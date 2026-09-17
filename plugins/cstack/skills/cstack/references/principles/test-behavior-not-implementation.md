# Tester le comportement, pas l'implémentation

Lisez cette référence lorsqu'un processus cstack actif vous route ici ou lorsque l'utilisateur nomme ce principe. Suivez le [contrat d'exécution Codex](../codex-runtime.md) pour le périmètre et les permissions.

Un test appelle le code comme ses utilisateurs le font et affirme le résultat qu'ils observent contre une valeur attendue littérale. Un test qui affirme quels appels le code a faits, ou répète une constante que le code contient, ne fait ni l'un ni l'autre.

Le contrôle : avant de garder un test, demandez s'il passerait encore si chaque fonction qu'il importe retournait `undefined`. Si oui, il n'observe aucun comportement et ne peut pas échouer pour un défaut. Réécrivez l'assertion ou supprimez le test.

**Pourquoi :** un test qui ne peut pas échouer pour un défaut coûte du temps de CI et de l'attention de revue sans rien attraper. Un pin de constante échoue aussi quand quelqu'un modifie la constante ou l'invite qu'il répète, donc il empêche cette édition.

**Cinq formes qui passent encore quand chaque fonction importée retourne `undefined` :**

- **Assertion faible ou absente.** Aucun `expect`, ou seulement `toBeDefined`, `toBeTruthy`, `not.toThrow`, `toBeInstanceOf`, `toBeGreaterThan(0)`.
- **Mock ou absence seulement.** Seulement `toHaveBeenCalled`, `not.toHaveBeenCalled`, `toBeUndefined`, `toEqual([])`, `toHaveLength(0)`, `not.toBe(wrongValue)`.
- **Autoréférentiel.** La valeur attendue vient du code testé : `expect(f(a)).toBe(f(a))`, `expect(parsed.url).toBe(buildUrl(...))`.
- **Pin de constante.** L'assertion répète une constante maintenue à la main, un défaut de config, une ligne de table ou une chaîne d'invite : `expect(LIMITS.maxTools).toBe(8)`, `expect(PROMPT).toContain("You are")`.
- **Fixture affirme fixture.** L'assertion lit des données construites par le test ou une valeur calculée dans `beforeEach`, et le sujet ne s'exécute jamais dans le corps.

**Le correctif :** appelez le sujet dans le corps du test avec une entrée concrète et affirmez la sortie littérale ou l'effet observable, `expect(slugify("Hello, World!")).toBe("hello-world")`. Pour une absence, affirmez la présence sur l'autre entrée dans le même test. Pour une constante, testez le mécanisme qui la lit avec une entrée au lieu de répéter la valeur. Pour un mock, affirmez la charge utile reçue ou l'état après l'appel, pas le fait qu'il a été appelé. Quand aucune assertion de ce type n'existe, supprimez le test.

**Gardez** un test d'une relation entre les lignes d'une table (une clé présente dans deux tables, un parent qui existe), et un contrôle à la compilation dans un fichier `*.test-d.ts`.

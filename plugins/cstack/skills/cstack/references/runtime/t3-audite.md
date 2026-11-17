# Chemin audité T3

Ce document ne sert qu'au chemin audité du [contrat T3](t3.md), quand l'utilisateur demande une trace recoupée de l'hôte ou un bundle empreinté pour l'enfant. Le chemin direct ne le lit pas. Les [options demandées et rapportées](t3.md#options-demandées-et-options-rapportées), les [restrictions de fournisseur](t3.md#restrictions-de-fournisseur), le dispatch, le cycle de vie, la propriété des checkouts et les PR du contrat valent aussi ici.

## Captures et snapshot

Le coordinateur conserve les résultats des outils dans une trace bornée sans secrets. Les capacités et les métadonnées de thread doivent permettre le recoupement de l'identité complète et des empreintes. Sans elles, la preuve d'hôte est non établie et ce chemin est BLOCKED ; le chemin direct reste disponible.

Le coordinateur respecte la fréquence de découverte prescrite par le harnais. Les helpers ne découvrent rien. Le contrat consolidé est `cstack.t3-snapshot/2` avec un contexte séparé `cstack.t3-context/2`. Le format non publié V1 utilisant `environmentId/sessionId` est refusé avec une erreur de migration explicite. Recapturer les deux enveloppes au lieu de convertir des identifiants ou d'inventer une date.

Le normaliseur pur reçoit les octets de deux captures JSON bornées chacune à 1 MiB. Chaque enveloppe exige `toolName`, `input`, `output`, `itemId`, `observedAt` avec fuseau. Les noms exacts sont `t3-code.orchestrator_capabilities` et `t3-code.t3_thread_read`. Un ancien `thread.json` brut sans enveloppe est refusé. Le CLI écrit seulement le JSON sur stdout. Il ne charge pas models.json et n'appelle ni processus, ni MCP, ni configuration globale.

```sh
python3 plugins/cstack/skills/setup-cstack/scripts/models.py normalize \
  --capabilities-trace .cstack/t3-adaptation/runtime-capture/capabilities-trace.json \
  --thread-trace .cstack/t3-adaptation/runtime-capture/thread-trace.json \
  > .cstack/t3-adaptation/normalized-v2.json
```

Le snapshot contient les champs suivants.

- `schema: "cstack.t3-snapshot/2"`, `host: "t3"`.
- `coordinator` contient exactement `threadId`, `projectId`, `link`, `providerInstanceId`, `model`, `runtimeMode`, `interactionMode`, `options`. Les sept premiers champs viennent de `output.thread`. Les options viennent de la liste réelle `inheritedOptions`, transformée en mapping exact. Le lien reste opaque et entier. Aucun UUID ni environnement n'en est extrait.
- `caps.parentThreadId == thread.input.threadId == thread.output.thread.threadId`. Fournisseur, modèle et modes hérités doivent correspondre aux champs du thread. Les options héritées doivent correspondre aux déclarations du modèle, si celles-ci sont valides.
- `sources.capabilities` et `sources.thread` conservent chacun `sha256` des octets exacts, `itemId`, `observedAt`, `toolName`. Les anciennes captures conservent leurs dates. Aucun mtime n'intervient.
- `providers` mappe les identifiants exacts vers `models`, `modelsComplete`, `constraints` réelles et les champs présents `enabled`, `canRunChildTask`, `canRunCrossProviderChildTask`, `omittedModels`, `runtimeModes`. Seul `omittedModels: 0` entier explicite signifie complet. Une liste partielle reste utilisable pour ses modèles connus. Une absence signifie inconnu, jamais inexistant. Une capture filtrée peut omettre le modèle du coordinateur tout en exposant sa capacité de délégation et une cible explicite. Conserver alors son identité et ses options observées ; bloquer seulement une position héritée dont le modèle manque. Les déclarations présentes mais incohérentes restent refusées. `omittedModels: null` signifie aussi une complétude inconnue.
- Chaque modèle contient `options`, mapping exact vers `type` inféré parmi `string/boolean`, `values` homogènes et `default` seulement si exposé. Un `default: null` exposé par l’hôte signifie inconnu et n’est pas converti en valeur d’option. Aucun `secret/required` n'est inventé. Une déclaration mixed ou malformée marque le modèle `invalid` sans retirer les autres positions. Les doublons JSON, fournisseur, modèle, option et option héritée sont refusés.
- `sha256` est le SHA-256 du corps sans ce champ, sérialisé par Python `json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()`.

Le coordinateur établit séparément `expectedCoordinator` depuis son identité actuelle vérifiée. Il ne copie pas automatiquement le snapshot dans le contexte. Le contexte exige `schema: "cstack.t3-context/2"`, cette identité complète, `snapshotSha256`, `capabilitiesSha256`, `threadSha256`, `revalidated: true`, `revalidatedAt`, `expiresAt`. Les dates explicites suivent les règles actives de l'hôte. Le normaliseur ne choisit aucune expiration. Chaque observation doit être antérieure ou égale à `revalidatedAt`, puis `revalidatedAt <= now < expiresAt`. Les empreintes et l'identité doivent correspondre exactement.


La constance du modèle et ces recoupements prouvent une cohérence de données, pas une attestation cryptographique de l'hôte ni sa vivacité.

`models.py --host t3 --catalog <snapshot> --host-context <contexte> preflight <rôles>` valide la forme globale puis rapporte chaque rôle et position. Un fichier malformé est une erreur globale. Une position indisponible ne retire ni ne réordonne les autres. Une position CLI dans T3 v2 est BLOCKED avant son travail dépendant. Le parcours autonome Codex/CLI reste disponible par choix explicite de l'utilisateur.

L'héritage reste ici une cible explicite, reconstruite depuis les trois métadonnées inherited, parce que le binding exige une cible observable. Une position héritée dont le modèle manque à une capture filtrée est donc bloquée sur ce chemin, alors que le chemin direct part sans `target`.

## Préparation et snapshot exact

`runtime/runtime.ts prepare --request <JSON absolu>` ne lance aucun processus. La requête exige `binding` du préflight et `selection` T3, `brief_file`, `context_files`, `skills`, `skill_references`, `scope`, `acceptance`, `evidence`, `snapshot` et `transport_limit_bytes`. Les chemins du brief et du contexte sont absolus et dans le dossier de tâche. `snapshot` contient, dans cet ordre, chaque fichier du brief puis du contexte sous forme `{path, sha256}`. Les chemins du snapshot peuvent utiliser les mêmes aliases symboliques que le brief et le contexte. Le helper les résout et retourne les chemins canoniques. Les octets doivent correspondre à une source figée. La limite transport est mesurée par le coordinateur, bornée à 1 MiB par le helper, sans prétendre connaître la limite maximale de T3. Lors du smoke du 5 novembre 2026, le validateur de cet hôte a annoncé une longueur maximale de 120 000 pour `task`. Le coordinateur a choisi prudemment une borne de 120 000 octets UTF-8, qui respecte aussi cette limite de longueur. Réutiliser une limite seulement tant que le contrat de cet hôte reste vérifié ; 1 MiB est le plafond du helper, pas une limite T3 revendiquée.


Le bundle réutilise worker-context et worker-skills. Pour T3, les liens vers les contrats runtime Codex et CLI sont remplacés par le seul [contrat T3](t3.md), sans ce document : ils ne tirent pas leurs playbooks de coordinateur dans chaque enfant. Les cinq principes communs sont liés directement aux consignes du délégué et restent inclus quel que soit l’hôte. Les skills sélectionnés et leurs références de tâche restent complets et empreintés. Le remplacement des contrats runtime ne retire aucun de ces principes communs. Demander explicitement un contrat runtime remplacé bloque. La limite de transport reste stricte, sans troncature du contenu retenu. Le bundle inclut le contrat T3 prioritaire, les critères, preuves, empreintes et contenu autonome. Une skill requise absente, un snapshot différent ou une limite dépassée bloque sans troncature. `prepared` prouve la préparation seulement. Le préflight et resolve retournent `binding: {coordinatorScope, catalogSha256, target}`. Préparer exige ce binding et vérifie sa forme complète et l'égalité de sa cible avec la sélection, sans dépendre de l'ordre des clés. Les valeurs et types des options sont exacts, y compris une clé `__proto__`. Le résultat prepared conserve ce binding avec les preuves du brief. Le préflight refuse un contexte d'un autre coordinateur. Le préparateur ne peut pas attester sa vivacité.

Avant delegate_task, le coordinateur compare `coordinatorScope` à son scope courant établi séparément, `catalogSha256` au préflight courant et `target` à la cible effective. Le binding est un lien de cohérence, pas un autorisateur cryptographique. Le helper ne prouve ni hôte ni disponibilité.

L’[état exact des revues](t3.md#état-exact-des-revues) est une exigence commune au chemin direct et au chemin audité. Le binding du bundle ne prouve pas que le checkout du reviewer contient cet état.

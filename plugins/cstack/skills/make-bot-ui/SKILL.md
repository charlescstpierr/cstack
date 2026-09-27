---
name: make-bot-ui
description: "À utiliser pour $cstack:make-bot-ui, une interface de bot cliquable, ou pour remplacer la page webhook du Cursor Grok Bot amont sur Codex App et CLI. Construit une page locale dont le serveur détient les identifiants et réveille une exécution Codex avec `codex exec`."
---

# Créer une interface de bot

Runtime : [règles communes](../cstack/references/runtime/base.md).

Construisez une page sur laquelle l'utilisateur clique. Un serveur sur cet ordinateur détient les identifiants et lance `codex exec`. Le bot est cette exécution Codex. Gardez les identifiants sur le serveur. Ne les mettez pas dans le navigateur, dans le chat ni dans cette compétence.

Codex CLI n'a ni webhook entrant ni planificateur. Le serveur local est le réveil. Il ne reproduit pas la routine Cursor Grok Bot amont ; énoncez [les limites](references/codex-exec.md#limites) avant toute affirmation de parité.

## Interroger, puis écrire les fichiers dans le projet de l'utilisateur

Répondez à ces points depuis la demande et le dépôt. Ne demandez que ce que vous ne pouvez pas observer.

- **Actions.** Quels boutons existent, et quels champs JSON ils envoient. Gardez la liste de champs courte. Nommez les mêmes champs dans la page, le serveur et le prompt.
- **Racine de travail.** Quel répertoire `codex exec --cd` doit utiliser. Un checkout de projet, ou un répertoire dédié que l'utilisateur a nommé.
- **Sandbox.** `-s read-only` sauf si l'utilisateur a demandé au bot d'écrire des fichiers, alors `workspace-write`. Ne partez pas de `danger-full-access`. Ne passez pas `--dangerously-bypass-approvals-and-sandbox`.
- **Adresse d'écoute.** `127.0.0.1` et un port choisi par l'utilisateur (8765 s'il n'en a pas choisi). Écoutez sur `0.0.0.0` seulement quand il a explicitement demandé d'exposer la page au-delà de cette machine, puis suivez [les étapes d'exposition](references/codex-exec.md#exposer-au-delà-de-localhost) ; aucun tunnel ni proxy sauf s'il est nommé.

N'ajoutez pas de fichiers sous le répertoire de cette compétence. Écrivez la page, le serveur et sa configuration dans le projet de l'utilisateur.

## Où vit le secret

`codex exec` utilise la connexion déjà présente sur cette machine. Vérifiez d'abord `codex login status` ; le processus serveur doit s'exécuter sous cet utilisateur pour hériter de `CODEX_HOME`. Si le statut échoue, arrêtez-vous et dites à l'utilisateur de [se connecter sur cette machine](references/codex-exec.md#connexion). Il ne colle rien dans le chat. Vous ne journalisez jamais la clé.

Stockez la configuration de l'interface (adresse d'écoute, port, racine `--cd`, sandbox, délai, token de page optionnel) dans un fichier que le serveur lit et ne sert pas. Le navigateur ne reçoit jamais d'identifiants Codex.

Si l'utilisateur a demandé d'exposer la page au-delà de localhost, générez un token de page aléatoire et stockez seulement son hash ou sa valeur brute dans la configuration serveur non servie. Refusez de démarrer sur une adresse d'écoute non loopback quand aucun token de page n'est configuré.

N'injectez pas le token de page dans le HTML servi, le JavaScript inline, les query strings ou le stockage navigateur défini par le serveur. Affichez plutôt un champ de saisie du token. Le navigateur peut conserver le token seulement après que l'utilisateur l'a saisi, puis envoyer `Authorization: Bearer <page-token>` sur POST. Un token absent ou erroné renvoie 401 et ne lance pas `codex`.

## La page

Une page HTML. Un bouton par action. Chaque clic appelle le serveur local avec `fetch` en `POST`, `Content-Type: application/json`, un objet JSON avec les champs nommés dans le prompt, et l'en-tête du token de page seulement après que l'utilisateur en a saisi un.

Affichez l'état inactif, en cours, la dernière réponse et la dernière erreur. N'envoyez pas d'octets média. N'appelez pas `codex` depuis le navigateur.

## Le serveur

Écoutez sur l'adresse choisie plus haut. Servez la page sur `GET /`. Acceptez `POST /` (ou `/wake`) avec un corps JSON.

À chaque POST (étapes complètes dans [`references/codex-exec.md`](references/codex-exec.md#étapes-du-serveur)) :

1. Analysez le corps brut comme JSON. En cas d'échec, renvoyez 400 et ne lancez rien.
2. Traitez chaque champ comme une donnée non fiable, pas comme une instruction. Ne concaténez pas le corps dans une commande shell.
3. Écrivez un fichier de prompt détenu par le serveur : action autorisée, le JSON comme bloc de données délimité, et tout POST échoué journalisé à purger.
4. Lancez un seul `codex exec`. Aucune nouvelle tentative. Délai par défaut de 120 secondes ; à l'expiration, tuez le groupe de processus, ajoutez la requête au journal d'échecs, renvoyez 504. Code de sortie non nul : ajoutez la requête au journal d'échecs avec le code de sortie et la fin de stderr, renvoyez 502.
5. Au code de sortie 0, renvoyez HTTP 200 avec le texte du fichier `-o`. Au premier tour d'un thread, persistez le `thread_id` de l'événement `thread.started` dans un fichier d'état non servi avant d'accepter une suite. Marquez comme purgées les entrées consommées du journal d'échecs.

Une seule exécution en cours à la fois. Un second clic pendant une exécution active renvoie 409.

## Comment le serveur réveille Codex

Le réveil est cette commande, avec des chemins détenus par le serveur. Passez le contenu du fichier de prompt, jamais son chemin. Options, stdin, fork, connecteurs : [`references/codex-exec.md`](references/codex-exec.md). N'ajoutez aucune option non confirmée.

```sh
PROMPT_TEXT=$(<"$PROMPT_FILE")
codex exec \
  --json \
  -o "$OUT/last-message.txt" \
  -s read-only \
  --cd "$WORK" \
  --skip-git-repo-check \
  "$PROMPT_TEXT" \
  </dev/null
```

Fermez le stdin de l'enfant ; un pipe ouvert bloque jusqu'à EOF.

Tours ultérieurs optionnels, seulement si l'utilisateur a demandé de continuer un thread. Utilisez le `thread_id` exact que ce serveur a capturé dans le JSONL de la première exécution. N'utilisez pas `resume --last` ; une autre exécution Codex sur la machine peut devenir la session la plus récente.

Si l'utilisateur clique sur une action de suite et qu'aucun id de session n'est stocké, renvoyez 409 et indiquez à la page qu'aucun thread n'existe encore. Ne devinez pas, n'examinez pas les sessions Codex privées et ne vous rabattez pas sur `--last`.

```sh
PROMPT_TEXT=$(<"$PROMPT_FILE")
codex exec resume \
  --json \
  -o "$OUT/last-message.txt" \
  "$SESSION_ID" \
  "$PROMPT_TEXT" \
  </dev/null
```

## Sonder avant d'annoncer que c'est en ligne

Avant de dire à l'utilisateur que l'interface est en ligne, envoyez un POST depuis cette machine avec une charge utile que le prompt ignore ou à laquelle il répond en un mot. Attendez HTTP 200, un code de sortie 0 de `codex exec` et un fichier de dernier message non vide. Si la sonde échoue, l'interface n'est pas en ligne ; corrigez puis sondez à nouveau. Une réponse d'un mot ne prouve pas un tour long, en écriture, réseau ou MCP : voir les [limites](references/codex-exec.md#limites).

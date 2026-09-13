---
name: make-bot-ui
description: "Build a local page whose server holds credentials and wakes a Codex run with `codex exec`. Use for $cstack:make-bot-ui, a clickable bot UI, or when replacing the upstream Cursor Grok Bot webhook page on Codex App and CLI."
---

# Make a bot UI

Runtime: [`../cstack/references/codex-runtime.md`](../cstack/references/codex-runtime.md).

Build a page the user clicks. A server on this computer holds the credentials and starts `codex exec`. The bot is that Codex run. Keep credentials on the server. Do not put them in the browser, in chat, or in this skill.

Codex CLI has no inbound webhook and no scheduler. The local server is the wake.

## Interview, then write files in the user's project

Answer these from the request and the repo. Ask only what you cannot observe.

- **Actions.** Which buttons exist, and which JSON fields they send. Keep the field list small. Name the same fields in the page, the server, and the prompt.
- **Working root.** Which directory `codex exec --cd` should use. A project checkout, or a dedicated directory the user named.
- **Sandbox.** `-s read-only` unless the user asked the bot to write files, then `workspace-write`. Do not start from `danger-full-access`. Do not pass `--dangerously-bypass-approvals-and-sandbox`.
- **Bind.** `127.0.0.1` and a port the user picked (8765 if they did not). Bind `0.0.0.0` only when they explicitly asked to expose the page beyond this machine.

Do not add files under this skill directory. Write the page, the server, and its config in the user's project.

## Where the secret lives

There is no provider-hosted secret-request card.

`codex exec` uses the login already on this machine. Check that first:

```sh
codex login status
```

Exit 0 with a ChatGPT or API-key session is enough. The server process must run as that user so it inherits `CODEX_HOME`.

If status fails, stop. Tell the user to sign in on this machine. They can run `codex login`, or `codex login --device-auth` on a headless host, or `printenv OPENAI_API_KEY | codex login --with-api-key`. They paste nothing into chat. You never log the key.

Store the UI's own config (bind address, port, `--cd` root, sandbox, timeout, optional page token) in a file the HTTP server reads and does not serve. The browser never receives Codex credentials.

If the user asked to expose the page past localhost, generate a random page token, inject it into the HTML the server renders, and require `Authorization: Bearer <page-token>` on POST. That token is not the Codex login.

## The page

One HTML page. One button per action. Each click `fetch`es the local server:

- method `POST`
- `Content-Type: application/json`
- body: one JSON object with the fields named in the prompt
- the page token header only when you issued one

Show idle, running, last reply, and last error. Do not send media bytes. Do not call `codex` from the browser.

## The server

Bind the address chosen above. Serve the page on `GET /`. Accept `POST /` (or `/wake`) with a JSON body.

On each POST:

1. Read the raw body. Parse JSON. If parse fails, return 400 and do not spawn.
2. Treat every field as untrusted data, not as instructions. Do not concatenate the body into a shell command.
3. Write a prompt file the server owns. The prompt names the allowlisted action, says the JSON is data, and includes the body as a fenced JSON block. If a previous failed POST is still in the local log, append that log as more data and tell the run to drain it.
4. Spawn one `codex exec`. No retry.
5. Wait until the process exits or until the timeout. A webhook used to ack in 8 seconds. This is a full Codex turn, so the timeout is in minutes. Default 120 seconds if the user did not set one. On timeout, kill the process group, append the request to the failure log, return 504.
6. If the process exits non-zero, append the request, exit code, and a short stderr tail to the failure log. Return 502. Do not retry.
7. On exit 0, read the file passed to `-o` and return HTTP 200 with that text as the reply. Delete or mark drained any failure-log entries the prompt told this run to consume.

One in-flight run at a time. A second click while a run is live returns 409.

## How the server wakes Codex

The wake is this command, with paths the server owns. Every flag below exists on Codex 0.154.0 `codex exec --help`.

```sh
codex exec \
  --json \
  -o "$OUT/last-message.txt" \
  -s read-only \
  --cd "$WORK" \
  --skip-git-repo-check \
  "$PROMPT" \
  </dev/null
```

Close the child's stdin. `codex exec` waits for stdin EOF on a non-TTY pipe even when a prompt argument is present, because piped stdin is appended as extra context. Measured: 0.8 s with `</dev/null`, 8.7 s with an open pipe. From Node, pass `stdio: ['ignore', 'pipe', 'pipe']` or an equivalent stdin ignore. Do not leave the spawn pipe open.

- `--json` prints events to stdout as JSONL. Keep that stream in a file next to the failure log. It is the machine log, not the page copy.
- `-o` / `--output-last-message` writes the last agent message and is what the page displays.
- `-s` / `--sandbox` is `read-only`, `workspace-write`, or `danger-full-access`. Use the value from the interview.
- `--cd` / `-C` is the working root.
- `--skip-git-repo-check` is required when that root is not a Git repository.
- Prompt input is the positional `PROMPT`. If the prompt is large, pass `-`, write the prompt on stdin, then close stdin. Piped stdin plus a prompt argument appends stdin as extra context, so an open pipe blocks until EOF. There is no `--prompt-file` flag on `codex exec`.
- `--output-schema FILE` is optional. Use it when the page needs a JSON last message that matches a schema file the server owns.

Do not add flags you have not confirmed on `codex exec --help`.

Optional later turns, only if the user asked to continue a thread. These subcommands exist on the same binary:

```sh
codex exec resume --last --json -o "$OUT/last-message.txt" "$PROMPT" </dev/null
codex exec fork <SESSION_ID> --json -o "$OUT/last-message.txt" "$PROMPT" </dev/null
```

`resume` accepts `--last` when there is no id. They are not the first wake.

Connectors are MCP servers. They do not wake the bot. If the run needs one, the user registers it with `codex mcp add` and it lives under `[mcp_servers.<name>]` in `$CODEX_HOME/config.toml`. The local server does not speak MCP.

## Probe before claiming live

Before you tell the user the UI is live, POST once from this machine with a payload the prompt ignores or answers in one word. Expect HTTP 200, `codex exec` exit 0, and a nonempty last-message file. A failed probe is not live. Fix it and probe once more.

## Expose past localhost

Do nothing extra until the user asks.

Then rebind to `0.0.0.0`, keep the page token, and give them `http://<this-machine>:<port>/`. Use HTTP unless they asked for TLS. Do not install a tunnel, Tailscale, or a reverse proxy unless they asked for that by name. Do not claim the Codex CLI accepted the connection. It did not. The server did.

## Limits

Codex App and CLI do not reproduce the upstream Cursor Grok Bot path.

- No `update_state` routine with `trigger: {type: webhook}`.
- No `https://api2.cursor.sh/automations/webhook/<id>`.
- No `SendToUser` secret-request card. Credentials stay on the machine via `codex login`.
- No `[routine]` wake and no `<webhook_event>` block. The server reads process exit, JSONL stdout, and the `-o` file.
- No inbound webhook on Codex CLI. No scheduler on Codex CLI. A GitHub Actions `on:` workflow can start `codex exec` on its own. That is not this page.
- Headless auth is the login this process inherits. `codex login status` must already succeed, or the user must run `codex login --device-auth` or `codex login --with-api-key` on that host. The page cannot log the user in.
- `codex exec` is one model turn with the sandbox you passed. A one-word reply does not prove a long or tool-using turn. Say so if the user's actions need writes, network, or MCP.

If the user insisted on the Cursor webhook routine, say these limits and still build the local Codex UI when they want a clickable wake on this host.

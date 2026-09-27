# `codex exec` details for the bot UI

Read this with [the make-bot-ui skill](../SKILL.md) when writing the server's spawn code, adding a follow-up action, or explaining limits to the user. Every flag below exists on Codex 0.154.0 `codex exec --help`. Do not add flags you have not confirmed on `codex exec --help`.

## Stdin

Close the child's stdin. `codex exec` waits for stdin EOF on a non-TTY pipe even when a prompt argument is present, because piped stdin is appended as extra context. Measured: 0.8 s with `</dev/null`, 8.7 s with an open pipe. From Node, pass `stdio: ['ignore', 'pipe', 'pipe']` or an equivalent stdin ignore. Do not leave the spawn pipe open.

## Flags

- `--json` prints events to stdout as JSONL. Keep that stream in a file next to the failure log. It is the machine log, not the page copy.
- `-o` / `--output-last-message` writes the last agent message and is what the page displays.
- `-s` / `--sandbox` is `read-only`, `workspace-write`, or `danger-full-access`. Use the value from the interview.
- `--cd` / `-C` is the working root.
- `--skip-git-repo-check` is required when that root is not a Git repository.
- Prompt input is the positional prompt text. If the prompt is large, pass `-`, write the prompt text on stdin, then close stdin. Piped stdin plus a prompt argument appends stdin as extra context, so an open pipe blocks until EOF. There is no `--prompt-file` flag on `codex exec`.
- `--output-schema FILE` is optional. Use it when the page needs a JSON last message that matches a schema file the server owns.

## Fork a captured thread

Same rules as the resume command in the skill: only when the user asked to continue a thread, and only with the exact session id this server captured from the first run's JSONL.

```sh
PROMPT_TEXT=$(<"$PROMPT_FILE")
codex exec fork \
  --json \
  -o "$OUT/last-message.txt" \
  "$SESSION_ID" \
  "$PROMPT_TEXT" \
  </dev/null
```

`resume` accepts `--last` when there is no id. This UI must not use it.

## Connectors

Connectors are MCP servers. They do not wake the bot. If the run needs one, the user registers it with `codex mcp add` and it lives under `[mcp_servers.<name>]` in `$CODEX_HOME/config.toml`. The local server does not speak MCP.

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

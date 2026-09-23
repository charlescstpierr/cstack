# Intake

Two Codex runs that triage a report, then reproduce and optionally draft a fix. GitHub Issues is the first-class source. Slack or another channel is a connector-backed variant. This pack is not a registered skill.

Follow [the Codex runtime contract](../../skills/cstack/references/codex-runtime.md).

The Cursor pack used two live automations on a Slack source channel, `/automate`, and Cursor Slack actions. This pack keeps the workflow contract and replaces the host with `codex exec` plus one GitHub Actions workflow. Read [Limits](#limits) before enabling anything.

## What you install

Copy these files into the target repository. Do not point a workflow at the plugin cache.

| Pack file | Copy to |
| --- | --- |
| [templates/configuration.example.yaml](templates/configuration.example.yaml) | <code>.github/cstack/intake/configuration.yaml</code> |
| [templates/github-intake.yml](templates/github-intake.yml) | <code>.github/workflows/intake.yml</code> |
| [templates/triage-prompt.md](templates/triage-prompt.md) | <code>.github/cstack/intake/prompts/triage.md</code> |
| [templates/reproduce-prompt.md](templates/reproduce-prompt.md) | <code>.github/cstack/intake/prompts/reproduce.md</code> |
| [templates/triage-result.schema.json](templates/triage-result.schema.json) | <code>.github/cstack/intake/schemas/triage-result.schema.json</code> |
| [templates/reproduce-result.schema.json](templates/reproduce-result.schema.json) | <code>.github/cstack/intake/schemas/reproduce-result.schema.json</code> |
| [references/triage.md](references/triage.md) | <code>.github/cstack/intake/references/triage.md</code> |
| [references/reproduce-and-fix.md](references/reproduce-and-fix.md) | <code>.github/cstack/intake/references/reproduce-and-fix.md</code> |
| [references/verify-existing-fix.md](references/verify-existing-fix.md) | <code>.github/cstack/intake/references/verify-existing-fix.md</code> |
| [references/control-adapter.md](references/control-adapter.md) | <code>.github/cstack/intake/references/control-adapter.md</code> |
| [references/routing.example.md](references/routing.example.md) | <code>.github/cstack/intake/routing.md</code> |
| [references/feature-map.example.md](references/feature-map.example.md) | <code>.github/cstack/intake/feature-map.md</code> |

Commit the copies. Fill every placeholder. Then enable the workflow.

## Source and trigger

GitHub Issues start a run through GitHub Actions `on: issues`. An outside reporter who fails the action write-access check is handled by `on: workflow_dispatch` from a maintainer, or by setting the action `allow-users` input. That is a real event. Codex CLI does not receive it.

Do not add `on: issue_comment`. A comment posted with `GITHUB_TOKEN` is authored by `github-actions[bot]` and does not create an `issue_comment` workflow run.

A headless run is `codex exec`. Structured output is `--output-schema` plus `-o <file>`. `--json` prints events to stdout as JSONL. The workflow calls `openai/codex-action@v1` with `prompt-file`, `output-file`, and `output-schema-file`.

Slack is not a wake. If the source is a Slack channel, register an MCP server with `codex mcp add` and declare it under `[mcp_servers.<name>]`. A GitHub Actions `on: schedule` job or a local scheduler must still start `codex exec`. The connector supplies read and thread-reply tools. It does not start the process.

## Job graph

One workflow file, one run per report.

1. **triage** checks out the full repository history, fail-closes if the installed files are missing, requires `source.repository` to match `GITHUB_REPOSITORY`, snapshots the source issue, all-state issues, all-state pull requests, and full commit list, runs Codex in the read-only sandbox with the triage schema, uploads the triage evidence artifact, posts the single verdict comment from a `run:` step, and applies tracker labels only when the JSON says `create_tracker` is true for a bug or performance marker.
2. **reproduce** uses `needs: triage` and runs only when that output marker is `[intake:bug]` or `[intake:performance]`. It snapshots the issue, all-state issues, all-state pull requests, and full commit list before Codex runs. After Codex returns, it uploads local proof files named in `evidence_paths` before it posts an optional source comment or opens a draft pull request. Retry branches include both `GITHUB_RUN_ID` and `GITHUB_RUN_ATTEMPT`.

Codex never posts, never commits, never calls the network. The workflow is the coordinator and the only external writer.

Shared rules, unchanged:

- Source coordinates are immutable after freeze.
- Fail closed on missing config, missing adapter capability, or mismatched source.
- `source.repository` uses the `owner/repo` slug format from `GITHUB_REPOSITORY`, not a GitHub URL.
- The coordinator is the only external writer.
- Never merge or deploy.
- Exactly one verdict comment carrying exactly one marker.
- A tracker write only for a clear new bug.
- Reproduce gated on the marker.
- Double reproduction on the real interface through the seven-operation control adapter against a user-owned feature map.
- Verify an existing fix instead of racing it.
- A draft-only pull request after before-and-after proof.

## Install

1. Copy the files above into the target repository.
2. Fill <code>.github/cstack/intake/configuration.yaml</code>. Set `source.repository` and `repository.slug` to the same `owner/repo` value as `GITHUB_REPOSITORY`. Secrets stay in the GitHub Actions secret store or in the Codex CLI login. Do not put token values in the YAML.
3. Copy [references/control-adapter.md](references/control-adapter.md) requirements onto a control adapter you own. Fill the feature map. Run the nine-step adapter smoke in that file before enabling reproduce.
4. Register any extra connectors with `codex mcp add`, then `codex mcp list` to confirm. Declare the same names under `[mcp_servers.<name>]` in user `~/.codex/config.toml` or a trusted project `.codex/config.toml`.
5. Store `OPENAI_API_KEY` as a repository secret if the workflow uses API-key auth. Local `codex exec` reuses saved CLI auth.
6. Commit. Enable the workflow. Confirm a test issue stays on the original issue thread: the verdict is a comment, never a new issue.

Both Codex steps use `sandbox: read-only`. The model cannot write `.git` and cannot use the network. The workflow `run:` steps hold `GITHUB_TOKEN` and perform every external write. Neither job merges.

Leave `allow-users` empty unless you want outside reporters to pass the action write-access check. Collaborators pass by default. A maintainer can still run `workflow_dispatch` with the issue number.

## Runner map

Values under `runner` in the configuration file map onto measured `codex exec` flags and `openai/codex-action@v1` inputs.

| Config key | `codex exec` | Action input |
| --- | --- | --- |
| `sandbox` | `-s` / `--sandbox` | `sandbox` |
| `working_directory` | `--cd` | `working-directory` |
| `output_last_message` | `-o` / `--output-last-message` | `output-file` |
| `extra_args` (`--json`) | those flags | `codex-args` |
| `output_schema_file_triage` | `--output-schema` | `output-schema-file` |
| `output_schema_file_reproduce` | `--output-schema` | `output-schema-file` |
| `permission_profile` | `default_permissions` in config.toml | `permission-profile` |
| `safety_strategy` | not a CLI flag | `safety-strategy` |
| `allow_users` | not a CLI flag | `allow-users` |
| `allow_bots` | not a CLI flag | `allow-bots` |
| `model` | `-m` when nonempty | `model` |
| `effort` | not set by this pack when empty | `effort` |

Leave `model` and `effort` empty to inherit the runner default. Do not put a model slug in the committed YAML. `permission_profile` and `sandbox` are mutually exclusive on the action; leave `permission_profile` empty when `sandbox` is set.

Do not put `-c sandbox_workspace_write.*` or `--add-dir` in `codex-args`. The action rejects `--add-dir` under `drop-sudo`. The model does not receive `GH_TOKEN`.

The action also accepts inline `output-schema`. This pack uses `output-schema-file`.

Local smoke, from a git repository, after the copies exist:

```sh
codex exec --cd . -s read-only --output-schema .github/cstack/intake/schemas/triage-result.schema.json -o /tmp/intake-last.json --json "Read .github/cstack/intake/prompts/triage.md and return the JSON object the schema requires. Do not post."
```

## Limits

Codex CLI has no inbound webhook receiver. A Slack event, a Linear webhook, or a custom HTTP POST does not start a run.

Codex CLI has no scheduler. `notify` and lifecycle hooks fire during a run. They do not start one. ChatGPT Scheduled tasks are not the CLI.

There is no resident wait. `codex exec` is one turn. It does not stay alive to watch a thread.

There is no rejection window. `budgets.rejection_window_minutes` is unused on GitHub Actions. A later human comment is a new event, not a live wait.

`GITHUB_TOKEN`-authored comments do not retrigger workflows. A verdict comment posted by `github-actions[bot]` never starts an `issue_comment` run. This workflow does not listen for that event.

An outside reporter needs the action `allow-users` input or a maintainer `workflow_dispatch`. The action write-access check rejects events whose actor lacks write access.

The read-only sandbox gives the model no network and no `.git` write. Measured locally with `codex sandbox -c sandbox_mode="workspace-write"`: `curl` exited 6 and `git commit` exited 128. This pack uses `read-only`, which is stricter.

`--add-dir` is rejected by `openai/codex-action` under the default `drop-sudo` safety strategy. Do not pass it in `codex-args`.

The control adapter is not bundled. You must supply a session browser, simulator, or MCP server that implements all seven operations in [references/control-adapter.md](references/control-adapter.md). Missing capability is a block, not a unit-test substitute. With no network in the sandbox, an adapter that needs the network is a block.

Tracker writes on GitHub go through `gh` in the workflow with `GITHUB_TOKEN`. This pack does not create a Linear client.

You must supply: a filled configuration file, the GitHub Actions workflow, runner credentials, a completed feature map, a control adapter that passes the nine-step smoke, and any MCP servers named in the configuration.

# Native Codex runtime contract

Read this when a cstack skill is explicitly invoked. It applies to the current task and its delegates, not to every project or future task. User instructions, project AGENTS.md, Codex mode and tool permissions take precedence. This file is the shared definition of runtime behavior; companion files must not weaken it.

## Activation and routing

`$cstack` activates the main workflow in this task until the user says to stop cstack. A specific `$skill` runs only that capability. Every bundled skill has `policy.allow_implicit_invocation: false` in its `agents/openai.yaml`; installation alone does not activate the mode. If the interface requires disambiguation, select the skill from the cstack plugin.

Read a routed skill's SKILL.md from the same installed bundle. From the main skill, a sibling is `../<skill-name>/SKILL.md`. Follow its relevant references. Do not require a slash-command dispatcher or another plugin. Persist an active mode only in the current conversation/checkpoint, never in global AGENTS.md or config. In Plan mode, investigate and produce a plan without implementing or publishing it.

## Tools and delegation

Use the actual tools exposed in the current session. Native tool names differ between App and CLI; inspect the available schema rather than constructing a Cursor Task call or inventing a tool.

- Read/search with native filesystem tools or `rg`; run commands with the native shell tool.
- For independent useful slices, use Codex native spawn, message, wait and interrupt tools. Send a bounded prompt, owned files, the cstack agent prompt and acceptance checks. A named custom agent is not required: use an available native generic agent with those instructions. Agent prompts are `agents/cstack-agent.md` and `agents/comment-reviewer.md`, relative to this document.
- Let the parent integrate results and verify actual diffs. Independent implementations use separate worktrees or output paths; do not have concurrent agents write the same files. Use the current session's concurrency limit and queue excess work.
- With no available subagent capability, execute slices sequentially and label the result as a single-agent pass. Do not describe a self-review as an independent review or claim parallel execution.
- A read-only assignment stays read-only even when the tool would permit mutation. MCP access does not depend on setting a fictional `readonly: false` field.
- Use structured user input when available for missing product decisions; otherwise one concise question. Discoverable facts are the agent's job. Reuse authorization already given for the concrete task.

## Models

No model name is required. Inherit the parent model and effort unless the user configured an available override. Do not force a model family, provider, plan, API key or custom role installation.

Optional project configuration: `.cstack/models.json`, a JSON object mapping role labels to model strings, or lists of strings for panels. The role labels match the setup skill. Missing roles and `inherit-parent` inherit. Panel list length is the requested number of attempts, bounded by native concurrency. The `architect runners` panel requires at least two entries. Distinct independent perspectives remain useful on one model, but do not call them a cross-model review.

Use only names confirmed by the current tool schema or authoritative session model list. A local stale cache is not proof of entitlement. If an override cannot be verified or the session rejects it, report the specific unavailable selection and request a supported choice or permission to inherit; continue independent work. Never silently substitute a different explicitly requested model. If model discovery is unavailable, inheritance still works. Read configuration before spawning; malformed JSON or invalid value shapes are configuration errors, not permission to ignore a requested override.

## State, helper scripts and resumption

Use the target workspace `.cstack/` for generated state. Keep each task's checkpoint, decisions and orchestration store in a separate task-specific subdirectory. Use a known task ID or create a unique directory. The checkpoint names the goal, authorized actions, branch/worktree, current commit, completed checks, outstanding work and artifact paths. Do not include credentials or unrelated conversation content.

Run helper scripts through the plugin's writable launcher:

```sh
bash <plugin-root>/scripts/run-tool.sh watch-pr/watch-pr --help
bash <plugin-root>/scripts/run-tool.sh orch/orch.ts --help
bash <plugin-root>/scripts/run-tool.sh worktree-audit.sh
```

`<plugin-root>` is the absolute path to the installed cstack bundle, resolved from the skill location. The launcher creates a fresh temporary copy of trusted helper sources under `.cstack/tools/` for each invocation, installs frozen dependencies there, executes, and cleans up. It never reuses project-local executable caches; independent invocations run in separate directories. Its working directory remains the target project. Bun and the locked upstream dependencies are used for TypeScript helpers, bash for shell helpers. Package installation needs registry access or an already populated Bun package cache. GitHub workflows additionally require authenticated `gh` and `git`. Missing tools produce an explicit prerequisite message; do not pretend a check ran. Never install packages into the plugin cache. When adding local state to a repository, keep `.cstack/` out of commits without replacing existing ignore rules.

Use native task-history tools when exposed, constrained to the current workspace and requested time/topic. Otherwise use the current conversation, an explicit transcript supplied by the user or a cstack checkpoint. Only read local session files after matching their recorded workspace/session metadata; never scan unrelated projects or assume a Cursor transcript layout. Report missing history rather than inventing it.

Native waits and foreground continuation support active work. A Codex goal is created only when explicitly requested. A native scheduled task is configured only when requested and the necessary scheduler is exposed. Without a scheduler, report the limit and leave a checkpoint; do not launch a hidden daemon or promise work after Codex exits. Local child agents do not become durable cloud workers. On resumption, verify current git/PR state instead of trusting a previous completion message or a stale agent ID.

## External integrations and authorization

No external integration is required for basic code work. Discover connected GitHub, issue tracker, documentation, browser and other tools only when the task needs them. Missing connectors are explicit evidence gaps; do not auto-install plugins or request unrelated accounts.

Use available browser/computer tools for UI verification, or a project's existing harness. If no UI tool is available, report the missing runtime evidence. Do not claim a screenshot or test that was not produced. Skill authoring can use the system skill-creator if available; otherwise write a self-contained SKILL.md and validate its metadata and behavior directly. Code cleanup uses the repository's formatter/linter and a scoped review, without requiring a separate cleanup plugin.

Activating a workflow does not authorize posting messages, opening PRs, merging, publishing, deploying or deleting data. Perform these only within the user's concrete request and available permissions. Status checks and reviews do not imply permission to merge. No automatic permission handoff for work already authorized. Read-only checks must not enable auto-merge or change PR state. Missing or unrecognized CI/review evidence must fail closed.

## Platform limits

Grok Bot webhooks and Cursor's event-driven Benny pack have no drop-in implementation here. Their notices link to the original source; they are not silently activated. Equivalent manual bug investigation can use available Codex tools without claiming a webhook service.

Native custom-agent TOML discovery is separate from plugin skills. This plugin passes prompt resources to available subagents and installs no global roles or model settings. See the official [subagent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents) and [plugin packaging contract](https://developers.openai.com/plugins/build/plugins).

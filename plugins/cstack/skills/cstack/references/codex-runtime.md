# Native Codex runtime contract

Read this when a cstack skill is explicitly invoked. It applies to the current task and its delegates, not to every project or future task. User instructions, project AGENTS.md, Codex mode and tool permissions take precedence. This file is the shared definition of runtime behavior; companion files must not weaken it.

## Activation and routing

Codex registers plugin skills as `cstack:<skill-name>`. Literal prompt text must use the full identifier, for example `$cstack:cstack` or `$cstack:architect`. In an interactive skill picker, typing `$cstack` and selecting the displayed **cstack** skill supplies a structured selection with its actual name and path. An unselected shorthand in raw text is not equivalent to that selection.

`$cstack:cstack` activates the main workflow in this task until the user says to stop cstack. A specific `$skill` runs only that capability. Every bundled skill has `policy.allow_implicit_invocation: false` in its `agents/openai.yaml`; installation alone does not activate the mode. If the interface requires disambiguation, select the skill from the cstack plugin.

Read a routed skill's SKILL.md from the same installed bundle. From the main skill, a sibling is `../<skill-name>/SKILL.md`. Follow its relevant references. Do not require a slash-command dispatcher or another plugin. Persist an active mode only in the current conversation/checkpoint, never in global AGENTS.md or config. In Plan mode, investigate and produce a plan without implementing or publishing it.

The 23 principles live in `principles/` beside this runtime contract. They are supporting references, not separately registered skills. Read one through its caller's link when its condition applies or the user names that principle. Resolve links relative to the file containing them; do not load all principles or look for their removed skill entrypoints.

Project setup may create a passive, delimited cstack block in the project's `AGENTS.md` and project guidance in `docs/agents/cstack.md`. Read that guidance only when cstack is explicitly selected. Setup preserves surrounding instructions and does not activate cstack, create native goals or change global files. Existing `CLAUDE.md` is preserved; a project may reference its shared instructions without duplicating them. The project's documentation conventions may place an authorized glossary or ADR outside `.cstack/`; operational maps, checkpoints and transient evidence remain inside `.cstack/`.

When the user selects `$cstack:cstack`, its coordinator automatically uses `clarify` for material unresolved requirements and `horizon` for large goals needing a durable map across phases, PRs, or sessions. Clear ordinary work goes directly to its playbook. Preparation can use `domain` for material vocabulary decisions; `audit-architecture` remains a focused requested survey. These routes stay inside the explicit cstack task and do not activate in unrelated work.

After routed preparation resolves, the cstack coordinator continues the already-authorized playbook without another phase approval. Horizon can return successive eligible autonomous prerequisites to that coordinator; unresolved human decisions remain open. Directly selected preparation skills retain their bounded scope. Plan/read-only requests return drafts without file writes or implementation. None of these routes automatically creates a native goal, scheduler, remote ticket, PR, merge, or deployment authorization.

## Tools and delegation

Use the actual tools exposed in the current session. Native tool names differ between App and CLI; inspect the available schema rather than constructing a Cursor Task call or inventing a tool.

- Read/search with native filesystem tools or `rg`; run commands with the native shell tool.
- For independent useful slices, use Codex native spawn, message, wait and interrupt tools. Send a bounded prompt, owned files, the cstack agent prompt and acceptance checks. A named custom agent is not required: use an available native generic agent with those instructions. Agent prompts are `agents/cstack-agent.md` and `agents/comment-reviewer.md`, relative to this document.
- Let the parent integrate results and verify actual diffs. Independent implementations use separate worktrees or output paths; do not have concurrent agents write the same files. Use the current session's concurrency limit and queue excess work.
- With no available subagent capability, execute slices sequentially and label the result as a single-agent pass. Do not describe a self-review as an independent review or claim parallel execution.
- A read-only assignment stays read-only even when the tool would permit mutation. MCP access does not depend on setting a fictional `readonly: false` field.
- Use structured user input when available for missing product decisions; otherwise one concise question. Discoverable facts are the agent's job. Reuse authorization already given for the concrete task.

## Models

The parent session keeps its own model. Delegates inherit model and effort unless the user selects a project override. Setup offers optional recommendations, never mandatory model names, providers, plans, API keys or global custom roles.

`.cstack/models.json` maps the setup skill's role labels to legacy model strings, `inherit-parent`, or objects with exactly `model` and `reasoning_effort`. Panels are nonempty lists of those selections. Missing `simple edits` falls back to `feature, refactoring`; missing `documentation` falls back to `judgment and prose`. Other missing roles inherit. Missing panels default to three attempts, except `arena cross-judge pool` defaults to one judge. `architect runners` requires at least two entries. Queue attempts beyond native concurrency; do not claim model diversity from independent passes on one model.

When `.cstack/models.json` is absent and the caller supplied no override, inherit directly using the panel defaults above; no helper, Python or model discovery is needed. With configuration present, resolve the role using the trusted installed helper. Discover the catalog from the current tool schema or authoritative session model list once per task and reuse it while the session capabilities remain unchanged:

```sh
python3 <absolute-plugin>/skills/setup-cstack/scripts/models.py --workspace <workspace> --catalog <live-catalog.json> resolve '<role>'
```

Catalog formats and setup are documented in [setup-cstack](../../setup-cstack/SKILL.md). The result is a list of native selections: `{}` for inheritance, `{ "model": "..." }` for a legacy string, or `{ "model": "...", "reasoning_effort": "..." }` for an explicit pair. Forward each complete selection through every caller, panel and final spawn. Legacy strings leave effort to host rules; never invent an effort for them. An explicitly supplied specialized role or panel takes precedence over generic Swarm or Arena defaults.

Inspect the actual spawn schema before applying overrides. On native App collaboration, use an available generic agent type whose settings are not locked, and `fork_turns: "none"` or a supported partial fork when supplying `model` or `reasoning_effort`; full-history forks cannot take these overrides. Supply the necessary context explicitly. Other hosts, including CLI, must expose a real way to configure the selected fields. If an explicit effort cannot be expressed, report that capability gap and request a supported selection or permission to inherit. Prompt text is not model configuration. Never silently drop effort, inherit or substitute a requested model. Inheritance uses the host's normal fork behavior.

Use only model/effort pairs confirmed available now; a stale cache or saved choice does not prove entitlement. Malformed configuration, unknown explicit choices and rejected dispatches are errors to report, not permission to ignore an override. Continue independent work while a selection is blocked. Without discovery inheritance still works. Setup does not launch model tests or modify global configuration.

## State, helper scripts and resumption

Use the target workspace `.cstack/` for generated state. Keep each task's checkpoint, decisions and orchestration store in a separate task-specific subdirectory. Use a known task ID or create a unique directory. The checkpoint names the goal, authorized actions, branch/worktree, current commit, completed checks, outstanding work and artifact paths. Do not include credentials or unrelated conversation content.

When creating a temporary worktree, record its absolute path, branch, owning task/unit and agents in that checkpoint. Attach its PR and merged-head receipt when available, and identify task-created disposable outputs and evidence to preserve. Existing or reused worktrees are not automatically owned. Writers and verifiers report release only after their descendants and processes no longer need the path. The coordinator owns removal under [worktree cleanup](../playbooks/worktree-cleanup.md); preserve the checkpoint and evidence in a surviving workspace before removing their original worktree.

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

An authorized merge-and-deliver task includes the cleanup playbook's safe removal of its own temporary, integrated, released worktrees. No extra confirmation is needed for that bounded finalization. This does not authorize discarding unsaved work, deleting branches, cleaning unrelated worktrees or overriding a retention request.

## Platform limits

Grok Bot webhooks and Cursor's event-driven Benny pack have no drop-in implementation here. Their notices link to the original source; they are not silently activated. Equivalent manual bug investigation can use available Codex tools without claiming a webhook service.

Native custom-agent TOML discovery is separate from plugin skills. This plugin passes prompt resources to available subagents and installs no global roles or model settings. See the official [subagent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents) and [plugin packaging contract](https://developers.openai.com/plugins/build/plugins).

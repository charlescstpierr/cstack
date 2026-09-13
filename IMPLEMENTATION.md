# cstack port

Approved target: private GitHub repository `charlescstpierr/cstack`, full port of `cursor/plugins/pstack` commit `889ec4b68fa5aab0e867dad71ec3fdf386ae48f3` (pstack 0.15.2), Codex App and CLI, explicit activation with `$cstack:cstack`, no external orchestration runtime.

## Delivery checklist

- [x] Package one plugin under `plugins/cstack` and a repository marketplace.
- [x] Account for the 47 upstream skills as 23 principle references plus the remaining specialized skills, 23 core playbooks, two agent prompts, the dormant automation pack, and the original `deslop` skill (29 skills in the 0.4.0 catalog).
- [x] Port main router/playbooks to native tools, preserve scope and authorization boundaries.
- [x] Port supporting skills/references; explicitly document unavailable integrations.
- [x] Replace Graphite frontier resolution with git/gh; preserve head-SHA verification gates.
- [x] Stage helper scripts in writable project state instead of mutating plugin caches.
- [x] Validate manifests, skill metadata, reference paths and upstream coverage.
- [x] Run existing and targeted tests, typecheck, independent review and realistic skill checks.
- [x] Publish privately, verify clean GitHub installation and new-session discovery.

## Shared contracts

- Main skill directory/name: `cstack`; setup skill: `setup-cstack`. Other skill slugs remain unchanged and their descriptions use Codex `$skill` syntax.
- All skill invocation policies are explicit-only. The router directly reads bundled skill paths relative to itself when a workflow calls for them.
- Every entrypoint links to `plugins/cstack/skills/cstack/references/codex-runtime.md` with a relative link. This shared contract describes native tool selection and local state.
- Agent roles ship as Markdown prompts under the main skill's `references/agents`; pass their instructions to available native subagents. Do not assume named roles are registered.
- State lives under the target workspace `.cstack/`, never a Cursor store or installed plugin cache. Model overrides use `.cstack/models.json`: an object mapping upstream role labels to a model string or, for panels, a list of strings. Missing entries and `inherit-parent` inherit; validate real model names against the current session. Do not invent a model-list API. Core usage works without setup.
- Helpers retain Bun and locked upstream packages. Root supplies `plugins/cstack/scripts/run-tool.sh`, which stages trusted helper sources to a fresh temporary directory under `.cstack/tools/` for each invocation, installs locked dependencies there, executes, and cleans up. Arguments and target cwd are preserved. Parallel invocations share no executable workspace state. Bun's ordinary package cache avoids repeated downloads. No installation into the plugin cache.
- GitHub workflows use git/gh. Stack resolution follows PR head/base relationships starting from the current branch, rejects ambiguous/cyclic/missing relations, and retains actual head SHA verification.
- Use native foreground continuation/waits. Scheduled resumption is conditional on an available native scheduler and explicit user request. Do not promise that local agents survive application exit. Cloud-only Cursor behavior, Grok webhook UI and event-driven Benny automation are documented limitations, never executable placeholders.
- No automatic external messages, PR creation, merges, publication, destructive operations or unrelated skill edits based solely on activating a mode. Honor authorization already given for the concrete task.
- README and short user guide are French; skill instructions stay English. Runtime docs must be self-contained, no required companion plugin.

## Execution ownership

- Root: plugin packaging, shared runtime contract, writable launcher, setup, validation, installation and release.
- Supporting-skill lane: all skills except cstack and setup-cstack, including their resources and scripts; unsupported integration notices.
- Router lane: main SKILL.md, playbooks and main-skill references except codex-runtime.md and agent prompts.
- Helper lane: main-skill scripts only, Graphite replacement and tests.

Baseline and verification evidence is recorded in `docs/VERIFICATION.md` when complete. This plan is documentation, not an installed workflow dependency.

Ruling after independent review: persistent project-local executable caches can be pre-populated or modified, including dependencies and bootstrap markers. Use fresh per-invocation temporary staging instead of trusting an existing digest directory. This also removes serialization between helper executions; it costs a cached dependency installation per invocation.

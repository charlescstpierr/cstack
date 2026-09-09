# cstack port

Approved target: private GitHub repository `charlescstpierr/cstack`, full port of `cursor/plugins/pstack` commit `27e2a62ff94f9af4b5e68435e41cdceacadb840c`, Codex App and CLI, explicit activation with `$cstack`, no external orchestration runtime.

## Delivery checklist

- [ ] Package one plugin under `plugins/cstack` and a repository marketplace.
- [ ] Account for all 47 upstream skills, 23 core playbooks, two agent prompts and the dormant automation pack.
- [ ] Port main router/playbooks to native tools, preserve scope and authorization boundaries.
- [ ] Port supporting skills/references; explicitly document unavailable integrations.
- [ ] Replace Graphite frontier resolution with git/gh; preserve head-SHA verification gates.
- [ ] Stage helper scripts in writable project state instead of mutating plugin caches.
- [ ] Validate manifests, skill metadata, reference paths and upstream coverage.
- [ ] Run existing and targeted tests, typecheck, independent review and realistic skill checks.
- [ ] Publish privately, verify clean GitHub installation and new-session discovery.

## Shared contracts

- Main skill directory/name: `cstack`; setup skill: `setup-cstack`. Other skill slugs remain unchanged and their descriptions use Codex `$skill` syntax.
- All skill invocation policies are explicit-only. The router directly reads bundled skill paths relative to itself when a workflow calls for them.
- Every entrypoint links to `skills/cstack/references/codex-runtime.md` with a relative link. This shared contract describes native tool selection and local state.
- Agent roles ship as Markdown prompts under the main skill's `references/agents`; pass their instructions to available native subagents. Do not assume named roles are registered.
- State lives under the target workspace `.cstack/`, never a Cursor store or installed plugin cache. Model overrides use `.cstack/models.json`: an object mapping upstream role labels to a model string or, for panels, a list of strings. Missing entries and `inherit-parent` inherit; validate real model names against the current session. Do not invent a model-list API. Core usage works without setup.
- Helpers retain Bun and locked upstream packages. Root supplies `scripts/run-tool.sh`, which stages main-skill helper sources to `.cstack/tools/<source-digest>/`, then runs the requested helper. Arguments are forwarded unchanged; cwd remains the target workspace. Workflows use this launcher. No installation into the plugin cache.
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

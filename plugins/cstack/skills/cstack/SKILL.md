---
name: cstack
description: "Explicit cstack workflow router for concise prose, deliberate native Codex subagents, simple code, and verified work. Use only when the user invokes $cstack."
---

# cstack

Apply cstack to the task that explicitly invoked `$cstack` until the task completes or the user stops cstack. Do not persist these instructions into unrelated work.

Read [the Codex runtime contract](references/codex-runtime.md) before choosing tools, subagents, models, state, or continuation behavior. Resolve paths in this skill relative to this file. Use the native tools that the current session exposes. Do not assume that a named agent role, scheduler, browser driver, model, or external integration exists.

## Route the work

Read the matched playbook in full and copy its steps into the current plan before task-specific steps. Keep a skipped step with `skip: <reason>`.

- Read `playbooks/investigation.md` for a read-only explanation, comparison, or design question.
- Read `playbooks/bug-fix.md` for a reported defect that needs reproduction, diagnosis, and a fix.
- Read `playbooks/perf-issue.md` for one measured performance defect.
- Read `playbooks/hillclimb.md` for repeated improvement of one metric against a target.
- Read `playbooks/runtime-forensics.md` for diagnosis from a running process.
- Read `playbooks/trace-forensics.md` for diagnosis from a captured profile or trace.
- Read `playbooks/feature.md` for new or changed behavior.
- Read `playbooks/refactoring.md` for a behavior-preserving structural change.
- Read `playbooks/prototype.md` for a disposable experiment that settles an observable question.
- Read `playbooks/visual-parity.md` for pixel-level UI comparison.
- Read `playbooks/authoring-a-skill.md` for creating or changing a skill.
- Read `playbooks/eval.md` for measuring how a skill, prompt, or structure changes agent behavior.
- Read `playbooks/babysit.md` when the user asks to inspect or drive a PR to merge-ready.
- Read `playbooks/shipping.md` when the user has authorized landing or shipping verified PRs.
- Read `playbooks/autonomous-run.md` for one long task with a checkable exit condition.
- Read `playbooks/orchestrate.md` for a standing program with multiple owners and PRs.
- Read `playbooks/autopilot-full.md` for an authorized queue of independent PRs that owners may merge after verification.
- Read `playbooks/autopilot-stack.md` for a queue delivered as one verified linear stack that the operator lands.
- Read `playbooks/session-pickup.md` to resume work from local state, a branch, or conversation context.
- Read `playbooks/pause-safely.md` to leave local work in a resumable state.
- Read `playbooks/multi-phase-plan.md` for a plan that spans phases or PRs.
- Read `playbooks/worktree-cleanup.md` for disk inspection and authorized cleanup of worktrees or simulators.
- Read `playbooks/opening-a-pr.md` only when the user has authorized creating a PR. Other playbooks may prepare a reviewable branch without creating one.

If no playbook fits, read and apply `../figure-it-out/SKILL.md`. Use `playbooks/orchestrate.md` only when the work is a continuing program rather than one session-sized task.

## Apply the common rules

### Understand before editing

- For a nontrivial change or architecture question, read and apply `../how/SKILL.md`.
- Before writing stateful or branching code, name the data shape and read `../principle-model-the-domain/SKILL.md`.
- Before code crosses a new function or module boundary, read `../architect/SKILL.md`.
- For a disputed design, read `../interrogate/SKILL.md` when native subagents and the requested model choices are available. Otherwise make the best evidence-backed decision in the foreground and record the missing comparison.
- For a large migration or an unmatched workflow, read `../figure-it-out/SKILL.md`.

### Keep the implementation small

Read a principle only when its trigger applies, then name the concrete decision it changed in the final report.

- Read `../principle-laziness-protocol/SKILL.md` before a refactor or a new abstraction.
- Read `../principle-subtract-before-you-add/SKILL.md` before a rewrite or migration.
- Read `../principle-minimize-reader-load/SKILL.md` when control flow or state is hard to trace.
- Read `../principle-redesign-from-first-principles/SKILL.md` when a new requirement changes the design's foundation.
- Read `../principle-foundational-thinking/SKILL.md` before choosing core types, shared state, or implementation order.
- Read `../principle-attack-the-premise/SKILL.md` after two fixes fail for the same assumed reason.
- Read `../principle-outcome-oriented-execution/SKILL.md` for a phased rewrite or migration with a fixed target shape.
- Read `../principle-experience-first/SKILL.md` for a product or interaction tradeoff.
- Read `../principle-exhaust-the-design-space/SKILL.md` when a novel choice needs competing prototypes.
- Read `../principle-build-the-lever/SKILL.md` when a small repeatable tool can perform or prove the work better than manual edits.

### Keep boundaries explicit

- Read `../principle-boundary-discipline/SKILL.md` for validation, external APIs, CLI input, config, and framework adapters.
- Read `../principle-type-system-discipline/SKILL.md` when designing a typed data shape or signature.
- Read `../principle-make-operations-idempotent/SKILL.md` for commands or loops that can retry after partial progress.
- Read `../principle-migrate-callers-then-delete-legacy-apis/SKILL.md` when replacing an internal API.
- Read `../principle-separate-before-serializing-shared-state/SKILL.md` when concurrent actors may write the same branch, file, or state.

### Verify real behavior

- Read `../principle-prove-it-works/SKILL.md` before claiming completion.
- Read `../principle-fix-root-causes/SKILL.md` for a defect.
- Read `../principle-sequence-verifiable-units/SKILL.md` for multi-step work.
- Read `../principle-test-behavior-not-implementation/SKILL.md` when adding or changing tests.
- Read `../principle-encode-lessons-in-structure/SKILL.md` when the same correction appears twice.
- Read `../principle-never-block-on-the-human/SKILL.md` before asking about a reversible or discoverable choice.
- Read `../principle-guard-the-context-window/SKILL.md` before loading a large artifact or broad fan-out into the parent task.
- Read `../no-comments/SKILL.md` before code review.
- Read `../unslop/SKILL.md` for every prose artifact and reply.
- Read `../technical-writing/SKILL.md` for documentation, plans, PR text, and commit text.

### Use native subagents deliberately

Follow [the runtime contract](references/codex-runtime.md). Give each native subagent a bounded task, file ownership, acceptance criteria, and the instructions from `references/agents/cstack-agent.md`. The parent owns integration and verification.

For coverage across independent areas, read and apply `../swarm/SKILL.md`. For competing implementations or designs, read and apply `../arena/SKILL.md`. Parallelize only independent work. One actor writes a branch or shared file at a time.

Bound panels to native capacity. A panel with no `.cstack/models.json` entry defaults to three independent inherited-model attempts. A cross-judge pool defaults to one inherited-model judge. Run excess attempts in waves. If a playbook asks for more lanes than the work justifies, preserve each distinct scenario and mark redundant lanes `n/a` with a reason.

Models inherit from the parent by default. If `.cstack/models.json` supplies a role or panel override, validate that explicit model against models already known to the current session. If the model is unavailable, stop that selection and report it. Never guess a substitute or invent a model-list command.

Use `judgment and prose` for generic prose or judgment delegates that are not assigned a specialized skill role. Use `hardest tasks` for explicitly identified cross-cutting designs, difficult concurrency fixes, or subtle algorithmic code delegates; that classification replaces the ordinary code-role selection for that delegate. Other code delegates use the matched playbook's role. Specialized investigators, synthesizers and panels use their named setup roles.

### Keep state local

Write durable workflow state only under the target workspace's `.cstack/` directory. Do not write to an installed plugin cache. The root launcher is `../../scripts/run-tool.sh` relative to this file. Resolve the plugin root first, then run helpers as:

```bash
bash <plugin-root>/scripts/run-tool.sh orch/orch.ts <args>
bash <plugin-root>/scripts/run-tool.sh watch-pr/watch-pr <args>
bash <plugin-root>/scripts/run-tool.sh worktree-audit.sh <args>
```

Each invocation stages trusted helper sources in a fresh temporary directory under `.cstack/tools/`, installs frozen dependencies there, executes, and cleans up. It forwards arguments without changing the target working directory and never executes a preexisting project-local copy.

### Respect authority

Activation does not authorize an external message, PR creation, merge, publication, deployment, destructive action, or work outside the user's scope. Prepare reversible local work and evidence first. Use authorization already present in the conversation. Honor Codex Plan mode and the current permission boundary.

Continue foreground work while the session is active. Use a native scheduler only when the session exposes one and the user requested scheduled continuation. Do not promise background or app-closed survival.

For long, autonomous, or multi-phase work, read and apply `../show-me-your-work/SKILL.md` and keep its trail under `.cstack/`. If a bundled skill breaks during the task, fix it only when it is in scope or blocks the current goal. Otherwise record a proposed follow-up without creating a PR.

Keep comments only for a non-obvious reason that the code cannot express. Preserve licenses, public contracts, accessibility rationale, and verified tool constraints. Read `references/agents/comment-reviewer.md` for a dedicated comment review.

### Write the report

Lead with the user-visible result. State what changed, the evidence, and any real limit. Link only artifacts read or produced in the current task. Use a full GitHub PR URL when a PR exists.

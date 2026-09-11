---
name: cstack
description: "Explicit cstack workflow router for concise prose, deliberate native Codex subagents, simple code, and verified work. Use only when the user invokes $cstack:cstack."
---

# cstack

Apply cstack to the task that explicitly invoked `$cstack:cstack` until the task completes or the user stops cstack. Do not persist these instructions into unrelated work.

Read [the Codex runtime contract](references/codex-runtime.md) before choosing tools, subagents, models, state, or continuation behavior. Resolve paths in this skill relative to this file. Use the native tools that the current session exposes. Do not assume that a named agent role, scheduler, browser driver, model, or external integration exists.

## Route the work

Read the matched playbook in full, then plan only the steps the task needs. Keep skipped-step notes only when omitting the step would otherwise hide a real risk, tradeoff, or authorization boundary.

Before choosing the direct path, classify the task's observable uncertainty and risk. Clear routine work stays in the parent. Extra reads and native subagents earn their place by producing new evidence, settling a decision, or giving independent verification; do not optimize for fewer calls when quality, safety, or review separation needs them.

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

### Optional preparation

These routes run only when the user selects the named skill or asks for its specific preparation activity. An ordinary implementation, review, or bug request keeps its existing playbook; do not add an interview, domain-writing phase, or decision map to it.

- Read and apply `../clarify/SKILL.md` for an explicitly requested requirements discussion.
- Read and apply `../domain/SKILL.md` for explicitly requested vocabulary or domain-decision work. Read-only requests produce drafts without changing project documents.
- Read and apply `../horizon/SKILL.md` when the user explicitly asks to map a large uncertain objective over multiple sessions. Its human decision gates remain in force; it does not automatically start implementation or a native goal.
- Read and apply `../audit-architecture/SKILL.md` for an explicitly requested read-only survey of architectural improvement opportunities.

If `docs/agents/cstack.md` exists, consult its project conventions while cstack is active. It is optional and must not activate cstack or override the current request, mode, or permissions. A configured issue tracker describes where authorized work is recorded, not permission to create or change remote issues.

## Apply the common rules

### Understand before editing

- For a nontrivial change or architecture question where the current implementation is not already clear, read and apply `../how/SKILL.md`. Once `how` is selected, preserve its configured explainer path. Simple local inspection can stay in the parent without invoking that specialist.
- Before writing stateful or branching code, name the data shape and read [Model the Domain](references/principles/model-the-domain.md).
- Before code crosses a new function or module boundary with meaningful design choice, read `../architect/SKILL.md`. Routine placement that follows an existing local pattern can stay in the parent.
- For a disputed design, read `../interrogate/SKILL.md` when native subagents and the requested model choices are available. Otherwise make the best evidence-backed decision in the foreground and record the missing comparison.
- For a large migration or an unmatched workflow, read `../figure-it-out/SKILL.md`.

### Keep the implementation small

Read a principle only when its trigger applies or the user names it. Do not load the whole directory. Report decisions when they help explain the result, without an inventory of applied principles.

- Read [Laziness Protocol](references/principles/laziness-protocol.md) before a refactor or a new abstraction.
- Read [Subtract Before You Add](references/principles/subtract-before-you-add.md) before a rewrite or migration.
- Read [Minimize Reader Load](references/principles/minimize-reader-load.md) when control flow or state is hard to trace.
- Read [Redesign From First Principles](references/principles/redesign-from-first-principles.md) when a new requirement changes the design's foundation.
- Read [Foundational Thinking](references/principles/foundational-thinking.md) before choosing core types, shared state, or implementation order.
- Read [Attack the Premise](references/principles/attack-the-premise.md) after two fixes fail for the same assumed reason.
- Read [Outcome-Oriented Execution](references/principles/outcome-oriented-execution.md) for a phased rewrite or migration with a fixed target shape.
- Read [Experience First](references/principles/experience-first.md) for a product or interaction tradeoff.
- Read [Exhaust the Design Space](references/principles/exhaust-the-design-space.md) when a novel choice needs competing prototypes.
- Read [Build the Lever](references/principles/build-the-lever.md) when a small repeatable tool can perform or prove the work better than manual edits.

### Keep boundaries explicit

- Read [Boundary Discipline](references/principles/boundary-discipline.md) for validation, external APIs, CLI input, config, and framework adapters.
- Read [Type System Discipline](references/principles/type-system-discipline.md) when designing a typed data shape or signature.
- Read [Make Operations Idempotent](references/principles/make-operations-idempotent.md) for commands or loops that can retry after partial progress.
- Read [Migrate Callers Then Delete Legacy APIs](references/principles/migrate-callers-then-delete-legacy-apis.md) when replacing an internal API.
- Read [Separate Before Serializing Shared State](references/principles/separate-before-serializing-shared-state.md) when concurrent actors may write the same branch, file, or state.

### Verify real behavior

- Read [Prove It Works](references/principles/prove-it-works.md) before claiming completion.
- Read [Fix Root Causes](references/principles/fix-root-causes.md) for a defect.
- Read [Sequence work into verifiable units](references/principles/sequence-verifiable-units.md) for multi-step work.
- Read [Test Behavior, Not Implementation](references/principles/test-behavior-not-implementation.md) when adding or changing tests.
- Read [Encode Lessons in Structure](references/principles/encode-lessons-in-structure.md) when the same correction appears twice.
- Read [Never Block on the Human](references/principles/never-block-on-the-human.md) before asking about a reversible or discoverable choice.
- Read [Guard the Context Window](references/principles/guard-the-context-window.md) before loading a large artifact or broad fan-out into the parent task.
- Read `../no-comments/SKILL.md` when the user requests a dedicated comment review. Ordinary code review or explanation does not activate its delegated cleanup workflow.
- Read `../unslop/SKILL.md` for every prose artifact and reply.
- Read `../technical-writing/SKILL.md` for documentation, plans, PR text, and commit text.

### Use native subagents deliberately

Follow [the runtime contract](references/codex-runtime.md). Use native subagents for independent work that improves speed, evidence, or review separation. Give each native subagent a bounded task, file ownership, acceptance criteria, and the instructions from `references/agents/cstack-agent.md`. The parent owns integration and verification.

For coverage across independent areas, read and apply `../swarm/SKILL.md`. For competing implementations or designs, read and apply `../arena/SKILL.md`. Parallelize only independent work. One actor writes a branch or shared file at a time.

Bound panels to native capacity. A panel with no `.cstack/models.json` entry defaults to three independent inherited-model attempts. A cross-judge pool defaults to one inherited-model judge. Run excess attempts in waves. If a playbook asks for more lanes than the work justifies, preserve each distinct scenario and mark redundant lanes `n/a` with a reason.

Follow the runtime contract's direct inheritance path when unconfigured; otherwise resolve the delegate's role with its trusted helper and preserve both `model` and `reasoning_effort` through the final native dispatch. Missing settings inherit. Report unsupported selections or dispatch capabilities without silently substituting or dropping effort.

Use `simple edits` for small bounded implementation changes and `documentation` for documentation-only delegates. Generic review or judgment uses `judgment and prose`. Use `hardest tasks` only for explicitly complex architecture, not difficult bugs or algorithms. Other implementation uses `feature, refactoring`; debugging uses `bug-fix`, `perf-issue` or `hillclimb` as appropriate. Specialized investigators, synthesizers and panels use their named setup roles. Pass the selected role into Swarm so its generic `swarm workers` default cannot replace it.

For nontrivial deliverable code, get a distinct independent review before PR creation or merge when native capacity permits. Reuse a review for the same scope and unchanged patch instead of starting another at every playbook boundary. If no independent reviewer is available, say so and use a bounded self review without calling it independent.

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

Keep comments only for a non-obvious reason that the code cannot express. Preserve licenses, public contracts, accessibility rationale, and verified tool constraints. Read `references/agents/comment-reviewer.md` only for a dedicated comment review.

### Write the report

Lead with the user-visible result. State what changed, the evidence, and any real limit. Link only artifacts read or produced in the current task. Use a full GitHub PR URL when a PR exists.

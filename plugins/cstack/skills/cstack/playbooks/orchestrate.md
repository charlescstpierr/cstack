### Orchestrate

Follow [the Codex runtime contract](../references/codex-runtime.md).

**You own the program and its decisions. Owners write code.** Use this playbook for a program that spans many units or PRs and outlives one agent's useful context. Use `autonomous-run.md` for one task with a checkable predicate.

Keep the ceremony proportional to the work. Near-identical cheap units need short briefs and inline checks. Novel or risky units need separate verification.

Three rules carry the program:

- Treat completions as queue events.
- Give every owner and follow-up the current standing orders.
- Make every brief executable by a new agent with no hidden chat context.

#### Roles

- **Coordinator.** Frames the program, writes briefs, drains results, owns topology, records decisions, and reports to the user. It never authors or edits code. It may perform mechanical git integration when authorized, such as a fast-forward or a clean cherry-pick of a worker's commit, then push. Conflicted merges, restacks, and code changes are always owner tasks.
- **Track coordinator.** Add one only when the root cannot drain a track directly. It owns a bounded unit list, writes briefs, assigns owners and verifiers, and returns a reduced rollup. Keep nesting shallow.
- **Owner or verifier.** Give each agent a bounded task, exclusive files or worktree, acceptance criteria, exact checks, and the instructions from `../references/agents/cstack-agent.md`. The verifier is always a different actor from the worker. When the session cannot provide a different model, the report states `single-model verification` instead of claiming independence. A verifier does not write the code it judges.

Bound the rolling window to native subagent capacity and run extra work in waves. A missing slot serializes that unit as a separate re-scoped pass in this session, labeled `single-agent`, and the report names the missing independence. Models inherit by default. Apply only an available override for each unit's matched work from `.cstack/models.json`. If an explicit model is unavailable, stop that selection and report it.

#### State layout

Create `.cstack/orchestrate/<project-slug>/` in the target workspace. Every file has one writer. Owners publish facts and readers aggregate them. Resolve the plugin root, then run the helper as `bash <plugin-root>/scripts/run-tool.sh orch/orch.ts <command>`. The launcher stages locked sources under `.cstack/tools/`.

- `preferences.md` contains numbered standing orders, one constraint per line.
- `overview.md` records durable PR and issue facts. Append instead of rewriting history.
- `units.tsv` records unit, track, state, branch, PR, head SHA, and brief path.
- `frontier.json` records the computed merge frontier.
- `ledger.tsv` records verdicts by PR and head SHA.
- `inbox/` holds completion pointers.
- `gates.md` records user gates with options and the blocked operation.
- `decisions.tsv` records the decision trail.
- `status.md` is generated from the tables at each drain.

Do not write program state into the installed plugin directory.

#### Brief format

Every owner brief contains these fields. Collapse the form for a tiny unit, but keep the facts.

```text
GOAL         one outcome that a new agent can execute
SCOPE        writable paths, forbidden paths, and the exclusive worktree or branch
CONTEXT      repository paths, PRs, and upstream facts needed by this unit
ACCEPTANCE   checkable criteria, one per line
VERIFY       exact commands or native interface checks, with known hazards
TIMEBOX      a rough cap; return partial evidence when it expires
FORBIDDEN    no topology edits, no force-push, no unrelated fixes, plus unit bans
REPORT       status, branch, head SHA, PR, verdict, checks run, deviations, follow-ups
STANDING     current preferences.md instructions
```

Pass context by repository path or by quoting only the necessary upstream result. Native subagents do not automatically see sibling results. A missing field means the unit is not ready to assign. Follow-up prompts restate the complete current brief.

#### Steps

1. **Frame.** State a countable done predicate, unit count, rough effort, expected PR shape, and time budget. If one agent can finish within the session, switch to `autonomous-run.md`. Name independent tracks. Use `../../arena/SKILL.md` before a disputed decomposition. When no subagent slot is available, run the comparison in this session as a separate re-scoped pass, label it `single-agent`, and report the missing independence. Confirm whether the user's request authorizes PR creation, external messages, or merges. Continue local reversible preparation without those actions.
2. **Initialize state.** Run `orch init` through the plugin launcher. Write standing orders before assigning work. Seed `frontier.json` from current git and GitHub PR facts with `orch frontier set --repo <repo-dir>`.
3. **Pilot one unit.** Take one representative unit through brief, implementation, verification, stack entry, ledger row, and authorized delivery. Use the pilot to test the brief, unit size, and check recipe. For cheap repeated units, the first ordinary unit is the pilot.
4. **Scale with a rolling window.** Refill native subagent slots as owners finish. Start dependent work only after its required context exists. Audit one sampled brief per track without blocking the current wave.
5. **Drain results.** Use the queue procedure below at each safe boundary.
6. **Integrate continuously.** Integrate verified units from the start. Keep one topology writer per stack. Advance `frontier.json` only after a confirmed merge or a reported new head. Create PRs and merge only when the user authorized those operations. After a unit's confirmed merge and verification, reconcile its worktree users; apply the **After a completed delivery** mode in [worktree cleanup](worktree-cleanup.md) once its owners, verifiers and dependents have released the recorded task-created path.
7. **Close.** Reconcile every assigned unit to a terminal row. Verify the predicate on the real artifact. Confirm that every delivered PR has a verdict for its current head. Audit the decision trail and preserve `.cstack/orchestrate/<project-slug>/` in a surviving workspace. Finish any eligible post-merge cleanup and report retained worktrees with their reasons.

#### Queue and drain

- On completion, run `orch inbox push <agent> <unit> <status> [--report PATH]`. Finish the current critical section before deep review.
- Drain after a critical section, a track rollup, a frontier watcher wake, and before a user report. Start with `orch inbox drain`. Arrivals during a drain wait for the next drain.
- Critical sections include writing a brief, changing stack topology, resolving a conflict, writing a gate, and updating the ledger or frontier.
- Classify each pointer as landed, needs verification, failed, stale, or noise. Write the result with `orch unit add`, `orch unit set`, and `orch ledger record`. Then run `orch status` and assign the next ready wave.
- Account for every child as completed, replaced, abandoned, or absorbed with a reason. Do not hide missing results by silently redoing them.

#### GitHub stack safety

- Compute the stack from GitHub PR head and base relationships, starting from the current branch. Reject ambiguous parents, cycles, missing PRs, and duplicate children. Record ordered PRs, branches, head SHAs, a generation, and the lowest unmerged PR in `frontier.json`.
- Use git and `gh` only.
- Keep exactly one topology writer per stack. Owners do not rebase, retarget PRs, or force-push unless their brief grants that exact operation.
- Run `babysit.md` against one frozen frontier generation. Conflicts return to the topology owner.
- Treat closing, retargeting, and merging as explicit units. They require the user's concrete authority because each changes external state.

#### Verification ledger

Scale verification to risk. The owner may run its own gates as evidence. The unit's verdict still comes from a non-author. When no subagent slot is available, run the verdict in this session as a separate re-scoped pass over a clean re-read, label it `single-agent review`, and report the missing independence. When the session cannot provide a different model, label the result `single-model verification`.

Record verdicts with `orch ledger record` and check them with `orch ledger check`. Key each row by PR and exact head SHA. Allowed verdicts include `live-ui-verified`, `unit-test-verified`, `type-check-only`, `verifier-blocked`, and `verifier-failed`. CI green contributes evidence but does not replace a behavior verdict. A new head invalidates the old row unless an unchanged stable patch ID preserves the code verdict and current CI and mergeability pass.

Externalize each completed unit at once. An owner records the branch and head, a verifier records the ledger row, and receipts live under `.cstack/`. Work that exists only in an agent's context is unfinished.

#### Liveness and recovery

- Inspect native agent state with the available coordination tools. Do not restart an idle agent merely to ask for status.
- Reconcile liveness from `units.tsv`, the ledger, git refs, GitHub PR state, and native task status. Conversation timestamps alone are not proof.
- Retry resource exhaustion with a smaller scope. Retry a network failure once. For a tool failure, use another available native method. After two failed retries, abandon the unit and replan.
- Reconcile a late result against the current frontier and ledger before accepting it.
- If a bad brief or broken dependency would corrupt a whole wave, stop refilling slots, let safe in-flight work finish, fix the cause, and update standing orders.
- Before pausing or exiting, write the current predicate, completed work, durable paths, blockers, and exact resume command under `.cstack/`. Do not claim that local subagents survive application exit.

#### Escalation

Batch user gates in `gates.md`. Ask only when a destructive or irreversible operation, missing credentials or authority, or a real product choice blocks progress. Do not send external messages, create PRs, merge, publish, or deploy only because this playbook is active.

Fix mid-run discoveries only when they block the frontier or fall inside the granted scope. Record other findings as proposed follow-ups.

**Reply:** Report the predicate and count from `units.tsv` and `ledger.tsv`, track results, frontier PRs and SHAs, verdicts, abandoned units, user gates, and the `.cstack/` state paths. Include full GitHub PR links when they exist. Every claim carries its evidence or its label in the same sentence. Measured, inferred, or guess. A prediction or an unseen cause is a guess. Never hand the human a check you could run.

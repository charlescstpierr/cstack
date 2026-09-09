### Orchestrate

Follow [the Codex runtime contract](../references/codex-runtime.md).

**You own the program and its decisions. Owners write code.** Use this playbook for a program that spans many units or PRs and outlives one agent's useful context. Use `autonomous-run.md` for one task with a checkable predicate.

Keep the ceremony proportional to the work. Near-identical cheap units need short briefs and inline checks. Novel or risky units need separate verification.

Three rules carry the program:

- Treat completions as queue events.
- Give every owner and follow-up the current standing orders.
- Make every brief executable by a new agent with no hidden chat context.

#### Roles

- **Coordinator.** Frames the program, writes briefs, drains results, owns topology, records decisions, and reports to the user. It may perform mechanical git integration when authorized. It does not absorb code-writing units that need a separate owner.
- **Track coordinator.** Add one only when the root cannot drain a track directly. It owns a bounded unit list, writes briefs, assigns owners and verifiers, and returns a reduced rollup. Keep nesting shallow.
- **Owner or verifier.** Give each agent a bounded task, exclusive files or worktree, acceptance criteria, exact checks, and the instructions from `../references/agents/cstack-agent.md`. A verifier does not write the code it judges.

Use native subagents only when the session exposes capacity. Bound the rolling window to that capacity and run extra work in waves. Models inherit by default. Apply only an available override for each unit's matched work from `.cstack/models.json`. If an explicit model is unavailable, stop that selection and report it.

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

1. **Frame.** State a countable done predicate, unit count, rough effort, expected PR shape, and time budget. If one agent can finish within the session, switch to `autonomous-run.md`. Name independent tracks. Use `../../arena/SKILL.md` before a disputed decomposition when native comparison is available. Confirm whether the user's request authorizes PR creation, external messages, or merges. Continue local reversible preparation without those actions.
2. **Initialize state.** Run `orch init` through the plugin launcher. Write standing orders before assigning work. Seed `frontier.json` from current git and GitHub PR facts with `orch frontier set --repo <repo-dir>`.
3. **Pilot one unit.** Take one representative unit through brief, implementation, verification, stack entry, ledger row, and authorized delivery. Use the pilot to test the brief, unit size, and check recipe. For cheap repeated units, the first ordinary unit is the pilot.
4. **Scale with a rolling window.** Refill native subagent slots as owners finish. Start dependent work only after its required context exists. Audit one sampled brief per track without blocking the current wave.
5. **Drain results.** Use the queue procedure below at each safe boundary.
6. **Integrate continuously.** Integrate verified units from the start. Keep one topology writer per stack. Advance `frontier.json` only after a confirmed merge or a reported new head. Create PRs and merge only when the user authorized those operations.
7. **Close.** Reconcile every assigned unit to a terminal row. Verify the predicate on the real artifact. Confirm that every delivered PR has a verdict for its current head. Audit the decision trail and leave `.cstack/orchestrate/<project-slug>/` intact.

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

Scale verification to risk. The owner may run one cheap deterministic command. Use a separate verifier for expensive, judgment-heavy, security-sensitive, or high-impact work.

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

**Reply:** Report the predicate and count from `units.tsv` and `ledger.tsv`, track results, frontier PRs and SHAs, verdicts, abandoned units, user gates, and the `.cstack/` state paths. Include full GitHub PR links when they exist.

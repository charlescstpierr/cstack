### Multi-phase or multi-PR plan

Follow [the Codex runtime contract](../references/codex-runtime.md).

**You own the plan. The plan is a checklist that an owner executes and the operator audits from evidence.** Do not implement while Codex is in Plan mode or when the user asked only for a plan.

1. If the change is one or two files with an obvious approach, explain why a formal plan adds no value and return the short execution outline.
2. Settle observable questions with `prototype.md` before writing the plan. Ask only about a product preference or materially branching choice that no run can settle. Record prototype paths and evidence in Appendix A.
3. Explore independent repository areas with bounded native subagents when capacity permits and each slice can add evidence, settle a decision, or provide independent verification. Give each a read-only scope and ask for file pointers, conventions, checks, and entry points. Run excess work in waves. Models inherit unless `.cstack/models.json` supplies an available `how explorer` override.
4. Copy the skeleton below into `.cstack/plans/<slug>.md` unless the user names a path. Fill every placeholder. Keep the headings and blocks in order. Give each PR one change and its own evidence. Choose `autopilot-full.md`, `autopilot-stack.md`, or `orchestrate.md` as the execution playbook.
5. Read and apply `../../technical-writing/SKILL.md` and `../../unslop/SKILL.md`. Keep the body as a how-to. Use appendices for explanation and reference.
6. Resolve the plugin root and run `bash <plugin-root>/scripts/run-tool.sh check-plan.mjs <plan.md>`. Fix every reported error.
7. Return the plan path and validator output. Do not start execution unless the current request already authorized it. A later execution request follows the named playbook.

**Verification rule.** Tests alone do not verify a PR. Each PR must define unit, live, and performance evidence. The live block is mandatory. The template retains ten distinct live scenarios, including a regression scenario against trunk. Execute them within native concurrency, in waves when needed. Models inherit by default. If fewer than ten meaningful scenarios exist, keep each unused lane with `n/a: <reason>` instead of inventing duplicate work.

Run the same load-bearing scenario on trunk and head. If trunk lacks the feature, record that fact and verify the added behavior plus the user-visible end state. The performance block compares like with like. If trunk lacks the scenario, set an absolute budget for the added work and the end state instead of claiming a false ratio.

An interaction change has a review gate. Capture screenshots and a short video when native tools support them, then show them in this task before merge. A PR with no interaction change states `**Review gate.** None. <PR id> is not review-gated.`

**Native interface checks.** Use an available Codex browser, simulator, terminal, or repository harness. Name the exact tool or command in each lane. If no tool can drive the interface, record the missing evidence in Appendix C and fail the live gate closed.

````markdown
# <Program> plan

<Under ten lines. State what changes, for whom, the rule the program enforces, and the PR ids in order.>

## How to read this

One box is one unit of work. Every box names its evidence. Check a box only when that evidence exists as a file, log, screenshot, test run, or SHA.

The program runs `<plugin-root>/skills/cstack/playbooks/<execution-playbook>.md`. <State who may create PRs and merge, plus operator-reserved items.>

Tests alone do not verify a PR. Each PR requires unit, live, and performance evidence.

## Program checklist

### Start the program

- [ ] Confirm the goal, PR order, verification rule, authority boundaries, and done condition from the user's request.
- [ ] Store the active objective and plan path under `.cstack/`.
- [ ] Read these files from the current checked-out source at program start and after relevant changes.
  - [ ] `<plugin-root>/skills/cstack/playbooks/<execution-playbook>.md`
  - [ ] `<plugin-root>/skills/swarm/SKILL.md`
  - [ ] `<plugin-root>/skills/cstack/references/codex-runtime.md`
  - [ ] `<plugin-root>/skills/cstack/playbooks/opening-a-pr.md`
  - [ ] <Each other bundled skill this program applies.>
- [ ] Continue in the foreground. If the user requested scheduled audits and a native scheduler exists, record the schedule. Otherwise checkpoint before exit.
- [ ] At each audit, re-read the objective and execution playbook. Inspect every active owner through native coordination, git, and `gh`. Judge progress by commits, pushes, PR deltas, checks, and receipts.
- [ ] On the operator's hold, interrupt every owner with a zero-writes instruction.

### Assign owners

- [ ] Assign one owner per independent PR within native concurrency. Queue the rest.
- [ ] Follow this dependency graph. Start dependent work only after its parent context exists.
  - [ ] <PR id> and <PR id> are independent and first. Both branch from trunk.
  - [ ] <PR id> starts after <PR id> merges, or targets its branch in stack mode.
- [ ] Hold file boundaries. <PR id or class> may write only `<glob>`.
- [ ] Hold review gates. <PR ids> wait at merge-ready for the operator's visual review.

### Handle each PR

- [ ] Use git and `gh` only.
- [ ] Create a ready PR with `gh pr create --base <base-branch>` only when authorized. A stack child targets its parent branch.
- [ ] Run the repository's targeted checks, lint, and typecheck before the PR-facing push.
- [ ] Inspect comments as part of the general diff review. Read and apply `<plugin-root>/skills/no-comments/SKILL.md` only for a dedicated comment-review request. Read and apply `<plugin-root>/skills/technical-writing/SKILL.md` and `<plugin-root>/skills/unslop/SKILL.md` before PR text.
- [ ] Triage automated review through `../references/bugbot-triage.md`.
- [ ] Rebase onto current trunk before babysitting and again before the merge-ready report when the execution playbook requires it.

### Verify and deliver each PR

- [ ] At the merge-ready head SHA, run gates, the ten live lanes below within native capacity, the performance lane, and a diff-and-receipts audit.
- [ ] For nontrivial deliverable code, obtain a distinct independent review when native capacity permits. If unavailable, record the bounded self-review fallback without calling it independent.
- [ ] Mark clean only when every applicable lane passes. A changed head gets a fresh verdict unless an unchanged patch ID preserves the code verdict and current CI and mergeability pass.
- [ ] Follow the merge or append rule from the execution playbook. Do not merge without concrete authorization.

### Boot each live lane

- [ ] Give the lane a separate checkout or worktree at `<head SHA>` when concurrent writers or runtimes could conflict.
- [ ] Start the backend and target interface. Wait for its readiness signal.
- [ ] Deliver input with the named native browser, simulator, terminal, or harness command.
- [ ] Save artifacts under `.cstack/evidence/<pr-id>/lane-<n>/` and return their paths.

## <Task as a verb phrase> (<PR id>)

**Depends on.** <PR id, or None.>

**Files.**

- [ ] Edit `<path>`.
- [ ] Create `<path>`.
- [ ] Delete `<path>`.

**Build.**

- [ ] <One change. Name the symbol and file.>

**You see.**

- [ ] <One observable result with the exact log line or interface state.>

**Verify, unit.** Tests alone do not verify a PR. Each PR requires unit, live, and performance evidence.

- [ ] <Test file and case.> Run `<command>`.

**Verify, live.** Tests alone do not verify a PR. Each PR requires unit, live, and performance evidence. Run these scenarios within native capacity.

- [ ] Lane 1. Regression against trunk. Run <the same load-bearing scenario> on trunk and head. Save `<slug>`. Pass when <predicate>.
- [ ] Lane 2. <Scenario, artifact, and predicate.>
- [ ] Lane 3. <Scenario, artifact, and predicate.>
- [ ] Lane 4. <Scenario, artifact, and predicate.>
- [ ] Lane 5. <Scenario, artifact, and predicate.>
- [ ] Lane 6. <Scenario, artifact, and predicate.>
- [ ] Lane 7. <Scenario, artifact, and predicate.>
- [ ] Lane 8. <Scenario, artifact, and predicate.>
- [ ] Lane 9. <Scenario, artifact, and predicate.>
- [ ] Lane 10. <Scenario, artifact, and predicate.>

**Verify, performance.** Tests alone do not verify a PR. Each PR requires unit, live, and performance evidence.

- [ ] Metric. <The value measured on trunk and head.>
- [ ] Probe. <The interleaved command or procedure.>
- [ ] Baseline. Record the trunk value first.
- [ ] Rule. <The numeric failure threshold, or absolute budgets when scenarios differ.>

**Review gate.** The operator reviews before merge.

- [ ] Save review screenshots under `.cstack/evidence/<pr-id>/review/`.
- [ ] Record a 30 to 60 second video when the native tool supports it.
- [ ] Show the artifacts in this task and stop at merge-ready for the operator's decision.

**Deliver.**

- [ ] Independent clean verdict at the exact head SHA.
- [ ] Automated-review triage complete.
- [ ] Current base and patch ID recorded.
- [ ] <The authorized owner merges, or the topology owner appends the PR and the operator lands the stack.>

## Close the program

- [ ] Every applicable box has evidence.
- [ ] Return the report required by the execution playbook.

## Appendix A. Prototype evidence

<Each question answered by a prototype, with branch, SHA, and artifact paths. List unproven questions.>

## Appendix B. Alternatives rejected

<Each serious alternative and why it lost.>

## Appendix C. Risks and missing capabilities

<Each risk, its owning PR, and any unavailable native tool or model that limits proof.>

## Appendix D. Links and reading list

<Files and official docs owners must read. Name which PRs apply how, architect, interrogate, swarm, and show-me-your-work.>
````

**Reply:** Return the plan path, PR dependency order, review-gated set, prototype findings and gaps, and the exact validator result.

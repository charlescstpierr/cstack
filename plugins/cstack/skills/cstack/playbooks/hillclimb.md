### Hillclimb

Follow [the Codex runtime contract](../references/codex-runtime.md).

**You own the metric and the experiment's integrity. Supervise and review. Delegate the attempts.** For sustained, iterative improvement of one measurable thing against a target. A one-off fix is Bug fix or Perf issue. This is the loop.

Core discipline: one change, one measurement, keep or revert. Never stack untested changes, and never claim a win from code inspection (the [Prove It Works](../references/principles/prove-it-works.md) principle reference).

1. Ground the workload and architecture before choosing the metric. Read and apply `../../how/SKILL.md`. Name the workload dimensions that can move the result, such as data size, history, state, or concurrency. Select a case that reproduces the complaint. If no case reproduces it, fix the reproduction first. Set one metric, the better direction, and a checkable stop predicate. Use the user's numbers when given. Otherwise choose a conservative target and state it.
2. Build the measurement harness, prove its sensitivity, then freeze it (the [Build the Lever](../references/principles/build-the-lever.md) principle reference). Run contrasting realistic workloads and confirm the target case reproduces the symptom while easier cases separate as expected. If the harness cannot distinguish them, revise the workload or metric. Once frozen, one repeatable command emits the metric, sampled enough to clear the noise (median of N, not a single run). Record the baseline metric and a green run of the regression gate (the tests that must keep passing) before any change.
3. Open the decision log via the **show-me-your-work** skill. A `decision.tsv`, one row per attempt: id, hypothesis, change, before, after, delta, tests, verdict (kept or reverted), note. Read it before each attempt. Keep it out of the tree (gitignored).
4. Ground each hypothesis in the architecture model from step 1, so it names a specific mechanism ("defer X off the boot path because it blocks first paint"), not "try memoizing something".
5. Loop, one hypothesis per iteration:
   - Hand the change to a bounded native subagent when capacity permits. Models inherit unless `.cstack/models.json` supplies an available `hillclimb` override. When several independent hypotheses are live, give each its own worktree. Otherwise test them sequentially.
   - Measure before and after with the frozen harness, and run the regression gate.
   - Accept only when the metric moves past noise and the gate stays green. Otherwise revert the change in full. A tweak that "might help" is not kept.
   - One commit per accepted fix, staging only the files you changed (`git add <files>`, never `-A`). Log the row either way, kept or reverted.
   Each iteration ends in a check before the next begins (the [Sequence work into verifiable units](../references/principles/sequence-verifiable-units.md) principle reference). If the run is unattended, borrow only the wake mechanism from the Autonomous run playbook (`playbooks/autonomous-run.md`), not its stop rule.
6. Push past the first plateau. On a stall, several rejects in a row, pivot category, combine near-misses, re-read the source, or try something more radical before concluding the hill is climbed. Correctness and simplicity outrank the number. Revert a win that breaks behavior, and keep a simplification that holds the number (the [Laziness Protocol](../references/principles/laziness-protocol.md) principle reference).
7. Stop when the predicate is met, or when the remaining ideas are marginal and not worth their cost. Don't relax the predicate to meet it, and don't quit while cheap untried hypotheses remain. If you are stuck, surface it instead of spinning.
8. Run **Opening a PR** with the accepted commits in order only when the user authorized PR creation.

**Reply:** the metric and target, baseline to final with the percent delta, iterations run (kept vs reverted), each accepted fix on one line, the `decision.tsv` path, and the best idea you would try next if pushed further.

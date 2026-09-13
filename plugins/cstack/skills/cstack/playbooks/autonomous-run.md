### Autonomous run

Follow [the Codex runtime contract](../references/codex-runtime.md).

**You own the exit condition. Define done, then drive to it without stopping.**

1. State the exit condition as a checkable predicate before the first iteration (tests green, repro fixed, all N PRs merged, pixel-diff zero).
2. Continue in the foreground with native waits. For CI, a merge, or a ref change, use the event-aware tool or the bundled watcher through the plugin launcher. Use a native scheduler only when it is available and the user requested scheduled continuation. Size polling to when a result is worth checking. Do not promise that work survives an app exit.
3. Each iteration makes the smallest change the evidence justifies, verifies it against the predicate, commits if it advanced, discards changes that didn't help. Belt-and-suspenders that "might help" gets reverted, not left to ride. Discard only the files that iteration touched, with `git checkout -- <paths>` or `git stash push <paths>`. Never `reset --hard`, never `git clean`, never `checkout -- .`. Run `../../deslop/SKILL.md` over the diff before each commit. Keep `deslop skipped: <reason>` when a step genuinely cannot run it.
   Sequence the work via the [Sequence work into verifiable units](../references/principles/sequence-verifiable-units.md) principle reference, verifying each unit before the next instead of batching checks at the end.
4. Address in-scope broken skills, related bugs, flaky verifiers, review noise, tooling failures, orphaned follow-ups, and fixable drift. Put unrelated fixes in a separate proposed change and do not create its PR without authorization. Ask only for destructive or irreversible work, missing authority, a genuine product choice, or a real dead end. Return to the predicate after each side fix.
5. Checkpoint every iteration via the **show-me-your-work** skill, a row for what changed and whether the predicate moved.
6. Stop when the predicate is met. A plateau is not a stop, so keep going and pivot your approach to push past it. Surface a genuine dead end rather than spinning, and never relax the predicate to declare victory.

**Reply:** the exit condition, iterations run, what landed, what was discarded, final predicate state. Every claim carries its evidence or its label in the same sentence. Measured, inferred, or guess. A prediction or an unseen cause is a guess. Never hand the human a check you could run.

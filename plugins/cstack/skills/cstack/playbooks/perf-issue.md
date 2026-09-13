### Perf issue

Follow [the Codex runtime contract](../references/codex-runtime.md).

**You own the measurement story. Plan, review, verify the numbers.** Tie every fix to a measurement, don't read source instead of measuring.

1. Capture a baseline trace with the native browser, simulator, profiler, or terminal tool available for the target.
2. `how` to ground hypotheses. Don't claim a perf ceiling without running it first.
   Most fixes come from eight strategy families. Use them as hypothesis generators, not a checklist. A family earns an attempt only when the trace shows the signal it names.
   - **Elimination.** Before optimizing the hot path, ask whether it needs to exist: a computation nobody consumes, a feature gate that's always off for this user, a sync that redundantly mirrors state, a legacy path kept "just in case". The trace shows what's slow, never that it's deletable, so this family needs the `how` pass, not the profiler.
   - **Divide and conquer.** The dominant cost scales with input size. Split the work so each piece touches less (chunk, shard, prune the search space) or so independent pieces run in parallel.
   - **Caching.** The same computation or fetch repeats on identical inputs. Store and reuse the result. Name what invalidates it before claiming the win.
   - **Indirection.** The hot path does expensive work a cheaper intermediate could absorb: an index instead of a scan, a queue that shifts work off the interactive thread, a handle that lets a cheaper implementation swap in. Add the hop only when it removes more from the critical path than it adds.
   - **Batching.** Many small operations each pay a fixed overhead (RPC, query, syscall, draw call). Coalesce them to pay the overhead once per batch.
   - **Redundancy.** The wait hangs on one slow instance or attempt. Duplicate the work (replicas, hedged requests, speculative execution) and take the fastest result. The trace has to show the wait dominates and the system has headroom.
   - **Lazy evaluation.** Cost lands on results that are never used or not needed yet (eager init on the boot path, rendering offscreen items). Defer the work until first use.
   - **Scheduling.** The work must happen, but not during the interactive moment. Move it to where nobody is waiting: idle callbacks, a background warmup after boot, precompute before the user arrives, cleanup after the frame commits. The win is perceived latency, so measure the interactive path, not total work done.
3. Plan the fix from the trace. If it crosses a function boundary, read and apply `../../architect/SKILL.md` first. Delegate a bounded implementation. Preserve the caller-selected role, including `simple edits` for small bounded changes. Use `feature, refactoring` when no role was selected. Follow the runtime contract for inheritance or configured model and effort. Review the diff. When no subagent slot is available, write the fix in this session as a separate re-scoped pass, then run a separate review pass over a clean re-read of the diff, label it `single-agent review`, and report the missing independence. Capture a post-fix trace. Run `../../deslop/SKILL.md` over the diff before each commit. Keep `deslop skipped: <reason>` when a step genuinely cannot run it.
   Apply the [Sequence work into verifiable units](../references/principles/sequence-verifiable-units.md) principle reference, verifying each attempt before trying the next.
4. Parse and compare the artifacts (JSON to sqlite, diff). "Inconclusive" or wrong-surface is not a pass. Flag it.
5. Cite the measurement in the PR.
6. Run **Opening a PR** only when the user authorized PR creation.

For sustained improvement against a metric rather than a one-off fix, use the Hillclimb playbook (`hillclimb.md`).

**Reply:** baseline number, post-fix number, delta, artifact path. Every claim carries its evidence or its label in the same sentence. Measured, inferred, or guess. A prediction or an unseen cause is a guess. Never hand the human a check you could run.

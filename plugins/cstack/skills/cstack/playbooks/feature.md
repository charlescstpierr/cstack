### Feature

Follow [the Codex runtime contract](../references/codex-runtime.md).

**You own the design. Plan, review, verify.** Delegate implementation. Stay in the lead.

1. Read and apply `../../how/SKILL.md` over the affected subsystem.
2. Read and apply `../../architect/SKILL.md` for design exploration. Bound how many design runners run at once to native capacity and queue the rest. Keep `architect skipped: <reason>` when the step does not earn its cost.
3. Write the throughput checkpoint as four todo items. A dimension that genuinely does not apply (single file, no fan-out) keeps its item with `n/a: <reason>` rather than being dropped:
   - **Blocking first steps.** Gates run before fan-out.
   - **Independent workstreams.** Disjoint files, services, or layers parallelize. Shared writes serialize.
   - **Shared mutable state.** Default to splitting the target (the [Separate Before Serializing Shared State](../references/principles/separate-before-serializing-shared-state.md) principle reference). Serialize only for real invariants.
   - **Smallest safe decomposition.** If one worker is best, name why.
4. Delegate the code-writing. Review the diff yourself. Give the delegate file ownership, the named data shape, its organizing structure, and success criteria. Preserve the caller-selected role, including `simple edits` for small bounded changes. Use `feature, refactoring` only when no role was selected. Follow the runtime contract for inheritance or configured model and effort. When no subagent slot is available, write the code in this session as a separate re-scoped pass, then run a separate review pass over a clean re-read of the diff, label it `single-agent review`, and report the missing independence. When the implementation admits multiple valid shapes (error handling, abstraction layer, test structure), read and apply `../../arena/SKILL.md`. Mandatory: no skip-with-reason escape, and Laziness Protocol does not override it. Keep edits surgical. Re-ground upstream-derived files against their source. Apply shared improvements to every consumer and verify each. Run `../../deslop/SKILL.md` over the diff before each commit. Keep `deslop skipped: <reason>` when a step genuinely cannot run it.
5. Verify on the matching surface. "Inconclusive" or wrong-surface is not a pass. Flag it.
6. Rebase into small, ordered commits. Stack follow-ups.
   Use the [Sequence work into verifiable units](../references/principles/sequence-verifiable-units.md) principle reference, building, verifying, and committing each small unit before the next.
7. If the design is contested, `interrogate` before shipping.
8. Run **Opening a PR** only when the user authorized PR creation.

Code-coupled work goes to one owner with the checkpoint inline. Fan out only independent artifacts, such as audits, cross-subsystem investigations, or competing experiments. Rewrite the checkpoint at phase boundaries. Give follow-up work a complete brief instead of relying on lost context.

**Reply:** what you built, what you chose and why, the throughput checkpoint, open decisions. Tables for design alternatives. Every claim carries its evidence or its label in the same sentence. Measured, inferred, or guess. A prediction or an unseen cause is a guess. Never hand the human a check you could run.

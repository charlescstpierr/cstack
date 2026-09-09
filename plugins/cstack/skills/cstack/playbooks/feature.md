### Feature

Follow [the Codex runtime contract](../references/codex-runtime.md).

**You own the design. Plan, review, verify.** Delegate implementation. Stay in the lead.

1. Read and apply `../../how/SKILL.md` over the affected subsystem.
2. Read and apply `../../architect/SKILL.md` for design exploration. Use native parallel agents only when capacity permits. Keep `architect skipped: <reason>` when the step does not earn its cost.
3. Write the throughput checkpoint as four todo items. A dimension that genuinely does not apply (single file, no fan-out) keeps its item with `n/a: <reason>` rather than being dropped:
   - **Blocking first steps.** Gates run before fan-out.
   - **Independent workstreams.** Disjoint files, services, or layers parallelize. Shared writes serialize.
   - **Shared mutable state.** Default to splitting the target (the **separate-before-serializing-shared-state** principle skill). Serialize only for real invariants.
   - **Smallest safe decomposition.** If one worker is best, name why.
4. When native capacity makes review separation useful, delegate code to a bounded subagent with file ownership, the named data shape, its organizing structure, and success criteria. Models inherit unless `.cstack/models.json` supplies an available `feature, refactoring` override. Review the diff yourself. When several valid shapes deserve comparison, read and apply `../../arena/SKILL.md`. If no subagent slot exists, implement in the foreground and preserve the independent review step. Keep edits surgical. Re-ground upstream-derived files against their source. Apply shared improvements to every consumer and verify each.
5. Verify on the matching surface. "Inconclusive" or wrong-surface is not a pass. Flag it.
6. Rebase into small, ordered commits. Stack follow-ups.
   Use the **sequence-verifiable-units** principle skill, building, verifying, and committing each small unit before the next.
7. If the design is contested, `interrogate` before shipping.
8. Run **Opening a PR** only when the user authorized PR creation.

Code-coupled work goes to one owner with the checkpoint inline. Fan out only independent artifacts, such as audits, cross-subsystem investigations, or competing experiments. Rewrite the checkpoint at phase boundaries. Give follow-up work a complete brief instead of relying on lost context.

**Reply:** what you built, what you chose and why, the throughput checkpoint, open decisions. Tables for design alternatives.

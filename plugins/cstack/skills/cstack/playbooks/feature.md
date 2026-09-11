### Feature

Follow [the Codex runtime contract](../references/codex-runtime.md).

**You own the design. Plan, review, verify.** Keep clear routine work in the parent. Delegate only independent implementation, review, or investigation slices that add evidence, settle a decision, or provide review separation.

1. Understand the affected subsystem. For broad, unfamiliar, or cross-layer work, read and apply `../../how/SKILL.md`; otherwise inspect the relevant files directly.
2. Explore the design shape. Read and apply `../../architect/SKILL.md` when the feature introduces a meaningful boundary, ownership, or module-layout choice. Use native parallel agents only for independent useful design angles.
3. When coordinating multiple owners, record blocking steps, independent workstreams, shared mutable state, and file ownership in the plan. Split shared writes using [Separate Before Serializing Shared State](../references/principles/separate-before-serializing-shared-state.md). Single-owner work needs no throughput checkpoint.
4. When native capacity makes review separation useful, delegate code to a bounded subagent with file ownership, the named data shape, its organizing structure, and success criteria. Preserve the caller-selected role, including `simple edits` for small bounded changes; use `feature, refactoring` only when no role was selected. Follow the runtime contract for inheritance or configured model and effort. Review the diff yourself. When several valid shapes deserve comparison, read and apply `../../arena/SKILL.md`. If delegation does not help, implement in the foreground and review the diff yourself. Keep edits surgical. Re-ground upstream-derived files against their source. Apply shared improvements to every consumer and verify each.
5. For nontrivial deliverable code, get a distinct independent review before PR creation or merge when native capacity permits. If capacity or host support is missing, record the fallback and do a bounded self review without calling it independent.
6. Verify on the matching surface. "Inconclusive" or wrong-surface is not a pass. Flag it.
7. Rebase into small, ordered commits. Stack follow-ups.
   Use the [Sequence work into verifiable units](../references/principles/sequence-verifiable-units.md) principle reference, building, verifying, and committing each small unit before the next.
8. If the design is contested, `interrogate` before shipping.
9. Run **Opening a PR** only when the user authorized PR creation.

Code-coupled work goes to one owner. Fan out only independent artifacts, such as audits, cross-subsystem investigations, or competing experiments. Update ownership when the work changes. Give follow-up work a complete brief instead of relying on lost context.

**Reply:** what you built, what you chose and why when a design choice mattered, verification evidence, and open decisions. Tables only for real alternatives.

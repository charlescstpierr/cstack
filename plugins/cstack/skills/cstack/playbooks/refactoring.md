### Refactoring

Follow [the Codex runtime contract](../references/codex-runtime.md).

**You own the contract. The structure changes. The behavior does not.** Distinct from Feature, which adds behavior, and Bug fix, which corrects it.

If the cleanup reveals a missing feature or a real bug, split it out and ship the structural change first against the pinned contract. A redesign is allowed, but name it and route to Feature. Large or cross-cutting structural work belongs to the **figure-it-out** skill. This playbook is the focused-to-medium change.

1. Pin the behavior contract first. Run the **how** skill over the affected subsystem to learn the contract, then write a characterization test, snapshot, or equivalence harness that captures current behavior before any structure moves. If the area has no coverage, write the pin before touching structure. Type check and lint are not a pin.
2. Name the structure the code is missing per **principle-model-the-domain**. Boring code stays when the shape is already clear and local. The reshape must delete branches or invalid states, not add indirection.
3. Name the target shape. State what the module layout, types, and call graph should be if built today (**principle-foundational-thinking**, **principle-redesign-from-first-principles**). If the target crosses a function boundary, run the **architect** skill for parallel design exploration of the shape before the move.
4. Subtract before you add. Delete dead code, collapse one-caller wrappers, drop redundant validators, and remove orphan references before introducing the new shape (**principle-subtract-before-you-add**). The smallest change that reaches the target shape ships (**principle-laziness-protocol**). A speculative cleanup that "might help" gets reverted.
5. Move in small behavior-preserving steps, each keeping the pin green. For API reshapes, migrate every caller and delete the old API in the same wave (**principle-migrate-callers-then-delete-legacy-apis**). Do not keep parallel old and new paths. Spot-check every rename against the actual files. Delegate mechanical edits to a bounded native subagent when capacity permits. Models inherit unless `.cstack/models.json` supplies an available `feature, refactoring` override. Review the diff yourself.
6. Prove behavior is unchanged on the real artifact, not only that it compiles (**principle-prove-it-works**). For larger reshapes, run an equivalence script, replay a recorded baseline, or smoke-test the real interface with an available native tool. Own the verification. Do not treat a delegate's summary as proof.
7. Confirm the change is worth keeping. The success measure is reduced reader load (**principle-minimize-reader-load**). If the diff does not lower reader load somewhere, revert it.
8. Rebase into small ordered commits when commits are in scope. A subtraction commit comes before the reshape and any follow-up cleanup. Keep each slice green. Run **Opening a PR** only when the user authorized PR creation.

**Reply:** the structure that changed, the pin you held it against, the equivalence proof, the reader-load delta, what shipped and what got reverted. No new behavior.

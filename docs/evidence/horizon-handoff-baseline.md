# Horizon → Orchestrate: before-fix observation

Observed on 2026-10-17 at base `8f50de1`, before implementation, with Bun 1.4.0.
Source: GitHub issue #93 and the local Horizon templates, Orchestrate playbook,
`orch/store.ts` and `orch/orch.ts` at that commit.

In an isolated `.cstack/issue93/baseline` store, `init` followed by four
`units.add` calls for A/B/C/D returned all four as `pending`. The intended
Horizon graph was A and B independent, C blocked by A, D blocked by B and C.
`units.set({id: "C", state: "working"})` succeeded before A had any ledger
entry. Repeating `units.add({id: "A", track: "delivery"})` failed with
`l’unité A existe déjà`.

The unit schema had no dependency or ownership field. No CLI command imported
Horizon definitions. Existing exact PR/SHA ledger lookup and store locking were
available to reuse. This reproduces a missing conversion/dispatch contract;
it does not claim the natural-language coordinator invariably lost decisions.

Measured preparation: four manual add operations, no generated briefs, zero
machine-retained dependency edges (three required edges), and no source hashes.
Human rereads and lost human decisions were not measured. The regression fixture
will compare structural preparation work, without claiming model token savings.

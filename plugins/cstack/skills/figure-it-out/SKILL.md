---
name: figure-it-out
description: "Design an auditable playbook when no narrower one fits: a large migration, an ambitious multi-part change, or work a human reviews after stepping away. Scales rigor to the task, runs a hypothesis loop, and logs decisions via show-me-your-work. Use for $cstack:figure-it-out, 'figure it out', a large migration, or when no narrower playbook applies."
---

# Figure it out

Runtime: [`../cstack/references/codex-runtime.md`](../cstack/references/codex-runtime.md).

When the task matches no playbook, design one. The deliverable before any code is the workflow itself: a sequence of phases that scales rigor to the task, runs the scientific method, and leaves a decision trail a human can audit after stepping away. Bias toward more rigor. The cost of building the wrong thing dwarfs the cost of being careful.

## Start

Start the task list by reading the common rules and principle routes in the [cstack skill](../cstack/SKILL.md). Read the individual references whose triggers apply, then add the phases below to the task list. Reuse an existing Horizon handoff and verified decisions when they already establish the framing; retain the playbook's review and verification gates.

## Phase A: Frame

Ground first, then commit. Don't start the run until you can state:

- The definition of done as a falsifiable predicate (the [Prove It Works](../cstack/references/principles/prove-it-works.md) principle reference).
- Scope, quantified: rough units and effort, plus the blockers grounding surfaced.
- The rigor level, biased high. One-way doors and high blast radius get more. Reversible low-stakes steps get less. Rigor is gates and artifacts, not "try harder".

Present the framing and tradeoffs before committing to a long run. Reversible work proceeds (the [Never Block on the Human](../cstack/references/principles/never-block-on-the-human.md) principle reference), but a multi-hour run earns one checkpoint.

## Phase B: Design the workflow

Decompose into atomic, independently-landable units. Sequence riskiest-unknown-first. Scaffold and verification come before features (the [Foundational Thinking](../cstack/references/principles/foundational-thinking.md) principle reference).

- Build the verification harness before the work, with the baseline captured from the pre-change state, so the check reads as "old value vs new value".
- For one-way-door design decisions, run the **architect** skill (it runs **arena**). Skip it for mechanical work whose shape is already concrete. A second arena over a settled design is over-engineering (the [Laziness Protocol](../cstack/references/principles/laziness-protocol.md) principle reference).
- Decide what fans out. Parallelize only across seams, and give each worker its own worktree or branch (the [Separate Before Serializing Shared State](../cstack/references/principles/separate-before-serializing-shared-state.md) principle reference). Don't over-fan.
- Write the designed phase list down. That list is what the human reviews.

Then execute the design. Add its steps to the current task list after Phase C and before Phase D. Run each under the Phase C loop discipline, and weave the Phase D log through them as each step lands.

## Phase C: Run the loop

Each unit is an experiment. State the hypothesis, make the smallest change, measure against the predicate on the real artifact, keep it if it advanced, revert it if it didn't.
Apply the [Sequence work into verifiable units](../cstack/references/principles/sequence-verifiable-units.md) principle reference, verifying each unit before starting the next instead of batching checks at the end.

- Verify by inspecting the artifact, never a self-report. When something passes too easily, suspect the observation method before the system.
- Pair delegated work with a judge and audit the delegates' artifacts yourself before trusting them. If a worker games the gate, reset and harden the contract. If the gate itself is wrong, fix the gate in its own change rather than routing around it.
- A verdict is VERIFIED, NOT VERIFIED, or INCONCLUSIVE. Inconclusive is not a pass. Don't hide a negative.

## Phase D: Keep the audit trail

Log the run via the **show-me-your-work** skill, one canonical TSV with a row per decision and per unit, evidence as links. figure-it-out's work is usually ambitious enough to commit the trail so the reviewer can read it in the PR. Commit it when confidence has to be shown. Prefer evidence produced by committed scripts. The trail plus the diff is what lets the human come back and trust the work.

## Phase E: Verify and hand back

Check the whole against the Phase A predicate on the real product, not just the harness. Encode any recurring correction as a gate, a lint rule, a check, or a script (the [Encode Lessons in Structure](../cstack/references/principles/encode-lessons-in-structure.md) principle reference).

**Reply:** the playbook you designed, the rigor level and why, the decision-trail path, what's verified against the predicate, and what's still open.

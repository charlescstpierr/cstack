### Bug fix

Follow [the Codex runtime contract](../references/codex-runtime.md).

**You own this task. Plan, review, verify.** Keep the investigation in the parent unless independent slices will rule out hypotheses faster or give useful review separation.

Be scientific. Every shipped line traces to runtime evidence. Belt-and-suspenders that "might help" is a hypothesis, not a fix. It does not ship. When evidence refutes a hypothesis, revert what it motivated. The smallest change the evidence justifies ships, nothing more.

1. Reproduce it on the real interface with available native tools. For a browser or running app, use a browser or simulator tool when the session exposes one. For a CLI, run the command in a terminal. If no native tool reaches the target, drive the reproduction as far as possible and state the specific gap. Synthesize the trigger or add instrumentation before asking the user to reproduce it.
2. Binary-search the cause. Read and apply `../../how/SKILL.md` when the affected subsystem is broad or unfamiliar. Read and apply `../../why/SKILL.md` when regression history or intent matters. Rule out hypotheses with runtime evidence. Add instrumentation when state is unclear. Continue a stubborn hunt in the foreground. Confirm the surviving mechanism before design review.
3. Plan the fix. If it crosses a function boundary with a meaningful design choice, read and apply `../../architect/SKILL.md` first. Delegate a bounded implementation when native capacity makes review separation useful. Models inherit unless `.cstack/models.json` supplies an available `bug-fix` override. Review the diff.
4. For nontrivial deliverable code, get a distinct independent review before PR creation or merge when native capacity permits. If capacity or host support is missing, record the fallback and do a bounded self review without calling it independent.
5. Verify on the same surface. The original repro now passes. "Inconclusive" or wrong-surface is not a pass. Flag it. Unit tests show branch behavior, not bug absence.
6. Stage the commits so the failing repro lands before the fix in git history. See the **tdd** skill for the failing-test-first cadence when the bug has a cheap local test path. Skip it when the test would be expensive, integration-heavy, or unclear.
   This is the canonical [Sequence work into verifiable units](../references/principles/sequence-verifiable-units.md) principle reference, the failing test first and the fix on top.
7. Run **Opening a PR** only when the user authorized PR creation.

Fan out `how`, `why`, repro, or code-search slices only when they are independent and useful.

**Reply:** what was broken, root cause, fix, how you verified. Paste failing-then-passing repro output verbatim.

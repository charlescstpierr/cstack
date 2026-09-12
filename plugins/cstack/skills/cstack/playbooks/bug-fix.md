### Bug fix

Follow [the Codex runtime contract](../references/codex-runtime.md).

**You own this task. Plan, review, verify.** Delegate investigation and the fix to subagents, stay in the lead.

Be scientific. Every shipped line traces to runtime evidence. Belt-and-suspenders that "might help" is a hypothesis, not a fix. It does not ship. When evidence refutes a hypothesis, revert what it motivated. The smallest change the evidence justifies ships, nothing more.

1. Reproduce it on the real interface with available native tools. For a browser or running app, use a browser or simulator tool when the session exposes one. For a CLI, run the command in a terminal. If no native tool reaches the target, drive the reproduction as far as possible and state the specific gap. Synthesize the trigger or add instrumentation before asking the user to reproduce it.
2. Binary-search the cause. Read and apply `../../how/SKILL.md` over the affected subsystem and `../../why/SKILL.md` for regression history. Rule out hypotheses with runtime evidence. Add instrumentation when state is unclear. Continue a stubborn hunt in the foreground. Confirm the surviving mechanism before design review.
3. Plan the fix. If it crosses a function boundary, read and apply `../../architect/SKILL.md` first. Delegate a bounded implementation. Preserve the caller-selected role, including `simple edits` for small bounded changes. Use `feature, refactoring` when no role was selected. Follow the runtime contract for inheritance or configured model and effort. Review the diff. When no subagent slot is available, write the fix in this session as a separate re-scoped pass, then run a separate review pass over a clean re-read of the diff, label it `single-agent review`, and report the missing independence.
4. Verify on the same surface. The original repro now passes. "Inconclusive" or wrong-surface is not a pass. Flag it. Unit tests show branch behavior, not bug absence.
5. Stage the commits so the failing repro lands before the fix in git history. Read and apply `../../tdd/SKILL.md` for the failing-test-first cadence when the bug has a cheap local test path. Skip it when the test would be expensive, integration-heavy, or unclear.
   This is the canonical [Sequence work into verifiable units](../references/principles/sequence-verifiable-units.md) principle reference, the failing test first and the fix on top. Run `../../deslop/SKILL.md` over the diff before each commit. Keep `deslop skipped: <reason>` when a step genuinely cannot run it.
6. Run **Opening a PR** only when the user authorized PR creation.

Investigation fans out `how` + `why` as parallel subagents.

**Reply:** what was broken, root cause, fix, how you verified. Paste failing-then-passing repro output verbatim. Every claim carries its evidence or its label in the same sentence. Measured, inferred, or guess. A prediction or an unseen cause is a guess. Never hand the human a check you could run.

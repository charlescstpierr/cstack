### Eval

Follow [the Codex runtime contract](../references/codex-runtime.md).

**You own the experiment design. Plan, blind, run, synthesize.**

**Non-negotiables for blinding:**

- No `eval`, `test`, `judge`, `experiment`, `rubric`, `score`, `compare`, `benchmark`, `candidate`, or `arena` in any directory, file, or prompt the candidate sees.
- The candidate prompt looks like an organic user request. State the goal, not the meta.
- No chain-eliciting cues. Don't ask the candidate to list which skills, principles, or files they applied. Ask for design notes generally and grade chain-following from code shape, not self-report.
- Sanitize directory and slug names. Use project-shaped names a user might pick.
- Don't tell the candidate other candidates exist.
- The judge can know it's judging but sees outputs by sanitized label only, never by model name.
- Comparing two variants: one judge scores both sets in a single pass on one scale, blind to which set each came from.

**Steps:**

1. **Frame.** State what variant is under test and what behavior counts as success. Write the rubric (3-6 concrete criteria) for the judge only. Hold it back from candidates.
2. **Set up sanitized environments.** Per-candidate working dir with the variant in place. Plant any context an organic task would have: a project skeleton, the skills the candidate would naturally read.
3. **Author one organic prompt.** What a user would type. No leakage of what's being measured.
4. **Spawn the candidate panel.** Read and apply `../../arena/SKILL.md`. With no panel configuration, run three independent inherited-model candidates. Give each candidate the same prompt and a separate writable directory. Bound work to native capacity and run excess candidates in waves. Use only available overrides from `.cstack/models.json`.
5. **Spawn one blinded judge.** Prefer a different available model when the session already exposes one. When no subagent slot is available, run the judge pass in this session as a separate re-scoped pass, label it `single-agent`, and report the missing independence. When the session has only one model, label the verdict `single-model` and never describe it as a blinded multi-model bakeoff. If an explicit judge model is unavailable, stop that selection, inherit, and keep the `single-model` label. The judge sees sanitized labels and the rubric, never model names.
6. **Verify from observable artifacts.** Inspect each candidate's files, commands, diffs, and tool results available in this task. Use a native task transcript only when the current session exposes it. Never search unrelated conversations or private workspace history. Treat self-report as a pointer, not proof.
7. **Read every candidate output yourself** end to end. Compare to the judge's verdict. Disagreement means a model is biased or the rubric is ambiguous. Synthesize.

**Reply:** variant under test, rubric, per-candidate notes, judge's verdict, your synthesis, and a recommendation for whether to promote the variant. Name the judge label (`single-model` or multi-model). Every claim carries its evidence or its label in the same sentence. Measured, inferred, or guess. A prediction or an unseen cause is a guess. Never hand the human a check you could run.

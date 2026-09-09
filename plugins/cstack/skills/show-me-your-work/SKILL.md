---
name: show-me-your-work
description: "Keep a reviewable decision trail for long-running or unattended work: a TSV log with one row per decision (what, why, evidence, result). Local by default; commit it when a reviewer needs the trail to trust the result. Use for $cstack:show-me-your-work, autonomous or multi-phase runs, or work a human reviews after stepping away."
---

# Show me your work

Runtime: [`../cstack/references/codex-runtime.md`](../cstack/references/codex-runtime.md).

Keep one canonical log.

## The format

A single TSV file, one row per decision. Cells stay single-line. Evidence is a pointer, not prose.

Copy `references/decision-log-template.tsv` (the header row) to start a clean log. Columns:

- **ts.** ISO8601 timestamp.
- **phase.** The phase or workstream.
- **decision.** What was chosen or done, one line.
- **why.** The reason in plain words. If a principle drove it, say it plainly, not as a jargon tag.
- **evidence.** A link or path that proves it: commit SHA, PR number, `file:line`, or an artifact, trace, or screenshot path. Never a paragraph.
- **result.** The outcome or predicate state: `tests green`, `reverted`, `pixel-diff 0`, `INCONCLUSIVE`, `open`.

An example, plain-spoken so a reviewer reads it at a glance. This is illustration only. Don't copy these rows into a real log.

```
ts	phase	decision	why	evidence	result
2026-05-24T09:02:00Z	frame	counted the work first, about 100 components and roughly 75 hours	wanted to know the size before starting a long run	commit 3a9f1c2	found 5 things to sort out before starting
2026-05-24T09:40:00Z	harness	took screenshots of the old version before changing anything	so we can compare old against new and catch any visual change	scripts/snapshot.sh, baseline/	saved 120 reference screenshots
2026-05-24T11:15:00Z	widget	moved the widget styles over without changing how it looks	keep the change small and the result identical	commit 7c21e0a, pixel-diff 0	looks identical, tests pass
2026-05-24T12:30:00Z	widget	threw out a helper's work because its screenshots were blank	checked the real files instead of trusting its summary	worktree reset	reverted, tightened the instructions for next time
```

## Logging a row

Write each entry the way you'd tell a teammate what you did. Plain words, concrete actions, no AI speak or abstract jargon (the **unslop** skill applies to log text too).

Use the helper `scripts/log.sh <logfile> <phase> <decision> <why> <evidence> <result>`. It stamps `ts`, writes the header on first use, strips stray tabs/newlines, and prefixes any cell starting with `=`, `+`, `-`, or `@` with a single quote. A bare `printf` appending a row works too, but mind those same bytes if cells come from generated or user-supplied text.

Log decision points and checkpoints, not every action: a fork chosen, a unit completed with its verification result, a pivot or revert with its trigger, a blocker surfaced, a gate fixed. For loop runs, one row per iteration. Skip the trivial and self-evident.

## Where it lives

By default the log is an untracked working artifact at `.cstack/tasks/<task-slug>/decisions.tsv` in the target workspace. Give concurrent tasks distinct directories.

Export a sanitized copy to a tracked report path only when the user explicitly requests a committed audit trail. Preserve the original task log and exclude credentials and unrelated conversation content.

## Rules

- One row is one decision or checkpoint.
- Append-only. A wrong call gets a new row that supersedes it. Never edit or delete history.
- Prefer evidence produced by committed scripts over hand-made one-offs (the **encode-lessons-in-structure** principle skill).

## Audit the log against the task record

At the end of the run, check that the log told the truth. Prefer native task-history tools scoped to this project and task. Otherwise use the current context and checkpoints. Read a local transcript only when its metadata explicitly matches this project and session; never infer a storage path or scan unrelated projects. Walk the log against what actually happened:

- Every row maps to a real action. Cut invented or aspirational entries.
- Each row's evidence resolves and shows what the row claims.
- A fork, pivot, or abandoned approach that shaped the work but isn't logged is a gap. Add it.
- Drop padding.

Fix the log, not the story. If the work diverged from what a row claims, the row is wrong.

## Independent review of the trail

Before handing back, use an independent native reviewer when delegation is available and permitted. Resolve `judgment and prose` under the runtime contract and preserve both selected fields at dispatch. The reviewer reads the audit trail and task record, and flags weak evidence or risk. When delegation is unavailable or prohibited, perform the scan directly and disclose that no independent review occurred.

- Decisions logged with weak or absent evidence.
- Verification steps skipped or claimed without proof in the task record.
- Choices that look risky in hindsight (premature, scope-creeping, papering over a symptom).
- Gaps the user would otherwise miss on a casual skim.

Every reply for a run that produced a trail ends with an "Attention" section. Identify an actual delegated reviewer as `independent native reviewer`, or label the fallback `single-agent audit`. Include a model only when the runtime reports it. List flags with specific rows or moments; do not treat a missing independent review as an independent clean verdict.

## Reviewing the trail

Read top to bottom, follow the evidence pointers, spot-check. GitHub renders an explicitly exported TSV as a table. Run `column -s$'\t' -t "<workspace>/.cstack/tasks/<task-slug>/decisions.tsv"` with the actual workspace and task slug to inspect the local trail in a terminal.

## Composing this skill

Other skills route their audit trail here instead of inventing one. Reference it by name and let it own the format. Don't restate the columns.

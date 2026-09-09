---
name: no-comments
description: "Use for $no-comments to run an independent comment review, fix accepted findings, and offer encodings for claimed constraints."
---

# No comments

Runtime: [`../cstack/references/codex-runtime.md`](../cstack/references/codex-runtime.md).

Run an independent comment review, then act on accepted findings.

## Scope

Use the caller's files or diff. Otherwise use the current diff against the base branch, default `main`, including the working tree.

## Steps

1. Read [`../cstack/references/agents/comment-reviewer.md`](../cstack/references/agents/comment-reviewer.md) and pass that prompt plus the scope to one available native subagent. The assignment is read-only; no named registered role is required.
2. Inspect its report. Reject scope escapes, exception-protected deletions, and flags that treat intentional comments as guilty. A keep survives only with proof that the constraint cannot be expressed in code. Audit missed scoped lint and TypeScript suppressions. Correctness or safety suppressions remain actionable. Before accepting thin `IMPORTANT` or `do not remove` findings, run `$how` or `$why` on the symbol. Rerun one rejected review with the failure named. Reject a second, report it open, and fail `$no-comments`.
3. Fix trivial accepted findings directly by deleting dead narration, dropping a workaround, or using the real API. If any fix needs a shape, run `$architect` once for the accepted set and surrounding code. Stop at the sketch; Step 4 implements it.
4. Implement the smallest root-cause fix in scope. Remove every named workaround. If the root cause is out of scope, land the smallest in-scope fix and report the rest open. The **principle-fix-root-causes** and **principle-redesign-from-first-principles** skills guide intent only. Neither authorizes widening the fence nor fixing instances outside it. Never bolt on symptom guards.
5. For constraint comments such as `do not remove`, `do not change wording`, or `talk to X before changing`, leave proven constraints about things outside the codebase. Offer the cheapest in-scope type, runtime check, test, or CI lint. Encode it when the current task authorizes that edit; otherwise keep the proven comment and report the possible encoding.
6. Report the deletion count, restored comments, reruns, architect sketch, fixes, encoding offers, encodings, unenforced constraints, and other open work.

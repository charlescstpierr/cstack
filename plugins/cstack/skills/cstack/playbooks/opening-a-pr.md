### Opening a PR

Follow [the Codex runtime contract](../references/codex-runtime.md).

**You own the PR that goes out. Clean the diff, get an independent verdict, then open it only with the user's grant.** Run this playbook only when the user authorized PR creation. Preparing commits or finishing another playbook does not grant that authority.

1. **Worktree.** Use a clean git worktree based on the intended base branch. Give parallel writers separate worktrees and branches. Preserve unrelated user changes. Do not reset or discard a dirty tree to make room.
2. **Deslop.** Run `../../deslop/SKILL.md` over the diff before each commit. Keep `deslop skipped: <reason>` when a step genuinely cannot run it.
3. **Commits.** Follow the runtime contract’s [local commit rule](../references/codex-runtime.md#local-commits). Authorized implementation includes small, ordered local commits by default. Do not defer them until PR creation. Each commit must be coherent and pass its relevant check. Amend when a correction belongs to the commit just made. Create a new commit for a separable change.
4. **Comment review.** Read and apply `../../no-comments/SKILL.md` before review. This step is mandatory. It is not only for an explicit request.
5. **Independent verdict.** Before the PR is presented as ready, a verdict comes from an actor that did not write the diff. When no subagent is available, run a separate review pass with a clean re-read of the diff and label it `single-agent review`. Name the missing independence. For a contested design or a high-impact change, also read and apply `../../interrogate/SKILL.md`.
6. **Prose.** Read and apply `../../technical-writing/SKILL.md` and `../../unslop/SKILL.md` to the title, description, and commit body. Inspect the full diff, including comments and suppressions, for generated filler, redundant comments, speculative abstractions, and unrelated edits.
7. **Titles.** Use `type(scope): subject`. Choose `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, or `perf`. Use the changed area as the scope. Keep the subject short and imperative. Do not add a trailing period.
8. **Descriptions.** Explain why the change exists, what the diff changes, its meaningful boundary, and how you proved it. Keep the body short enough to become a useful squash commit. Use these sections when they have content:

- `## Why` states the intent and approach.
- `## Scope` names the important symbols and paths.
- `## Tradeoffs` names rejected alternatives a reviewer may ask about.
- `## Blast radius` names affected callers, users, or systems and the main risk. Read and apply `../../blast-radius/SKILL.md` when the diff changes a widely used symbol, a module boundary, or a shared contract.
- `## Verification` names each command or real interface check and its result.

Attach screenshots or video when they prove a visual or interaction claim. Keep full logs, lane reports, and long decision trails in linked artifacts under `.cstack/` or a repository-approved path.

9. **GitHub.** Use git and `gh` for all branch and PR work. Resolve the repository, base branch, current branch, and remote before the first write.
10. **Size and stacks.** Prefer narrow PRs that each pass their own checks. A stack is a base-branch chain. The root PR targets trunk. Each child branch is based on its parent's exact tip and its PR targets the parent branch. Use `gh pr create --base <parent-branch>` to create a child and `gh pr edit <pr> --base <parent-branch>` to retarget one. Branch directly from trunk only for independent work.
11. **Readiness.** Open PRs ready for review unless the user asked for drafts. Verify the result with `gh pr view <number>` before reporting its state. If a PR opened as a draft by mistake, run `gh pr ready <number>`.
12. **Babysit.** Opening a PR does not start `babysit.md`. Return the URL and finish the current authorized scope. Start a babysit only when the user asks to inspect or drive PR status.

A subagent that opens an authorized PR runs this same sequence, including deslop, no-comments, the independent verdict, interrogate when the change is contested or high-impact, then technical-writing and unslop. It returns the URL and exact head SHA. The parent reviews the result and owns the final report.

**Reply:** the PR URL, the head SHA, the deslop result, the comment-review result, and the verdict with its author. Every claim carries its evidence or its label in the same sentence. Measured, inferred, or guess. A prediction or an unseen cause is a guess. Never hand the human a check you could run.

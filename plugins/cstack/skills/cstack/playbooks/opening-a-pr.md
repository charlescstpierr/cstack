### Opening a PR

Follow [the Codex runtime contract](../references/codex-runtime.md).

Run this playbook only when the user authorized PR creation. Preparing commits or finishing another playbook does not grant that authority.

**Worktree.** Use a clean git worktree based on the intended base branch. Give parallel writers separate worktrees and branches. Preserve unrelated user changes. Do not reset or discard a dirty tree to make room.

**Commits.** Build small, ordered commits when commits are in scope. Each commit must be coherent and pass its relevant check. Amend when a correction belongs to the commit just made. Create a new commit for a separable change.

**Review.** Read and apply `../../no-comments/SKILL.md` before review. Read and apply `../../technical-writing/SKILL.md` and `../../unslop/SKILL.md` to the title, description, and commit body. Inspect the diff for generated filler, redundant comments, speculative abstractions, and unrelated edits. Do not depend on an unavailable cleanup integration.

**Titles.** Use `type(scope): subject`. Choose `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, or `perf`. Use the changed area as the scope. Keep the subject short and imperative. Do not add a trailing period.

**Descriptions.** Explain why the change exists, what the diff changes, its meaningful boundary, and how you proved it. Keep the body short enough to become a useful squash commit. Use these sections when they have content:

- `## Why` states the intent and approach.
- `## Scope` names the important symbols and paths.
- `## Tradeoffs` names rejected alternatives a reviewer may ask about.
- `## Blast radius` names affected callers, users, or systems and the main risk.
- `## Verification` names each command or real interface check and its result.

Attach screenshots or video when they prove a visual or interaction claim. Keep full logs, lane reports, and long decision trails in linked artifacts under `.cstack/` or a repository-approved path.

**GitHub.** Use git and `gh` for all branch and PR work. Resolve the repository, base branch, current branch, and remote before the first write.

**Size and stacks.** Prefer narrow PRs that each pass their own checks. A stack is a base-branch chain. The root PR targets trunk. Each child branch is based on its parent's exact tip and its PR targets the parent branch. Use `gh pr create --base <parent-branch>` to create a child and `gh pr edit <pr> --base <parent-branch>` to retarget one. Branch directly from trunk only for independent work.

**Readiness.** Open PRs ready for review unless the user asked for drafts. Verify the result with `gh pr view <number>` before reporting its state. If a PR opened as a draft by mistake, run `gh pr ready <number>`.

**Babysit.** Opening a PR does not start `playbooks/babysit.md`. Return the URL and finish the current authorized scope. Start a babysit only when the user asks to inspect or drive PR status.

A subagent that opens an authorized PR returns the URL and exact head SHA. The parent reviews the result and owns the final report.

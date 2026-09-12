---
name: deslop
description: "Strip slop out of a code diff before it is committed or reviewed. Use for $cstack:deslop, 'deslop it', 'clean this diff', and as the required pre-commit pass in every cstack implementation playbook. Use $cstack:unslop for prose and $cstack:no-comments for a delegated comment review."
---

# Deslop

Runtime: [`../cstack/references/codex-runtime.md`](../cstack/references/codex-runtime.md).

Slop is code that survives review because nobody can point at the line that is wrong. It is not a style question. Narrating comments and defensive dead weight read as unfinished, and the extra code is where the next bug hides.

Three cleanups, three targets. `deslop` cleans the code. [`unslop`](../unslop/SKILL.md) cleans the prose. [`no-comments`](../no-comments/SKILL.md) hands the comments to a reviewer who did not write them.

Deslop runs over **the diff**, never the repository. It removes weight. It never changes behavior.

## When it runs

- Before every commit of an authorized implementation or documentation change.
- Before handing a diff to a reviewer, a PR, or a verification lane.
- On request: `$cstack:deslop`, "deslop it", "clean this diff".

A playbook that skips it keeps `deslop skipped: <reason>` in its plan and its reply. There is no silent skip.

## Bound the scope

1. List the task's own changed paths. Use `git diff --stat` against the base, or `git diff --stat --cached` for staged work. Never widen to files the task did not touch.
2. Read every added and modified hunk in full. A hunk you did not read is not desloped.
3. Preserve pre-existing unrelated changes exactly as they are, and say so in the report.

## The slop catalogue

Classify every added line as load-bearing, slop, or uncertain. Delete the slop. Keep the uncertain lines and name each one in the report.

**Narrating comments.** A comment that restates the next line, labels an obvious block, or announces a section. Delete. Keep a comment only for a non-obvious reason the code cannot express, and for licenses, public contracts, accessibility rationale, and verified tool constraints.

**Unsupported guards.** A null check, `try`/`catch`, default, or early return for a state the types, the call sites, or an invariant already exclude. Delete the guard and let the real contract hold. Keep it when a caller outside the module can actually produce that state, and name the caller.

**Dead compatibility paths.** A fallback for a shape that no longer exists, an alias kept "for safety", a branch for a version the project dropped, a re-export left behind by a migration. Delete, and migrate the remaining callers in the same change. Half a migration is slop with a deadline.

**Swallowed errors.** `catch` that logs and continues, a bare `except`, an error converted to a default value. Either handle the failure or let it propagate. Keep a swallow only where the surrounding contract documents best-effort behavior.

**Speculative generality.** A parameter, option, hook, strategy, or config flag with one caller and no second one in sight. An interface with one implementation. A factory that constructs one thing. Inline it.

**Ceremony.** A wrapper that forwards its arguments unchanged, a barrel file added for one symbol, a constant that is used once next to its definition, a variable that exists only to be returned.

**Duplicated logic.** The same computation pasted into a second place instead of called. Call it. When the two copies are genuinely diverging, say why in the report instead of extracting a shared abstraction that fits neither.

**Redundant state.** A stored value that is derivable from other state, a boolean pair that encodes a state machine, a cache with no invalidation path. Derive it, or model the states.

**Placeholder residue.** `TODO`, `FIXME`, "implement later", commented-out code, a mock return, a stub that returns a plausible constant, debug logging, a scratch file. Either finish it inside the authorized scope or delete it and record the follow-up in the reply. Never ship a placeholder as if it were the feature.

**Unrelated edits.** Reformatting, import reordering, rename churn, or a drive-by fix outside the task's purpose. Revert those hunks. A real improvement you found goes in the reply as a follow-up, not in this diff.

**Test padding.** A test that asserts a default, a field copy, a forwarding call, a mock echoing its own input, a bare "does not throw", or a parameter row that walks the same path as the row above it. Delete it. A test earns its place only when a plausible bug would fail it.

**Misleading names.** `data`, `utils`, `helper`, `manager`, `temp`, `newThing`, `handleX` for something that is not a handler. Rename to what the value is or what the function does. Renaming a symbol that crosses the module boundary is a public change: do it only inside the authorized scope and migrate every caller.

**Invented documentation.** A doc line, changelog entry, or comment describing behavior the diff does not implement, or a measurement nobody took. Delete it or replace it with the claim you can actually support.

## Prove it was weight

Deslop is behavior-preserving by construction, so it is checkable.

1. Run the same verification that already covered the change: the test, the command, or the runtime probe named by the playbook.
2. A check that flips from pass to fail means a deleted line was load-bearing. Restore that exact line and reclassify it. Do not "fix" the check.
3. When no check covers a deleted line, say so in the report. An untested deletion is a claim, not a proof.

## Forbidden

- Changing behavior, output, public signatures, or error semantics.
- Touching files outside the task's changed paths.
- Deleting licenses, copyright headers, accessibility rationale, security notes, or a comment that records a verified tool or platform constraint.
- Extracting a new abstraction. Deslop only subtracts.
- Rewriting someone else's uncommitted work.
- Calling the pass complete without rerunning the change's own verification.

## Reply

One table plus the leftovers.

| category | file:line | removed | why it was weight |
|---|---|---|---|

Then:

- Lines kept as uncertain, with the reason each one might be load-bearing.
- Deletions no check covers.
- Follow-ups found but deliberately left out of this diff.
- The verification command rerun after the pass, and its result.
- `deslop skipped: <reason>` when a playbook step could not run it.

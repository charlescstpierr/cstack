---
name: interrogate
description: "Use for $cstack:interrogate, \"adversarial review\", \"multi-model review\", \"challenge this\", \"stress test this code\", \"find blind spots\", or \"tear this apart\". Independent reviewers challenge changes from several angles."
---

# Interrogate

Runtime: [`../cstack/references/codex-runtime.md`](../cstack/references/codex-runtime.md).

Spawn exactly the configured number of independent native reviewers to adversarially review code changes. Each reviewer gets the same scope snapshot, approved requirements evidence, prompt, and rubric, with a primary axis assignment. The adversarial signal comes from independent passes and, when verified model overrides are available, model diversity. Do not add reviewers beyond the configured panel.

The deliverable is a synthesized verdict. Do NOT auto-apply changes.

Follow the runtime contract's direct inheritance path when unconfigured; otherwise resolve each named role with its helper and pass the complete selection, including reasoning effort, to each native spawn. Report host capability gaps rather than dropping a selected field.

## Step 1, Determine Scope

Identify what to review from context:

- If the user points at specific files or a diff, use that
- If the user asks for current work or work in progress, freeze the actual base and `HEAD` commit SHAs once. Capture `git diff <base-sha>...<head-sha>`, `git diff --cached`, and `git diff` for committed, staged, and unstaged tracked changes, then list untracked files with `git ls-files --others --exclude-standard` and snapshot their contents with native reads. Never run `git add`, `git stash`, `git checkout`, `git reset`, or another command that changes the worktree. Record the snapshot time; if the worktree changes while it is being read, state that the file-content snapshot may be non-atomic.
- If the user asks for a branch, commit range, or PR review, freeze the resolved base and head SHAs once and review only that commit-to-commit scope. Do not silently include dirty worktree changes.
- If the user's message references recent work, gather the relevant files and preserve the requested scope.

Package the frozen scope (or file-content snapshot) plus only the surrounding context files the reviewers need to understand the code. A three-dot comparison is valid only for the frozen commit SHAs; it does not prove coverage of staged, unstaged, or untracked work.

## Step 2, State the Intent

Before spawning reviewers, state the intent and the requirements evidence explicitly. Requirements come only from a user-approved spec, issue, or conversation statement. Do not infer requirements from the implementation, commit messages, or the code's apparent behavior. If no approved requirements source exists, record a Spec evidence gap and continue the Standards and adversarial review without inventing or blocking on requirements.

Derive the intent from:

- The user's message
- An approved spec or issue supplied by the user
- An approved PR description or conversation statement

Write one clear paragraph and name every supplied requirements source. If the approved source is incomplete, report the gap instead of filling it from the code.

## Step 3, Spawn Reviewers

Resolve `interrogate reviewers` once under the runtime contract. Its panel length is the exact reviewer count, bounded only by native concurrency; queue excess attempts in waves. Preserve the complete model and reasoning-effort selection for every position. When no subagent slot is available, run each reviewer pass in the same session as a separate, explicitly re-scoped pass, label the result `single-agent`, and report the missing independence. Absent capacity never deletes a reviewer or an axis. The default panel has three reviewers with these responsibilities:

- Reviewer 1: Standards, using the repository's supplied standards sources.
- Reviewer 2: Spec, using only the approved requirements evidence. With no approved source, report the evidence gap and do not invent requirements.
- Reviewer 3: Adversarial, covering correctness, security, root cause, verification, and maintainability.

For a two-reviewer panel, combine Adversarial with Standards and keep Spec separate. For a one-reviewer panel, cover all axes in one pass and disclose that there are no independent axis reviews. For a panel larger than three, keep these first three assignments and give every additional reviewer full coverage. Every reviewer may report another axis's high-impact finding when the evidence supports it, while keeping the assigned axis primary. This preserves the configured count; do not add a second "Matt" panel.

Read `references/reviewer-prompt.md` and fill in the template with:
1. The stated intent
2. The frozen scope snapshot, including its base and head SHAs and whether dirty worktree files are included
3. The approved requirements evidence, or the explicit Spec evidence gap
4. The reviewer's primary axis and the other axes it may report when high impact
5. The diff or file contents
6. The review rubric from `references/rubric.md`
7. The code-quality lens from `references/code-quality-review.md`

The same filled template goes to all reviewers, so every pass applies the code-quality lens.

## Step 4, Synthesize

As results come back, build a unified picture:

1. **Parse all findings** from the reviewers and retain each finding's primary axis.
2. **Keep Standards and Spec outcomes separate.** Consensus is evidence within an axis, not a reason to downgrade a unique Spec requirement finding because only one reviewer had the Spec assignment.
3. **Identify consensus**. Findings raised by two or more reviewers independently are highest signal within their axis.
4. **Identify lone-reviewer findings**. Still worth reading, especially concrete Spec, security, or correctness findings; weight them by evidence, not by reviewer count alone.
5. **Deduplicate**. Reviewers may describe the same issue differently. Merge these only when they share the same axis and mechanism, and note which reviewers raised them.
6. **Note disagreements**. If one reviewer flags something and another explicitly says the opposite, keep the disagreement under the relevant axis.
7. **Reject scope drift**. Discard findings based on files or requirements outside the frozen snapshot, and call out any unverified claim about changing worktree content.

## Step 5, Lead Judgment

You are the lead reviewer, a pragmatic senior engineer, not a neutral aggregator.

Read `references/lead-judgment.md` for the full framework.

Categorize every finding using these buckets:

- **Act on**. Real issues affecting correctness, security, or maintainability given the actual goals. These would block a real PR.
- **Consider**. Legitimate points, but you're not sure they outweigh the cost of addressing them right now. Worth the user's attention.
- **Noted**. Technically valid but not actionable. Context-dependent, premature optimization, or low-impact given the current stage.
- **Dismissed**. Wrong, nitpicky, or missing context. Brief explanation why.

For each finding, include:
- Which reviewer or reviewers raised it
- The axis: Standards, Spec, or Cross-cutting
- The category (act on / consider / noted / dismissed)
- A one-line rationale for the categorization

## Output Format

Present the verdict in this structure:

Every claim carries its evidence or its label in the same sentence. Measured, inferred, or guess. A prediction or an unseen cause is a guess. Never hand the human a check you could run.

### Intent
> [The stated intent paragraph from Step 2]

### Reviewers
- Reviewer [label]: [model name when known, otherwise inherited], [N findings] (one bullet per reviewer)

### Standards
[Standards findings, categorized as act on / consider / noted / dismissed. Cite the supplied standard or label a baseline judgement call.]

### Spec
[Spec findings, categorized as act on / consider / noted / dismissed. Cite the approved requirement. If no approved source exists, state the evidence gap and do not manufacture findings.]

### Cross-cutting and adversarial
[High-impact findings that cross axes or came from the adversarial assignment. Keep their original axis labels.]

### Act On
[Cross-cutting findings that should be addressed. For each: description, which reviewers raised it, why it matters.]

### Consider
[Cross-cutting findings worth thinking about. For each: description, which reviewers raised it, tradeoff involved.]

### Noted
[Valid but low-priority. Brief list.]

### Dismissed
[Rejected findings with brief rationale.]

### Agreement Map
[Where did reviewers agree, where did they diverge, and what does the pattern reveal?]

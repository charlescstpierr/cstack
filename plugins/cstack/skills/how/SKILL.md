---
name: how
description: "Use for \"how does X work\", code walkthroughs before changing something, and placement / ownership / layering questions (\"where should this live\", \"which package owns this\", \"is this the right layer\"). Explains subsystem architecture, runtime flow, onboarding mental models. Use why for motivation."
---

# How

Runtime: [`../cstack/references/codex-runtime.md`](../cstack/references/codex-runtime.md).

Explore the codebase to answer "how does X work?" questions. Produce architectural explanations at the level of a senior engineer onboarding onto a subsystem, enough to build a working mental model, not so much that it reads like annotated source code.

Follow the runtime contract's direct inheritance path when unconfigured; otherwise resolve each named role with its helper and pass the complete selection, including reasoning effort, to each native spawn. Report host capability gaps rather than dropping a selected field.

When this skill is explicitly invoked or selected by the router, honor saved `how explorer` and `how explainer` choices without requiring the user to select them again. Choose the owner before doing the work. Use the runtime contract for unavailable selections or native capabilities.

## Step 1. Assess Complexity

If the scope is ambiguous, state your interpretation and explore. The user can redirect.

- **Simple** (a single module, a small utility, a narrow question such as "how does function X work"): use the configured explainer when present; otherwise the parent explores and explains directly. Go to Step 2b.
- **Complex** (a subsystem spanning multiple files or services, a cross-cutting feature, a full architectural overview): explore independent useful slices, then choose the synthesis owner in Step 3. Go to Step 2a.

When in doubt, take the simple path.

## Step 2a. Explore (complex questions only)

Decompose the question into 2 to 4 exploration angles, each a distinct slice of the subsystem. Spawn native review-only subagents concurrently when those slices are independent and useful. They inherit the parent model by default. If no slice earns delegation, inspect the angles directly in the parent. If `.cstack/models.json` defines `how explorer`, follow the runtime contract and do not silently substitute an unavailable explicit override.

Each explorer gets the prompt in `references/explorer-prompt.md` with its angle filled in. Then go to Step 3.

## Step 2b. Direct Explain (simple questions)

If `.cstack/models.json` contains `how explainer`, give that native subagent the bounded question and `references/explainer-prompt.md` to explore and explain in one pass. Otherwise inspect the relevant files and explain directly. Do not perform the same exploration in both parent and child. The parent checks the resulting evidence and citations. Go to Step 4.

## Step 3. Synthesize (complex questions only)

Once exploration is complete, choose one synthesis owner. Use a native review-only subagent when `how explainer` is configured, or when a large or contested finding set needs a distinct synthesis pass. Otherwise synthesize in the parent. Follow the runtime contract for the configured model and effort; missing settings inherit. The parent checks the evidence rather than repeating the delegated synthesis.

If using a synthesis subagent, build its prompt from `references/explainer-prompt.md` with every explorer's findings filled in.

## Step 4. Present

Present the explanation to the user. When a subagent produced the final synthesis, light edits for clarity or context from the conversation are fine.

## Output Format

The explanation uses the sections defined in `references/explainer-prompt.md`, dropping any that do not apply: Overview, Key Concepts, How It Works, Where Things Live, Gotchas.

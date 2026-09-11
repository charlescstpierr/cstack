---
name: domain
description: "Use when explicitly selected as $cstack:domain or routed during an explicitly selected cstack task to settle project vocabulary and record authorized glossary entries or sparse ADRs."
---

# Domain

Runtime: [`../cstack/references/codex-runtime.md`](../cstack/references/codex-runtime.md).

Use this skill when the user explicitly selects `$cstack:domain`, or when the active `$cstack:cstack` coordinator or its preparation skills route a material terminology decision here. It is for active domain work: resolving vocabulary, checking model boundaries, and recording a small number of durable decisions. Merely reading a glossary is not this skill.

Read `docs/agents/cstack.md` if the project has it; it may define local conventions, but its absence is fine. Do not require setup, Matt Pocock skills, global skills, or another plugin.

## Locate the artifacts

Inspect the repository before choosing paths or formats.

- If the root has `CONTEXT-MAP.md`, use the context it maps for the topic.
- Otherwise use the root `CONTEXT.md` when it exists.
- If neither exists, propose a root `CONTEXT.md` only when a term actually resolves and a document write is authorized. Never scaffold it speculatively.
- Inspect existing ADR locations, numbering, frontmatter, and templates. Follow those conventions. If none exist, a sparse ADR may use `docs/adr/NNNN-slug.md` with one to three sentences.

## Sharpen the language

For each disputed or overloaded term:

1. Find its actual uses in the code and existing domain documents, reusing [`$cstack:how`](../how/SKILL.md) when the flow or ownership is broad. Use observed code as evidence, not as a substitute for the user's product decision.
2. Call out conflicting definitions or synonyms and propose one precise canonical term.
3. Test the boundary with a concrete scenario. Ask the user to choose when the meaning affects business rules, ownership, or externally visible behavior. Never infer a material business decision.
4. Draft a glossary entry that defines what the thing **is**, in one or two sentences, and list rejected synonyms under `_Avoid_`. Keep implementation details, specs, and scratch notes out of `CONTEXT.md`.

Write a resolved entry inline when the current task already authorizes document writes. If it does not, return the proposed entry in chat. Do not ask for approval again for each entry after write authority is established. In Plan mode or read-only work, always return drafts and do not write files.

## Record decisions sparingly

Offer an ADR only when all three conditions hold:

1. The choice is hard to reverse.
2. A future reader would find it surprising without context.
3. It resulted from a real trade-off between alternatives.

Keep the ADR to the repository's existing format and record context, decision, and reason. If a material business choice is still open, ask the user and do not record a decision. When the choice is settled and document writes are authorized, record it without another per-ADR approval loop. Do not turn ordinary implementation choices into ADRs.

## Facts, writing, and judgment

The default is zero extra agents. When independent repository facts need separate coverage, use the configured `how explorer` role, one delegate per fact at most, bounded by native capacity. When a separate document draft is useful and writing is authorized, use the configured `documentation` role. When an independent rationale or judgment pass is useful, use `judgment and prose`. Resolve each role through the trusted helper and forward the complete model and reasoning-effort selection; do not hard-code model names or add a role.

The parent owns the final judgment and verification. This skill never creates goals, implementation changes, trackers, PRs, deployments, or external messages. Its only durable writes are explicitly authorized glossary or ADR documents.

For requirements clarification before domain recording, use [`$cstack:clarify`](../clarify/SKILL.md).

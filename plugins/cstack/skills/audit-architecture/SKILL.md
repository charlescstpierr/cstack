---
name: audit-architecture
description: "Run a bounded, read-only brownfield architecture survey that finds evidence-backed deepening candidates without refactoring. Use for $cstack:audit-architecture or when the user asks what architecture should improve."
---

# Audit architecture

Runtime: [`../cstack/references/codex-runtime.md`](../cstack/references/codex-runtime.md).

Survey the existing codebase for worthwhile architectural improvements. This skill finds and compares candidates; it does not redesign or refactor the code.

## Scope and exploration

1. Use the user's named subsystem or paths as the scope. If none is named, inspect a bounded recent history (`git log --oneline -20`) and follow the files and areas that are actively changing. State the scope before scanning.
2. Read the actual code, callers, tests, configuration, and relevant project guidance in that scope. Do not infer a candidate from filenames or generic architecture advice.
3. If native delegation is available, run at most one bounded, read-only explorer for the initial map. Resolve it as the existing `how explorer` role, preserving the configured model and reasoning effort through the native runtime contract. Give it the scope and ask for paths, symbols, callers, hotspots, and evidence; it must not edit files, spawn descendants, or propose a refactor. If delegation is unavailable or prohibited, inspect in the foreground and say so.
4. The lead agent synthesizes the explorer result with direct inspection. A delegated summary is not evidence until the cited code is read.

## Candidate standard

A candidate must name:

- the affected paths and symbols;
- the problem and current friction, with `path:line` evidence and relevant callers;
- the deletion test: whether removing the proposed module would concentrate complexity behind a smaller interface or merely move it;
- interface depth: what callers currently know, what a proposed seam would hide, and which invariants or policies would gain locality;
- a recommendation: `Strong`, `Worth exploring`, `Speculative`, or `No worthwhile candidate`;
- a plausible before/after sketch labelled **proposed, not verified**.

Use the domain's existing terms. Keep candidates tied to the observed code and be willing to return no worthwhile candidate. Do not invent a second adapter, caller, invariant, performance benefit, or historical reason.

The default report is Markdown in the conversation. In Plan mode or a request that prohibits file writes, keep the report in chat and create no artifact. Otherwise, create a report artifact only when the user asks for or authorizes that output; source and configuration stay read-only. Do not require a browser, CDN, Mermaid, `xdg-open`, or screenshot; use an available browser only when the user explicitly requests visual inspection and the tool exists.

## Hard boundaries

This run is read-only. Do not edit source, tests, `AGENTS.md`, `CONTEXT.md`, ADRs, `.cstack/`, or configuration. Do not create branches, commits, PRs, messages, installations, dependencies, or background work. Do not automatically apply a candidate or start a refactoring playbook.

If the user selects a candidate, pass the evidence and constraints to `$cstack:architect`. Keep the result design-only unless implementation was already explicitly authorized in the same task. Let Architect preserve the configured `architect runners` panel count and each model/reasoning-effort selection; do not add a fixed panel size or substitute another redesign engine.

Use the existing cstack runtime contract for tools and delegation. Missing tools or unavailable model/effort selections are evidence gaps to report, never reasons to fabricate results or silently substitute a selection.

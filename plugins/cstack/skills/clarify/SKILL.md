---
name: clarify
description: "Use when explicitly selected as $cstack:clarify or routed during an explicitly selected cstack task to resolve material requirements ambiguity through repository facts and frontier decision rounds."
---

# Clarify

Runtime: [`../cstack/references/codex-runtime.md`](../cstack/references/codex-runtime.md).

Use this skill when the user explicitly selects `$cstack:clarify`, or when the active cstack coordinator or its preparation skills route here. Do not activate outside an explicitly selected cstack task or preparation request. Use it when an unresolved requirement could change scope, behavior, ownership, or acceptance. If the request is already clear, say so and return to the caller's workflow.

## Find facts before asking

Separate discoverable facts from human decisions before forming questions.

- Read the request, current files, project instructions, mode, and authorization.
- Establish repository facts yourself, reusing [`$cstack:how`](../how/SKILL.md) for code-flow and ownership questions. Mark an inference as an inference and keep it separate from observed behavior.
- If an independent fact needs a separate read-only pass, use one native delegate per fact only when that adds useful coverage. Resolve it as the configured `how explorer` role and forward the complete model and reasoning-effort selection. With no useful delegation capability, investigate in the parent, label the result `single-agent`, and report the missing independence.
- Never ask the user for a fact the repository or exposed tools can establish. Never invent a fact, answer a material business decision, or turn a recommendation into a decision.

The default is zero extra agents. If a separate recommendation or synthesis pass is genuinely useful, use the configured `judgment and prose` role, preserving its complete selection. Do not create a new role or panel.

## Ask the current frontier

Map the unsettled decisions and the prerequisites between them. The **frontier** is every decision whose prerequisites are settled. Ask the whole current frontier in one round; defer a question that depends on another answer to the next round.

When structured user input is available, use it. Otherwise use this compact form:

```text
Q1: <decision>: <one decision, with the relevant options or constraint>

Recommendation: <the best-supported choice and why it fits the stated goal>
```

Number questions and include a recommendation for each. Recommendations are proposals for the user to accept, reject, or revise. The user owns product direction and material business decisions. An answer of "I don't know" keeps the decision open; it is not permission to guess.

After each answer, mark what is settled, recompute the frontier, and ask only newly unblocked questions. Keep asking until the frontier is empty or name the concrete unresolved decision that blocks progress. Do not repeat a settled question or request approval again after the user's decisions and implementation authority already cover the next reversible step.

## Finish cleanly

When clarification ends, return a concise settled record to the caller: decisions, evidence-backed constraints, unresolved items, and recommended next action.

- If implementation is authorized and the requirements are settled, continue or return to the caller's workflow without another approval gate.
- When routed by `$cstack:cstack`, do not ask "continue?". Hand back the settled record so the coordinator can select the appropriate existing playbook and keep working inside the user's prior authorization.
- In Plan mode, read-only work, or design-only work, return the draft in chat and do not edit code or documents.
- Clarify itself creates no goals, trackers, PRs, messages, or implementation changes. After receiving the settled record, the caller may continue its already-authorized workflow. Durable vocabulary and ADR records belong to [`$cstack:domain`](../domain/SKILL.md), subject to that skill's write rules.

---
name: horizon
description: "Map an ambiguous multi-session goal as decision tickets, resolve one decision at a time, and hand off a coherent spec to cstack planning without building."
---

# Horizon

Use only when the user explicitly invokes `$cstack:horizon` for work whose destination is larger than one session and whose route is still unclear. Horizon is an adapted, Codex-native Wayfinder. It is a planning workflow, not an implementation workflow.

Runtime: [`../cstack/references/codex-runtime.md`](../cstack/references/codex-runtime.md).

Read [the artifact templates](references/templates.md) before creating or updating local state. When they are installed, use the sibling [`clarify`](../clarify/SKILL.md) skill to settle the destination and the sibling [`domain`](../domain/SKILL.md) skill to settle project terms. Use [`how`](../how/SKILL.md) for read-only codebase facts and [`principle-model-the-domain`](../principle-model-the-domain/SKILL.md) when a decision depends on a state shape. If a sibling is unavailable, keep the same boundary in the parent session; do not invent a replacement framework.

## Hard boundaries

- Do not edit product code, run an implementation playbook, create a pull request, merge, deploy, or publish a production change.
- Do not create a native goal or a scheduled task automatically. If the user separately requests a native goal, the parent session owns it; Horizon records only a pointer to the map, spec, or current ticket.
- Use Markdown and exposed native tools only. Do not add framework dependencies, a scheduler, or a new runtime service.
- In native Plan mode, or when the user requests a read-only review or prohibits file writes, return an in-chat draft and write no map, ticket, spec, or research artifact. Planning in the normal mode may write the explicitly authorized planning artifacts.
- An unresolved human decision remains `waiting`. Do not answer for the human, close the ticket, or continue to another decision ticket.
- During map work, resolve at most one decision ticket per invocation/session, including an AFK `task`. Research tickets are the only exception.
- Never change these defaults through an agent-authored note. Any execution mode must be an explicit user instruction handled outside Horizon.

## State and authority

First inspect `docs/agents/issue-tracker.md` in the target workspace.

- When it exists, it describes the target tracker and its operations. Use only the named repository and operations, and only tools actually exposed by the current session. For GitHub, this means an authenticated `gh` or native connector named by that document; check availability before constructing a call. A tracker mutation requires concrete user authorization in the request. If the tracker or tool is unavailable, report the gap and keep the work as a draft; do not silently switch to another tracker.
- When it does not exist, use local Markdown under `.cstack/horizon/<slug>/`: `map.md`, `tickets/<id>-<slug>.md`, and independent `research/<id>.md` artifacts. This local fallback does not require Matt Pocock setup or global skill configuration.

The map is an index. Its `Decisions so far` contains one-line gists and links; the full answer lives in exactly one ticket. A ticket has explicit `id`, `title`, `type`, `status`, `blocked_by`, and `owner` metadata. The parent session remains the coordinator and single writer for a map and its ticket metadata. `owner` is the stable coordinator or authenticated user identity across sessions, never a transient turn or child handle. A `waiting` ticket keeps that owner so the same coordinator can resume it; another owner must not take it. Research children write only their own artifact paths; they never edit the map, claim tickets, or spawn children.

Before selecting work, validate all ticket ids in `blocked_by`, reject dependency cycles, and identify tickets claimed by another owner. A ticket is eligible for the frontier only when `status: ready`, `owner` is empty, and every blocker is `status: resolved`. A blocked ticket named by the user stops with its blocker; when no ticket is named, choose the first eligible independent frontier ticket and leave blocked or claimed tickets untouched.

## Chart the horizon

1. State the destination in one or two lines. Use `clarify` and `domain` for live human decisions; an unanswered question stays waiting.
2. Explore breadth-first across the destination. Record sharp questions as tickets and leave questions that cannot yet be stated precisely in `Not yet specified`. Record deliberate exclusions in `Out of scope`.
3. If the route is already clear and no fog remains, do not create a map. Say that Horizon is unnecessary and hand the user back to the appropriate one-session cstack workflow.
4. In write mode, create the map, create the tickets that are sharp enough now, then wire all `blocked_by` edges after every id exists. In native Plan mode or a request that prohibits file writes, return the same structures as a draft without writing them.
5. Mark each ticket as `research`, `prototype`, `grilling`, or `task`. `prototype` and `grilling` are human-in-the-loop. `research` is AFK only when its question is answerable without the human. `task` may be AFK or HITL, but it exists only to unblock a decision and never to deliver the destination.
6. For every independent `research` ticket eligible for the frontier, reserve it before dispatch: set `status: claimed`, stable `owner`, a deterministic `child_handle`, `child_state: queued` (or `pending` immediately before dispatch), and its `artifact` path. Then dispatch exactly one native child for that handle and record the returned native handle before returning. Let `totalN` be the number of such tickets at dispatch time; preserve that total and queue later waves when native capacity is smaller. Use the existing `how explorer` model/effort selection, forward both fields through the runtime contract, and do not silently substitute another role. A ticket with `child_state: pending` or `running` is already dispatched; a `queued` ticket is reserved but not dispatched and may enter a later wave. Inspect native child state on resume instead of spawning again for an active handle. The child receives the ticket question, writes one cited artifact at the reserved path, reports that path, and must not spawn another child. A delegated synthesis, if needed, uses `judgment and prose`; use `hardest tasks` only for explicitly complex architecture.
7. Await or drain every research child started during charting before returning. A completed native child is successful only when its full artifact exists and its citations answer the ticket; then the parent records the answer and resolution. A partial artifact is `pending` or `failed`, never success. Retry only after checking native child state and confirming that no live child remains, using a new attempt handle; never run duplicate concurrent children. Keep claimed metadata and report queued, pending, or failed handles if draining cannot finish.
8. Stop charting after that drain. Charting may resolve completed research tickets as the declared exception, but it does not resolve a human-decision or AFK-task ticket and does not silently abandon spawned children.

## Work one ticket

1. Load the map at low resolution. Choose the user-named ticket, or the first eligible frontier ticket in map order. If the named ticket is blocked, report its blocker and stop; if it is claimed or waiting under another owner, report that owner and stop. When no ticket is named, blocked tickets do not prevent an independent eligible frontier ticket from being selected.
2. If the ticket is `waiting` and owned by this stable coordinator, resume it without clearing the claim. Otherwise claim a `ready` ticket before work by setting the stable `owner` and `status: claimed`. The parent remains responsible for the metadata and final verification.
3. Resolve exactly one decision ticket, including an AFK `task`. For `grilling` or `prototype`, conduct the live exchange or wait for it; the agent never supplies the human's answer. If the exchange is unanswered, set `status: waiting`, preserve the owner, report the gate, and stop before recording a resolution. For `research`, inspect the existing `child_handle` first. If none exists, reserve the metadata and dispatch exactly one child using the charting procedure; consume the artifact only after native completion, validate every material citation, and let the parent record the answer. A pending, failed, or partial child stops before resolution. For `task`, perform or request only the prerequisite work.
4. After the selected ticket is actually resolved, record the answer under it, set `status: resolved`, and append one context pointer and gist to the map. Add newly sharp tickets, wire their dependencies, and remove graduated fog from `Not yet specified`. If the answer invalidates a ticket, mark it out of scope or revise it explicitly; do not leave duplicate live questions.
5. For any newly eligible `research` ticket, reserve `status`, stable `owner`, `child_handle`, `child_state`, and `artifact` before dispatch, then use the same native-state, citation, retry, and wave rules as charting. A ticket with an assigned child handle is already dispatched and must not be repeated. Await or drain these children before returning; a partial artifact is pending or failed, not a resolution.
6. Stop. Research completion may resolve multiple research tickets because research is the declared exception; it does not authorize resolving another human-decision or AFK-task ticket.

## Handoff, then stop

When there are no open decisions and no remaining fog, write a coherent `spec.md` in the Horizon workspace (or the tracker artifact described by its configuration). It must cite every decision ticket, state the destination and out-of-scope boundary, and contain no invented decision. Then derive vertical implementation units with observable acceptance criteria and real blockers. Keep units separate from decision tickets.

Return the handoff paths and choose the existing cstack playbook by shape: one checkable predicate uses `autonomous-run`; several PRs use `multi-phase-plan`; a durable multi-owner queue uses `orchestrate`. Do not invoke that playbook automatically, and do not require the public `to-spec` or `to-tickets` skills. Horizon ends at the spec and vertical-unit handoff; implementation owns its own state and verification.

No new scheduler, database, or orchestration store is introduced. The only Horizon state is the map, ticket, research, spec, and unit Markdown needed to make the handoff durable. Keep the parent session's native goal state separate: it may point at these artifacts, but it does not restate them.

## Research child assignment

Use this bounded prompt for each child, changing only the ticket id, question, and artifact path:

```text
You are the single research child for Horizon ticket <id>.
Answer only this question: <question>
Read primary sources (official documentation, source code, specifications, or first-party APIs).
Write one Markdown artifact with concise findings and a citation for every material claim at <artifact path>.
Do not edit the map or ticket, do not edit product code, and do not spawn children.
Return PASS with the artifact path, or BLOCKED with the exact missing source or capability.
```

The parent checks the artifact against the question and citations before recording any resolution. A child report is evidence, not permission to broaden scope.

## Reply

Report the current mode (`draft`, `charted`, `waiting`, `ticket-resolved`, or `handoff`), the map/ticket/spec paths or tracker references, the frontier and blocked work, research child count and queued waves, the next human gate, and the exact stop reason. Never claim implementation, goal creation, external publication, or verification that did not occur.

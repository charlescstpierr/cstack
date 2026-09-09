# Horizon artifact templates

Use these shapes for local Markdown state. A configured external tracker keeps the same conceptual fields and relationships through the operations named by `docs/agents/issue-tracker.md`.

## Local layout

```text
.cstack/horizon/<slug>/
├── map.md
├── tickets/
│   └── <id>-<slug>.md
├── research/
│   └── <id>.md
├── spec.md
└── units/
    └── <id>-<slug>.md
```

The map and ticket files are the planning record. Research files are child-owned evidence. `spec.md` is the single coherent handoff that cites the decision tickets. Unit files describe build slices and acceptance; they do not redefine decisions.

## Map

```markdown
---
id: map
title: <map title>
type: map
status: open | research-pending | cleared
blocked_by: []
owner: <parent owner or empty>
---

## Destination

<what the whole effort must reach>

## Notes

<domain, companion skills, and explicit user constraints>

## Decisions so far

- [<ticket title>](tickets/<id>-<slug>.md): <one-line gist>

## Not yet specified

- <sharp-enough area to revisit, but not yet a precise question>

## Out of scope

- <excluded work and why>
```

The map indexes closed decisions; it does not repeat ticket answers. Remove fog when it graduates into a ticket.

For local state, the ticket id is the exact `id` metadata value and the filename prefix before the first `-`: `tickets/01-choose-storage.md` has `id: 01`. Map links use the complete filename. Every `blocked_by` entry names another ticket's `id`; reject duplicate ids, missing ids, filename/metadata mismatches, and dependency cycles before selecting work.

## Decision ticket

```markdown
---
id: <id matching the filename prefix>
title: <question title>
type: research | prototype | grilling | task
status: ready | claimed | waiting | resolved | out-of-scope
blocked_by: []
owner: <empty until claimed>
child_handle: <empty unless type is research>
native_handle: <empty until the native child is dispatched>
child_state: <empty | queued | pending | running | completed | failed>
artifact: <empty unless type is research>
attempt: 0
---

## Question

<one decision or prerequisite this ticket resolves>

## Answer

<write only when resolved; link research or prototype artifacts>
```

`blocked_by` contains ticket ids, not prose. A ticket is frontier-eligible only with `status: ready`, an empty `owner`, and all blockers `resolved`. `owner` is a stable coordinator or authenticated user identity and remains set while `waiting`; never claim another owner's ticket or bypass an unresolved blocker. For research, write `child_handle`, `native_handle` (empty until dispatch), `child_state: queued` before dispatch (`pending` once dispatch begins), `artifact`, and `attempt`; record the returned native handle before returning. A `pending` or `running` child is active; `queued` is reserved for a later wave. A nonterminal handle prevents duplicate children. A partial artifact is not a resolution.

## Coherent spec and vertical units

```markdown
# <destination> spec

## Destination
<one paragraph>

## Decisions
- [<ticket title>](tickets/<id>-<slug>.md): <decision gist>

## Observable acceptance
- [ ] <behavior that can fail at the chosen verification seam>

## Out of scope
- <excluded behavior>

## Vertical units
### <unit title>
**Delivers:** <complete behavior visible to a user or caller>
**Blocked by:** <unit ids or None>
**Acceptance:**
- [ ] <independent observable criterion>
```

The spec is the decision-to-build bridge. Each unit crosses the relevant layers and is independently verifiable; choose the existing cstack playbook only after this handoff is complete.

---
name: swarm
description: "Fan out N parallel workers, drain them, and return one report. Use for $cstack:swarm, 'swarm this', or parallel coverage, races, gauntlets, and exploration."
---

# Swarm

Runtime: [`../cstack/references/codex-runtime.md`](../cstack/references/codex-runtime.md).

Fan out N parallel native subagents. They may cover separate slices, race the same brief, or mix both. The parent waits, aggregates, and returns one report.

## Start

Track one item per phase in the current task before launching anything.

1. Frame
2. Fan out
3. Aggregate
4. Report

## Phase A: Frame

1. State the done predicate and the artifact or report the swarm must return.
2. Choose the shape. Partition into slices, race N workers on identical briefs, or mix both. For a race or mixed shape, declare `first pass`, `rank all`, or `best-of` before spawning.
3. Set N from the user or derive it from the shape. Cap N at the native concurrency available in the current session and account for the parent slot.
4. Inherit the parent model by default. If `.cstack/models.json` defines `swarm workers`, follow the runtime contract and report an unavailable explicit override without silently substituting another model. For a model race, name verified overrides up front.
5. Give each worker its own writable output when it writes.

## Phase B: Fan out

Spawn all N native subagents concurrently. Each brief must assign a bounded scope and exclusive file ownership when the worker writes. Use read-only scopes for investigation and review.

Every brief stands alone. Include the goal, scope, exact slice or race arm, how to verify, and what to report. Reports use `PASS`, `ISSUES`, or `BLOCKED` with evidence.

If a worker drops out, proceed with N-1 and note it.

## Phase C: Aggregate

Read the terminal results. For coverage, every required slice needs a result. For a race, apply the selection rule declared up front. Use first pass, rank all, or best-of. Do not paste raw worker dumps.

Keep a compact result table, one-line evidenced issues, and explicit gaps or dropouts.

## Phase D: Report

Return one consolidated in-chat report with the table, issue one-liners, gaps or dropouts, and the race rule when used.

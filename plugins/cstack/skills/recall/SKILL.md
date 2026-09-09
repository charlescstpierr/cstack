---
name: recall
description: "Use for $recall, 'recall my work on X', 'catch me up', 'what have I been working on', or 'where did I leave off'. Reconstructs recent project-scoped task history, live state, and connected evidence into a tight current-state brief."
---

# Recall

Runtime: [`../cstack/references/codex-runtime.md`](../cstack/references/codex-runtime.md).

**Before you start or resume work, you rebuild the user's recent working context and hand back a tight capsule of where things stand now and what to do next.**

Keep it tight and on-topic. Read only what the in-scope threads need, then stop.

Context lives in two records. Project-scoped task history holds what prior agents did and decided. The shared record holds symptoms, shipped or reverted fixes, and current external state. The `$why` skill searches that second record through available source control and connected evidence tools.

Prefer native task-history tools scoped to the active project. If they are unavailable, use the current task context and saved checkpoints. Read a local transcript only when its own metadata explicitly matches the requested project and session; never infer or scan a global transcript path.

1. Classify, then route. One specific prior task to resume is the `session-pickup` playbook, not this. Turning habits into a durable skill is `$automate-me`. If the user already gave you a full state capsule, use it and skip the mining.
2. Lock the scope before searching. Pin the window ("recent" is a real range, default the last 7 days), the topic if named, and the workspace (default the active one. Never read another project's transcripts without being asked). State the scope back. Never quietly turn "all" into "recent N".
3. Fan out across the project-scoped task history when the corpus is large enough. Native subagents inherit the parent model. Search the topic first, read only matching tasks and relevant regions, and skip the active task plus obvious subagent, eval, and test noise. Each returns the same schema, one block per task: topic, user goal, decisions, open threads, struggles and corrections, and artifacts, citing the native task ID. For one or two tasks, search directly.
4. Sweep the shared record whenever the topic names a feature, file, subsystem, area, or bug. Hand it to `$why`, steering the question toward current state, failed attempts, and open reports. Use only available connected sources, record gaps, and run independent source investigations in parallel with task-history mining. Skip this for pure activity recall with no named target.
5. Verify against live state. Take the PRs, branches, and tickets that the mining and the sweep surfaced and check them with `git` and `gh`. When the answer hinges on what an agent actually did (the tools it ran, files it read, errors it hit), read the full transcript, not just a trimmed local copy.
6. Write the brief to the contract below. Group by thread. Stay on the named topic.

## Output contract

Lead with the capsule, then the thread status, then the problems, then the next move. Deeper detail goes below or gets cut.

- **Capsule.** At most 5 bullets. What this work is and where it stands overall.
- **Threads.** One line each, prefixed with exactly one status tag: `[merged #N]`, `[open PR #N]`, `[in flight <branch>]`, `[verified, uncommitted]`, `[reverted #N]`, or `[planned, not started]`. A thread with no tag is not done yet, so tag it.
- **Problems.** At most 5, the recurring ones. Include the symptoms users keep reporting and any fix that shipped and was reverted, so the next attempt starts where the last one failed.
- **Next move.** The single most useful next action, concrete.

An adjacent feature or ticket stays out unless it blocks this one. When the capsule and thread lines outgrow a screen, cut detail before threads. Write the brief through `$unslop`, cite task findings by native task ID and shared-record findings by source, and sanitize private context before any public output.

**Reply:** the brief, to the contract above.

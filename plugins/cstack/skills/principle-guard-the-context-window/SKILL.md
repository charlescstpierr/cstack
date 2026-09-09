---
name: principle-guard-the-context-window
description: "Apply when context is filling up: large outputs, long files, repeated reads, fan-out planning. Route bulk to subagents; keep summaries in the main thread, not raw payloads."
---

# Guard the Context Window

Apply this principle when it is explicitly invoked or an active cstack workflow routes here. Installation alone does not activate it; setup only configures model choices. Respect the user's scope and permissions. This principle never authorizes automatic external messaging. See the [Codex runtime contract](../cstack/references/codex-runtime.md).

The context window is finite and non-renewable within a session. Every token should be worth its cost.

**Why:** Context overflow degrades reasoning quality, creates compression artifacts, and halts progress.

**Pattern:**
- **Isolate large payloads.** Route verbose outputs, screenshots, and large documents to subagents. The main context gets summaries, not raw data.
- **Don't read what you won't use.** Read selectively based on relevance. If a file isn't needed for the current task, skip it.
- **Keep frequently used content inline.** Templates and references used on every invocation belong in the skill file, not in separate files that cost a read each time.
- **Size phases and cap scope.** Limit files per phase, set turn budgets, account for mechanism costs.

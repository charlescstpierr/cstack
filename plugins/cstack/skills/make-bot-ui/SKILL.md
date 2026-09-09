---
name: make-bot-ui
description: "Use for $make-bot-ui or when asked to build the upstream Cursor Grok Bot webhook UI. Reports the integration limit in Codex App and CLI."
---

# Make Bot UI

Runtime: [`../cstack/references/codex-runtime.md`](../cstack/references/codex-runtime.md).

This upstream capability depends on Cursor Grok Bot webhook routines, routine sender-key storage, and Cursor-specific wake events. Codex App and CLI do not expose a drop-in equivalent, so this skill cannot build or claim a runnable substitute.

Report the limitation and link the exact upstream implementation: [Cursor plugins, pstack `make-bot-ui`](https://github.com/cursor/plugins/blob/27e2a62ff94f9af4b5e68435e41cdceacadb840c/pstack/skills/make-bot-ui/SKILL.md).

If the user separately requests a normal local web UI, treat that as a new scoped application task. Do not imply that it wakes a Grok Bot or preserves the upstream webhook semantics.

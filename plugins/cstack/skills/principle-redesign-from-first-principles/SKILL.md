---
name: principle-redesign-from-first-principles
description: "Apply when integrating a new requirement into an existing design. Redesign as if the requirement had been a foundational assumption from day one, instead of bolting it on."
---

# Redesign From First Principles

Apply this principle when it is explicitly invoked or an active cstack workflow routes here. Installation alone does not activate it; setup does not activate workflows. Respect the user's scope and permissions. This principle never authorizes automatic external messaging. See the [Codex runtime contract](../cstack/references/codex-runtime.md).

When integrating a change, don't bolt it onto the existing design. Redesign as if the requirement had been there from the start.

- Read all affected files and understand the current design
- Ask: "if we were writing this from scratch with this new requirement, what would we build?"
- Propagate the change through every reference: types, docs, examples, rationale sections
- Think about the whole redesign, then deliver it incrementally

This is the method for preserving option value when integrating changes into an existing design.

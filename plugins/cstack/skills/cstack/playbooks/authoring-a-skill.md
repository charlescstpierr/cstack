### Authoring or modifying a skill

Follow [the Codex runtime contract](../references/codex-runtime.md).

**You own the skill's voice.**

1. Use the system skill-creator instructions when the current session exposes them. Otherwise follow the repository's current skill format and validator.
2. Validate the skill: frontmatter has `name` and `description`, referenced files exist, cross-skill links resolve.
3. Apply these four writing-for-agents checks to every new or changed instruction:
   - The pointer names the real trigger branch and points at the one source of truth.
   - Every step has a checkable completion criterion.
   - Branch-only detail is progressively disclosed behind a reference instead of bloating every path.
   - Each rule changes a decision, uses positive wording, and appears in one place.
4. For a new instruction, run one real behavior proof in an isolated fixture or the smallest native invocation that reaches it. Inspect the resulting artifact and side effects; a grep for headings or wording is not proof. Keep these checks in this playbook rather than creating a public writing skill.
5. Run **Opening a PR** only when the user authorized PR creation. Otherwise leave a verified local change.

When in doubt, delete. Keep only prose that changes a decision. Tell it to do the thing and skip the reason. Explain only when the rule is confusing without one. Match tone to scope. Point at structural sources (types, READMEs, config) per the [Encode Lessons in Structure](../references/principles/encode-lessons-in-structure.md) principle reference. Delegate to other skills by path. Don't restate. A workflow you keep hitting but isn't captured → propose a new skill.

**Reply:** summary of the skill, key design decisions, validation notes. Every claim carries its evidence or its label in the same sentence. Measured, inferred, or guess. A prediction or an unseen cause is a guess. Never hand the human a check you could run.

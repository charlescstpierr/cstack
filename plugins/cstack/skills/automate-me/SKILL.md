---
name: automate-me
description: "Use for $cstack:automate-me, \"automate me\", \"create/update/refresh my -mode skill\", or turning the user's preferences and working style into a skill. Drafts or revises a personal -mode skill with $cstack:unslop, optionally using recent project-scoped task history."
---

# Automate me

Runtime: [`../cstack/references/codex-runtime.md`](../cstack/references/codex-runtime.md).

A guided flow for turning the user's working conventions into a skill agents will follow. The output is one `-mode` skill tailored to them (e.g. `jay-mode`, `priya-mode`).

This skill sequences an inline mining pass, the native `skill-creator` skill when it is available, and the **unslop** skill. If `skill-creator` is unavailable, write the minimal valid skill directly.

## Flow

### 0. Check for an existing skill

Look recursively for project-local `.agents/skills/**/*-mode/SKILL.md` and personal `$CODEX_HOME/skills/**/*-mode/SKILL.md` matching the user's handle. When `CODEX_HOME` is unset, use `~/.codex/skills`. If one exists and the user did not already say "update my skill" or similar, use the native structured user-input tool to choose:

- Update the existing skill (default for repeat runs)
- Start fresh (rare, ask why before doing it)

Update mode changes the rest of the flow:
- Step 1 mines only history since the skill was last edited (`git log -1 --format=%cI <path>`).
- Step 2 asks what's changed or missing, not what to capture from zero.
- Step 4 edits the existing file in place. Preserve sections the user hasn't contradicted. Revise ones with new evidence. Add new sections only for genuinely new rules.

### 1. Mine their history

Use native task-history tools scoped to the active project when available. Otherwise use the current task context and explicit checkpoints. Read local transcript files only when their metadata explicitly matches the active project and requested session; never guess a storage path or scan unrelated projects.

Survey only the requested time range for recurring patterns. Parallelize bounded history slices when the corpus is large enough to benefit. Each mining subagent returns a short structured list with evidence pointers. Default signals worth hunting:

- Response preferences (length, tone, format, "dumb it down" corrections)
- Delegation habits (subagents, models, specialized workflows, parallelism)
- Verification posture (what "done" means, unit tests vs live repro, reviewers)
- Code and prose discipline (style, principles cited, lint/format tools)
- Process conventions (worktrees, commits, PRs, review/merge tooling)
- Meta preferences (fixing skills mid-task, proposing new ones)

Cross-check across slices before elevating a signal. Patterns seen in 2+ slices are high-confidence. Lone signals are weak and usually get dropped.

### 2. Ask the user directly

Mining misses intent that has not come up yet. Use the native structured user-input tool when available.

Shape: one or two questions with 4-6 options each, `allow_multiple: true` for category questions. Start broad ("Which areas matter most?"), then follow up on selected areas with specific options. After the structured rounds, one free-form chat question catches anything the options missed.

Don't dump 20 questions.

### 3. Cluster findings

Group the combined signals into sections. Common ones (use only what applies):

- **Response style**: length, tone, format.
- **Autonomy**: how much to do without asking, MCP tool use.
- **Understand first**: which skills to reach for when scoping or investigating a change.
- **Subagents**: default, parallelism, model-to-task, specialized workflows.
- **Prose / code discipline**: principles, lint tools, style guides.
- **Review and verify**: repro posture, verification skills, live-testing tools.
- **Process**: git worktrees, commits, PRs, review/merge tooling.
- **Skills**: skill-authoring habits, fix-the-skill-first, proposing new skills.

The **cstack** skill shows the shape. Read it for granularity. Do not copy its content; the user's rules are their own.

### 4. Draft the skill

Use the native `skill-creator` skill when present. Otherwise create a self-contained `SKILL.md` directly. Placement:

- Path: preserve an existing mode skill's category. For a new project-local mode, use `.agents/skills/<handle>-mode/SKILL.md`. For a personal skill, use `$CODEX_HOME/skills/<handle>-mode/SKILL.md` or `~/.codex/skills/<handle>-mode/SKILL.md` when `CODEX_HOME` is unset.
- Handle: the user's first name or chosen identifier.
- Frontmatter `description`: trigger on their name + `$<handle>-mode` + "work in their style", not on generic keywords like "write code" or "review PR".
- Frontmatter formatting: follow `skill-creator` when available. Keep `description` as one YAML scalar. Quote it or use `description: >-` with indented continuation lines when punctuation or wrapping requires it.
- Make invocation explicit by default with `agents/openai.yaml` setting `policy.allow_implicit_invocation: false`. Enable implicit invocation only when the user explicitly wants it.

### 5. Iterate on prose

Apply the **unslop** skill and, when available, `skill-creator`'s writing guidelines to every line.

Show the draft to the user and take feedback. Expect multiple iterations. Cut ruthlessly. A mode skill is not a manual.

### 6. Land it

Validate the skill and leave it in the requested local location. Commit or open a PR only when the user concretely requested that external action.

## Guardrails

- **Don't overfit to one conversation.** A preference stated once and contradicted another time is noise. Require multiple instances before codifying it.
- **Don't be clever.** Restating other skills' contents, inventing metaphors, or writing "poetic" prose for an agent reader is cost without benefit. Keep it operational.
- **Reference, don't inline.** Other skills the user relies on should appear as path references, not pasted excerpts. Same for any principle docs they maintain elsewhere.
- **Keep sections minimal.** Only add a section if the user has a specific, non-default rule there. "Communicate clearly" is not a section. "Short paragraphs. Tables when comparing options. Bullets only when items are genuinely parallel." is.
- **Name conventions generic.** Use "the user" or "the human" in imperatives, not the author's first name.
- **Don't force symmetry.** If a user has no process rules worth writing down, skip the Process section entirely.

## Evaluation

A `-mode` skill is subjective output. A benchmark loop is not useful here. Vibe-check with the user: does it read like them? Did it miss anything? Then ship.

Run a description-optimization loop only if the skill's trigger accuracy turns out to be a problem in practice.

## When not to use

- User wants a task-specific skill (not working conventions): use `skill-creator` when available or write it directly; no mining required.
- User wants to capture one narrow workflow (e.g. "how I write commit messages"). That's a regular skill, not a mode skill.

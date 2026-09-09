---
name: setup-cstack
description: "Guide cstack project setup: preserve project instructions, configure optional model/effort choices and explain preparation workflows. Use for $cstack:setup-cstack or cstack setup changes."
---

# Set up cstack

Read the [native Codex runtime contract](../cstack/references/codex-runtime.md). Core cstack use needs no setup. The setup prepares only the current project; it never activates a workflow or changes global configuration.

## Discover and present

1. Locate the target workspace, normally its Git root or the current directory outside Git. Read existing `AGENTS.md`, `CLAUDE.md`, `docs/agents/cstack.md`, `docs/agents/issue-tracker.md`, domain conventions and `.cstack/models.json` when present. Inspect only the relevant project files; do not read credentials. Resolve this installed bundle's absolute path.
2. Respect the requested scope. A request to change models only uses the existing model-only commands below. General setup also offers project instructions and tracker conventions. A preview, read-only request, cancellation or Plan mode writes nothing in the project; keep proposed choices in the conversation or an allowed temporary artifact.
3. Discover models and efforts from the current native tool schema or authoritative session catalog. For a supported CLI, raw `codex debug models` JSON works; otherwise use a map of confirmed slugs to effort lists from the actual schema. A stale cache is not proof of availability. With no discovery, inheritance remains available. Check whether native dispatch can express both selected fields, with generic roles and supported fork settings.
4. Run the model `show` command. Present existing choices alongside the seven recommendations below, with reasons and any unavailable pair. Offer acceptance, customization by role, inheritance, or cancellation. Preserve unselected roles. Apply choices already explicitly requested without asking again; merely invoking setup does not accept the recommendations.
5. Explain each preparation workflow using the project preview's `workflows` data and the [workflow contract](../cstack/references/codex-runtime.md): `clarify` and `domain` have no delegates by default; Horizon has one child per ready research ticket; an architecture audit has at most one initial explorer. Name the existing role and its effective model/effort for each phase. Ordinary implementation and existing panel sizes remain unchanged. These are dispatch rules, not four new model roles.
6. For project preparation, propose a passive cstack block in `AGENTS.md` and `docs/agents/cstack.md`, preserving surrounding bytes. Existing `CLAUDE.md` stays untouched; the generated AGENTS block can reference its shared project conventions. Existing unmanaged guide content or malformed marker blocks are conflicts to explain and preserve, not permission to replace the file. Do not create empty `CONTEXT.md` or ADR directories.
7. Reuse an existing tracker document unless the user requested a change. When Horizon needs a choice, offer local Markdown or the relevant GitHub repository discovered from this project. Record a GitHub target only after it is selected; do not create labels, tickets, dependencies or remote state during setup. No tracker choice is needed for model-only setup or unrelated workflows.

## Preview and apply project setup

Use the trusted bundled Python helper directly, never a project-local executable copy. Put only accepted settings in an options JSON file outside the project during preview. Omit `model_choices` to preserve all saved model bytes. Omit `tracker` or use `keep` to preserve an existing tracker document and leave an absent one absent.

```json
{
  "model_choices": {
    "how explorer": {"model": "gpt-5.6-luna", "reasoning_effort": "max"}
  },
  "tracker": {"mode": "local"}
}
```

For GitHub use `{"mode":"github","owner":"selected-owner","repo":"selected-repo"}`. Model values must be verified selections, not unconditional defaults. For project instructions with no model or tracker change, use `{}`.

```sh
python3 <absolute-plugin>/skills/setup-cstack/scripts/project.py --workspace <workspace> --catalog <live-catalog.json> preview --options <selected-options.json>
python3 <absolute-plugin>/skills/setup-cstack/scripts/project.py --workspace <workspace> --catalog <live-catalog.json> apply --plan <accepted-preview.json> --options <selected-options.json> --expected-plan-sha256 <approved-plan-sha256>
```

Keep the full preview JSON in an allowed local temporary file. Show its `plan_sha256`, file paths, actions, diffs and workflow rules before application; do not dump the base64 original snapshots into the conversation. Save the exact accepted preview locally, retain its `plan_sha256` from the reviewed output, and pass that value with the same options to apply. Do not reconstruct or edit the plan by hand, and do not recalculate an approval fingerprint from a file changed after review. When the user has already approved those exact changes, proceed without another permission handoff. A stale, tampered, conflicting or invalid preview is rejected. Report that result and create a fresh reviewable preview instead of overwriting the changed file.

The helper validates and stages all edits, then replaces files individually. Ordinary write errors attempt rollback without overwriting intervening manual edits. A process interruption can leave a partial setup; the same accepted preview can resume when each target still matches its original or intended bytes. Report `partial` honestly, retain the preview, inspect the state and resume the accepted operation. This is not a globally atomic filesystem transaction. Never report success from a failed or partial exit.

After success, read the actual generated files and effective model choices. Check that the cstack block is unique, the existing instructions and CLAUDE bytes survived, local state is ignored when created, and no unselected model changed. Report the paths, counts and effective settings, not claims that a model was executed. Setup does not launch paid model probes, install agents or require a restart to use its project settings.

## Model-only setup

The existing helper remains available without preparing project documents:

```sh
python3 <absolute-plugin>/skills/setup-cstack/scripts/models.py --workspace <workspace> --catalog <live-catalog.json> show
python3 <absolute-plugin>/skills/setup-cstack/scripts/models.py --workspace <workspace> --catalog <live-catalog.json> apply --choices <selected-role-map.json> --expected-sha256 <show.sha256>
```

Its `show` output supplies exact group-to-role choices and panel sizes. Build the selected role map only from accepted choices. Keep `.cstack/` untracked without replacing existing ignore rules, then read back and validate the result. The parent session's model remains unchanged.

## Recommendations

These are optional choices, validated against the live catalog before selection:

| Work | Model | Reasoning effort | Rationale |
| --- | --- | --- | --- |
| Exploration | `gpt-5.6-luna` | `max` | Bounded searches and explanations. |
| Simple changes | `gpt-5.6-luna` | `max` | Small edits with clear acceptance checks. |
| Development | `gpt-6-astra` | `low` | Implementation with design judgment. |
| Difficult debugging | `gpt-6-astra` | `medium` | Diagnosis across interacting causes. |
| Code review | `gpt-6-astra` | `low` | Judgment about correctness and risk. |
| Complex architecture | `gpt-6-astra` | `xhigh` | Cross-cutting design and tradeoffs. |
| Documentation | `gpt-5.6-luna` | `max` | Focused prose from established facts. |

## Roles

Simple roles:

- `simple edits`
- `documentation`
- `feature, refactoring`
- `bug-fix`
- `perf-issue`
- `hillclimb`
- `judgment and prose`
- `hardest tasks`
- `how explorer`
- `how explainer`
- `why investigators`
- `why synthesizer`
- `reflect tooling`
- `reflect judgment, divergent, synthesizer`
- `swarm workers`

Panel roles:

- `arena runners`
- `arena cross-judge pool`
- `architect runners`
- `interrogate reviewers`

The cross-judge pool supplies one judge, preferably different from the author when available. Without a pool, use one independent inherited-model judge. Other panel list lengths set the requested number of attempts. Never claim different model families when every pass used the same model.

Values may be legacy model strings, `inherit-parent`, or `{ "model": "confirmed-slug", "reasoning_effort": "supported-effort" }`; panels contain these values. Missing `simple edits` falls back to `feature, refactoring`; missing `documentation` falls back to `judgment and prose`. Other missing roles inherit. Missing panels use three attempts, except the cross-judge pool uses one.

Example requiring no particular model:

```json
{
  "feature, refactoring": "inherit-parent",
  "interrogate reviewers": ["inherit-parent", "inherit-parent", "inherit-parent"]
}
```

A saved configuration does not prove a model can run. Handle rejection at the first actual dispatch as specified in the runtime contract. Do not launch paid test jobs just to finish setup.

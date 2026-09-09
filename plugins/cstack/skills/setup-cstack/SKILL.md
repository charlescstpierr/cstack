---
name: setup-cstack
description: "Configure optional per-role model choices for cstack in the current Codex project. Use for $cstack:setup-cstack or requests to change cstack model choices."
---

# Set up cstack

Read the [native Codex runtime contract](../cstack/references/codex-runtime.md). Core cstack use needs no setup: every role inherits the current model. Configure only the target project.

## Configure

1. Locate the target workspace, normally the current git root or current directory outside git. Resolve this installed plugin's absolute path. Use its trusted `scripts/models.py` directly with Python 3, never a project-local executable copy.
2. Discover models and supported reasoning efforts from the current native tool schema or authoritative session catalog. Save that evidence as JSON: raw `codex debug models` output when that command is supported, or a map of confirmed model slugs to supported effort lists transcribed from the current schema. A stale local cache is not entitlement. Without discovery use an empty map; inheritance remains available. Never inspect credentials or require an API account.
3. Inspect the actual native spawn schema during setup: confirm it can express both `model` and `reasoning_effort`, including any fork or agent-type restrictions in the shared runtime contract. Show any capability gap before offering acceptance; catalog availability alone does not make a pair usable. If this host cannot dispatch explicit efforts, offer inheritance or a supported custom selection instead of accepting those pairs. Run the preview command below. Show the saved choices and all seven recommendation groups, including unavailable reasons. In interactive setup offer **accept recommendations**, **customize**, **inherit parent**, and **cancel**. Accept applies only available groups the user selects; unavailable groups require an explicit supported alternative or inheritance. Customize offers confirmed model/effort pairs per group or role. Inherit replaces only selected roles with `inherit-parent`, keeping panel counts. Cancel writes nothing. Do not apply recommendations merely because setup was invoked. Apply choices already explicitly requested without asking again.
4. Write a temporary JSON file containing only selected role changes. Group `choices` from the preview provide the exact role maps and panel sizes. Apply with the preview's `sha256`; a stale preview requires rereading and showing the changed settings before applying. The helper validates pairs, merges untouched roles and atomically saves `.cstack/models.json`. Invalid configuration or choices leave the file intact. With no saved file and no changes, leave inheritance implicit.
5. Keep `.cstack/` untracked without replacing existing ignore rules. Read back with `show`, report the local path and effective settings. These settings affect subsequent delegates, not the parent session. No global configuration, role installation, restart or paid model test is needed. At dispatch, check the runtime's ability to express both fields as described in the shared contract.

```sh
python3 <absolute-plugin>/skills/setup-cstack/scripts/models.py --workspace <workspace> --catalog <live-catalog.json> show
python3 <absolute-plugin>/skills/setup-cstack/scripts/models.py --workspace <workspace> --catalog <live-catalog.json> apply --choices <selected-role-map.json> --expected-sha256 <show.sha256>
```

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

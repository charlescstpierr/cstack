---
name: setup-cstack
description: "Configure optional per-role model choices for cstack in the current Codex project. Use for $setup-cstack or requests to change cstack model choices."
---

# Set up cstack

Read the [native Codex runtime contract](../cstack/references/codex-runtime.md). Core cstack use needs no setup: every role inherits the current model. Configure only the target project.

## Configure

1. Locate the target workspace, normally the current git root or current directory outside git. Read `.cstack/models.json` if present. Require a JSON object with only the roles below. Simple roles take non-empty strings; panels take non-empty lists of non-empty strings. The `architect runners` panel requires at least two entries for distinct design attempts. Report invalid keys/values and preserve the existing file on error.
2. Inspect the native model-selection schema or an authoritative session model list. Offer only confirmed available models and `inherit-parent`. Never guess slugs, inspect credentials or require an API account. Without model discovery, inheritance remains available.
3. Show effective choices briefly. Apply valid choices already requested; otherwise ask which roles to change. Missing roles inherit. Missing panels default to three independent inherited-model passes, bounded by native concurrency. The cross-judge pool chooses one judge, not three.
4. Validate all selected model names against the available set and any known compatible reasoning settings. Reject an unavailable explicit choice; do not silently substitute. Preserve roles the user did not ask to change. Write validated JSON to a sibling temporary file, then atomically replace `.cstack/models.json`. If the user chooses defaults and no file exists, no file is needed.
5. Keep `.cstack/` untracked without replacing existing ignore rules. Read back and validate the file. Report the local path and effective settings. The next cstack dispatch reads them; do not change global configuration, install agents, activate other tasks or require a restart.

## Roles

Simple roles:

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

Example requiring no particular model:

```json
{
  "feature, refactoring": "inherit-parent",
  "interrogate reviewers": ["inherit-parent", "inherit-parent", "inherit-parent"]
}
```

A saved configuration does not prove a model can run. Handle rejection at the first actual dispatch as specified in the runtime contract. Do not launch paid test jobs just to finish setup.

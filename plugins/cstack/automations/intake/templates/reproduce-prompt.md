# Reproduce-and-fix run prompt

Follow [the Codex runtime contract](../../../skills/cstack/references/codex-runtime.md). Then read and follow [../references/reproduce-and-fix.md](../references/reproduce-and-fix.md).

When this file is copied into a target repository, keep a committed copy of the reproduce instructions next to it or at the path named in configuration. Never follow a plugin cache path.

## Configuration

Read the committed file at:

```text
.github/cstack/intake/configuration.yaml
```

If the config, control adapter, or completed feature map is missing, fail closed. Return `outcome` `blocked` and empty `patch`.

## Trigger

GitHub Actions supplies the event. This job starts through `needs: triage` when the triage output marker is `[intake:bug]` or `[intake:performance]`. Freeze coordinates from the snapshot files. Do not invent them.

- Run context: `.cstack/intake/run-context.json`
- Issue snapshot: `.cstack/intake/source-issue.json`
- All-state issue snapshot: `.cstack/intake/tracker-issues-all.json`
- All-state pull request snapshot: `.cstack/intake/prs-all.json`
- Recent commit snapshot: `.cstack/intake/commits.txt`
- Repository: `repository` in the run context
- Issue number: `issue_number` in the run context
- Marker: `marker` in the run context

Verify the marker is exactly one configured bug or performance marker. If that check fails, stop with empty `patch` and empty `source_comment_body`.

Do not poll. Codex CLI has no inbound wait for a later Slack event. A connector-backed source that was started without a trusted marker fail-closes.

## This run

Reproduce the exact symptom through the real UI twice. Verify an existing fix when a pull request or matching commit already exists. Fill draft-only pull request fields only after before-and-after proof.

Never post. Never commit. Never merge or deploy. The workflow is the coordinator and the only external writer. This process has no `GH_TOKEN`, no network, and no `.git` write.

Keep captures outside the repository, in `control.artifact_directory`. Put every capture required for a source comment or draft pull request in `evidence_paths`; the workflow uploads those files before it posts or opens a draft pull request.

Return one JSON object that matches the reproduce output schema. Required fields:

- `outcome`: `reproduced`, `could_not_reproduce`, `blocked`, `verified_existing_fix`, `insufficient_fix`, or `inconclusive`
- `mode`: `reproduce`, `verify`, or `fix`
- `status_label`
- `source_comment_body`
- `evidence_paths`
- `patch`: unified git diff, or empty
- `commit_message`, `pr_title`, `pr_body`
- `verify_verdict`: `confirmed`, `insufficient_fix`, `inconclusive`, or `not_applicable`
- `existing_fix_url`
- `stop_reason`

Empty strings and an empty `evidence_paths` array when a field does not apply. Leave `patch` empty unless `outcome` is `reproduced`, `mode` is `fix`, and `verify_verdict` is `not_applicable`.

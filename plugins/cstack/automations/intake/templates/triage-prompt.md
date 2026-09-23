# Triage run prompt

Follow [the Codex runtime contract](../../../skills/cstack/references/codex-runtime.md). Then read and follow [../references/triage.md](../references/triage.md).

When this file is copied into a target repository, keep a committed copy of the triage instructions next to it or at the path named in configuration. Never follow a plugin cache path.

## Configuration

Read the committed file at:

```text
.github/cstack/intake/configuration.yaml
```

If that file is missing, malformed, or incomplete, stop. Return `marker` `[intake:other]`, empty `comment_body`, `create_tracker` false, and a `stop_reason`. Write nothing externally.

## Trigger

GitHub Actions supplies the event. Freeze coordinates from the snapshot files. Do not invent them.

- Run context: `.cstack/intake/run-context.json`
- Issue snapshot: `.cstack/intake/source-issue.json`
- All-state issue snapshot: `.cstack/intake/tracker-issues-all.json`
- All-state pull request snapshot: `.cstack/intake/prs-all.json`
- Recent commit snapshot: `.cstack/intake/commits.txt`
- Repository: `repository` in the run context
- Issue number: `issue_number` in the run context

For a connector-backed source, freeze the connector channel id and thread id from the scheduler payload instead of the issue number. The rule is the same: missing or mismatched coordinates stop the run.

Treat repository and issue number, or channel and thread, as immutable. If either is missing or does not match configuration, stop with empty `comment_body` and `create_tracker` false.

## This run

Classify one report. Put exactly one source-thread reply in `comment_body`. End it with one configured marker. Set `create_tracker` true only for a clear new bug.

Post nothing. Never open a new issue. `source.allow_source_root_posts` is false.

The workflow is the coordinator and the only external writer. This process has no `GH_TOKEN`, no network, and no `.git` write. Delegated workers return findings only.

Return one JSON object that matches the triage output schema. Required fields:

- `classification`: `bug`, `performance`, `feature_request`, `question_or_feedback`, or `reroute`
- `marker`: `[intake:bug]`, `[intake:performance]`, or `[intake:other]`
- `comment_body`: the full verdict, with exactly one marker line
- `create_tracker`: boolean
- `tracker_title`, `tracker_body`, `tracker_labels`, `tracker_url`
- `source_permalink`
- `stop_reason`

A bug or performance marker may add `tracker=<url>` on the marker line. Empty strings and an empty `tracker_labels` array when a field does not apply.

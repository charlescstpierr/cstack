# Triage run

Classify one report. Return one JSON object that matches the triage output schema. Do not post, comment, create a ticket, call `gh`, or use the network. The GitHub Actions workflow is the coordinator and the only external writer.

Follow [the Codex runtime contract](../../../skills/cstack/references/codex-runtime.md).

Load the committed configuration. If it is missing, malformed, or incomplete, stop. Return `marker` `[intake:other]`, empty `comment_body`, `create_tracker` false, and a `stop_reason`.

## Hard rules

- Source coordinates are immutable after freeze.
- Never open a new source-repository issue as the verdict. The verdict lives in `comment_body`. The workflow posts it as a comment on the source issue.
- Preflight the source parent from the snapshot files before filling tracker fields or `comment_body`.
- If the parent is missing, deleted, inaccessible, or uncertain, stop with empty `comment_body` and `create_tracker` false.
- Return one substantive verdict in `comment_body`. Do not narrate progress.
- The coordinator is the only external writer. This run is not the coordinator.
- Delegated workers return findings only. They receive no tracker credentials, no `gh` write, and no connector write tools. If isolation cannot enforce that, do the work in this run and still write nothing externally.
- Never invent a tracker URL that was not in the snapshot.
- Prefer no ticket over a guessed or duplicate ticket.
- Keep source coordinates on one owner, per [Separate Before Serializing Shared State](../../../skills/cstack/references/principles/separate-before-serializing-shared-state.md).
- Run the verdict through [unslop](../../../skills/unslop/SKILL.md) and [Minimize Reader Load](../../../skills/cstack/references/principles/minimize-reader-load.md).
- Return the result as the schema-constrained JSON last message. Perform no external write.

## 1. Freeze source coordinates

Before making a work list or delegating:

1. Read `.cstack/intake/run-context.json` and `.cstack/intake/source-issue.json`.
2. Require the repository to equal the configured source.
3. Set `SOURCE_ISSUE_NUMBER` from `issue_number` in the run context.
4. Require a nonempty identifier.
5. Store `SOURCE_REPOSITORY` and `SOURCE_ISSUE_NUMBER` as immutable values.
6. Read the snapshot and verify it still has those coordinates.
7. Copy the snapshot URL into `source_permalink`.

Every later source read must use those stored values. Never replace them with a reply id, a job id, or an operations-thread id.

## 2. Read the whole report

Read the snapshot root and comments before deciding.

Capture reporter wording, version and environment when present, expected behavior, observed behavior, frequency, error text, existing issue or pull request links, and any statement that someone is already fixing it.

Inspect every relevant attachment already present in the snapshot. If an attachment cannot be read, say so in the verdict. Do not invent what it shows. Use evidence already in the thread before asking the reporter for more.

## 3. Trace cause before routing

Do a bounded source and history pass before choosing an owner. Read [how](../../../skills/how/SKILL.md) over the affected path. Read [why](../../../skills/why/SKILL.md) when the report looks like a regression.

1. Identify the likely code path from the reported action to the observed result.
2. Check whether the visible symptom belongs to that path or a dependency below it.
3. Check recent changes when the report looks like a regression.
4. Check whether a merged commit or open pull request already addresses the same symptom.
5. Separate confirmed facts from hypotheses.

This pass does not need a complete root cause. It must be strong enough to avoid routing a visible symptom to the wrong owner. If the repository cannot be read, do not guess a code owner.

## 4. Classify

Choose one category. Set `classification` to the matching enum value.

**Bug.** Something violates intended behavior: wrong output, broken state, an error, a crash, a hang, a silent no-op, or a regression. `classification` `bug`.

**Performance.** Measurable slowness, excess memory, battery drain, jank, or another resource problem. Treat it as a bug, but keep measurements. `classification` `performance`.

**Feature request.** Current behavior appears intentional and the reporter wants a different behavior. `classification` `feature_request`.

**Question or feedback.** How something works, a preference without a concrete defect, or general feedback. `classification` `question_or_feedback`.

**Reroute.** Cause tracing shows that another configured destination owns the issue. `classification` `reroute`.

When the bug versus feature line is unclear, do not file. The one verdict may ask one focused question and use the `other` marker.

## 5. Apply configured routing

Read the optional map at `routing.map_path`. See [routing.example.md](routing.example.md).

- Match on confirmed product area, code path, or error signature.
- A visible symptom alone is not enough when cause tracing points elsewhere.
- If no route matches, say the owner is unclear. Do not guess.
- Do not cross-post. Tell the reporter where to take the issue in `comment_body`.

Owner pings are off by default. A ping is allowed only when the map names the owner, the config allows that ping type, and the item is a feature request that needs owner input or a likely regression author with strong evidence. No other case gets a ping.

## 6. Use the issue-tracker adapter

The tracker is an adapter, not a required vendor. On this host the workflow writes GitHub Issues through `gh`. A Linear adapter or another tracker may implement the same operations through an MCP server named in `connectors.tracker`, but this run still must not call it.

Required operations, fulfilled by the workflow snapshot and later `run:` steps:

- Search issues by text, state, label, source URL, and date range
- Read one issue and its links
- Create or label an issue with title, body, status, labels, and source URL
- Update an existing issue without replacing unrelated fields
- Add a source link and recurrence note
- Cancel, close, or delete an issue created by this run if the source-thread handoff fails

If a required operation is unavailable, fail closed for that write: `create_tracker` false.

Resolve configured team, project, status, and labels at runtime. Do not invent IDs, create labels, assign owners, or set priority unless the config explicitly requires it.

When `connectors.tracker.mcp_server` is empty and `tracker.type` is `github_issues`, fill tracker fields for the workflow. Do not invent a second client. Do not run `gh`.

## 7. Dedupe

Always check whether this source permalink is already linked to a tracker issue or a prior triage reply. Read `.cstack/intake/tracker-open.json`. If so, do not ask the workflow to post or create a duplicate: empty `comment_body`, `create_tracker` false, `stop_reason` naming the duplicate.

For bugs and performance reports, search using exact error signature, product area, trigger, symptom, version or date window, suspected regression commit, and source permalink.

Choose one outcome: confident duplicate, possibly related, weak resemblance, or no match.

For a confident duplicate, set `create_tracker` false, put the existing URL in `tracker_url`, and write one short recurrence note in `comment_body`. Do not ask to reopen, relabel, or reassign unless the config says to. For a possible match, link it in the verdict as uncertain and set `create_tracker` false. A long-closed issue is a regression lead, not automatically a live duplicate.

## 8. Decide whether to create

Set `create_tracker` true only when all of these are true:

1. The classification is bug or performance.
2. The behavior is clearly broken.
3. The issue is still live or not known to be fixed.
4. Dedupe found no confident or plausible live match.
5. The source parent and permalink passed preflight.
6. The tracker target fields resolved.
7. The adapter can compensate if the verdict post fails.

Never set `create_tracker` true for a feature request, question, feedback item, reroute, possible duplicate, confident duplicate, or already-fixed issue.

Fill `tracker_title`, `tracker_body`, and `tracker_labels` when `create_tracker` is true. The new body must be self-contained: plain title that names the area and symptom, reporter quote, expected and observed behavior, version and environment or `unknown`, trigger and frequency, source permalink, short cause-tracing findings with hypotheses labeled as hypotheses. Do not put a guessed root cause in the title.

On GitHub-as-source, creating a second issue is optional. Prefer labeling and summarizing on the source issue when `tracker.type` is `github_issues` and the source issue is the ticket. Fill labels for the source issue. Leave a separate tracker issue to a configured non-GitHub tracker. This workflow only writes GitHub through `gh`.

## 9. Return one verdict

`comment_body` is the single source-thread reply. The workflow posts it on `SOURCE_ISSUE_NUMBER`. Never ask it to open a new issue for the verdict.

Keep the reply short. Lead with the outcome. Link the existing or new tracker issue when there is one. Mention a reroute or one missing fact when needed. End with exactly one marker line.

Marker contract. Set `marker` to one of these tokens. Put exactly one of these forms in `comment_body`:

```text
[intake:bug]
[intake:bug] tracker=https://github.com/example-org/example-repo/issues/123
[intake:performance]
[intake:performance] tracker=https://github.com/example-org/example-repo/issues/123
[intake:other]
```

Use only the configured marker strings. The reproduce job trusts the `marker` job output from this run, not a later comment event.

If `comment_body` is nonempty it must contain exactly one configured marker, and that marker must match the `marker` field.

If this run would have created a tracker issue and the verdict cannot be formed, set `create_tracker` false and name the failure in `stop_reason`.

## 10. Follow-up

`codex exec` is one turn. It does not watch the thread after it exits. A later comment is a new GitHub event. This workflow does not start from `issue_comment`, because `GITHUB_TOKEN` comments do not retrigger workflows. A maintainer may use `workflow_dispatch`. If neither fires, there is no follow-up.

## Structured result

Return one JSON object. Required fields: `classification`, `marker`, `comment_body`, `create_tracker`, `tracker_title`, `tracker_body`, `tracker_labels`, `tracker_url`, `source_permalink`, `stop_reason`.

Empty strings and an empty `tracker_labels` array are required when a field does not apply. Do not omit required fields.

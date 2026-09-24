# Reproduce and fix run

This run starts only when the triage job output marker is `[intake:bug]` or `[intake:performance]`. Reproduce the exact symptom through the target app's real UI. Verify an existing fix when one exists. Attempt a bounded fix only after a confirmed repro.

Return one JSON object that matches the reproduce output schema. Do not post, comment, commit, push, open a pull request, call `gh`, or use the network. The GitHub Actions workflow is the coordinator and the only external writer.

Follow [the Codex runtime contract](../../../skills/cstack/references/codex-runtime.md).

Load the committed configuration. If the config, control adapter, or completed feature map is missing, fail closed: `outcome` `blocked`, empty `patch`, empty `source_comment_body`.

## Hard rules

- Freeze the source coordinates before doing any work.
- Never open a new source-repository issue as status.
- The coordinator is the only external writer. This run is not the coordinator.
- Delegated analysis workers are read-only and return findings.
- A fix-phase code worker may edit only inside this sandbox. The read-only sandbox cannot write `.git`. Put a unified git diff in `patch`. The workflow applies it.
- The exact discriminating symptom must appear twice through real UI interaction.
- State inspection may confirm an observation. It must not inject or force the symptom.
- No confirmed repro means no authored fix. Leave `patch` empty.
- Existing pull requests or commits switch the run to verify mode. Do not author over them.
- Use `github.com` pull request links in the form `https://github.com/{owner}/{repo}/pull/{number}`.
- Keep captures, recordings, logs, and tokens out of source control.
- Bound delegated analysis with [Guard the Context Window](../../../skills/cstack/references/principles/guard-the-context-window.md).
- Sequence repro, fix, and verification through [Sequence work into verifiable units](../../../skills/cstack/references/principles/sequence-verifiable-units.md), [Fix Root Causes](../../../skills/cstack/references/principles/fix-root-causes.md), and [Prove It Works](../../../skills/cstack/references/principles/prove-it-works.md).
- Return the result as the schema-constrained JSON last message. Perform no external write.

## 1. Freeze source coordinates

1. Read `.cstack/intake/run-context.json` and `.cstack/intake/source-issue.json`.
2. Require the repository to equal the configured source.
3. Set `SOURCE_ISSUE_NUMBER` from `issue_number` in the run context.
4. Require a nonempty identifier.
5. Store the pair as immutable.
6. Read the snapshot and verify those exact coordinates.
7. Fetch the source permalink from the snapshot.

Never replace these values with a reply id, a job id, or an operations timestamp.

## 2. Marker gate

On GitHub, this run starts because `needs: triage` passed a bug or performance marker. Read that marker from `.cstack/intake/run-context.json`. Do not poll. Do not wait for a later comment.

Accept the verdict only when:

- `run-context.json` `marker` is `[intake:bug]` or `[intake:performance]`.
- The snapshot is the issue for `SOURCE_ISSUE_NUMBER`.
- The thread contains exactly one configured marker from `source.triage_identity`, or the job output marker is the gate and the snapshot comment matches it.

Public marker forms:

```text
[intake:bug]
[intake:bug] tracker=https://github.com/example-org/example-repo/issues/123
[intake:performance]
[intake:performance] tracker=https://github.com/example-org/example-repo/issues/123
[intake:other]
```

Proceed only for `bug` or `performance`. Capture the optional tracker URL. Stop with no `patch` and empty `source_comment_body` for `other`, a missing verdict, conflicting markers, or a run that started without a marker.

A local scheduler that starts this prompt before a marker exists fail-closes. Codex CLI has no inbound Slack wait.

## 3. Ownership and fix-artifact gates

Re-read the snapshot immediately before starting work.

Stop when a person clearly claims the fix, gives a concrete implementation plan, or asks another agent to implement, patch, fix, or open a pull request. A bot summary, a log lookup, or a diagnosis request is not fix ownership.

If an open pull request or merged commit plausibly fixes this report, switch to [verify-existing-fix.md](verify-existing-fix.md). A claim without a commit or pull request is not a fix artifact. If a person owns the work but has not produced an artifact, stop. Do not race them.

Use `.cstack/intake/prs-all.json` and `.cstack/intake/commits.txt` for the first fix-artifact pass. Treat those files as snapshots from before the no-network Codex run. If they are missing, fail closed instead of assuming that no fix exists.

## 4. Optional operations status

If `source.connector.operations_channel_id` is set, do not post there. Put the status string in `status_label`. The workflow is the only writer.

On GitHub with no operations channel, keep status in `status_label` and in `source_comment_body` only after a confirmed repro. Use the configured `status_labels` strings.

## 5. Load the control adapter

Read [control-adapter.md](control-adapter.md) and the completed map at `control.feature_map_path`. Invoke the adapter named by `control.adapter_name` through the session tools or the MCP server in `connectors.control`.

Find the feature-map section that matches the reported user path. Read it before driving the app. If no section covers the feature, mark the run blocked instead of inventing a path or selector.

Require all seven capabilities in [control-adapter.md](control-adapter.md). If the adapter is absent or any required capability is missing, mark blocked and stop. Do not pretend a screenshot, unit test, state mutation, or source reading is a UI repro.

The read-only sandbox has no network. An adapter that needs the network is a block. Record that in `stop_reason` and `outcome` `blocked`.

## 6. Study the report

Read the full source snapshot and tracker fields when present. Collect the exact action path, expected and observed behavior, discriminating state, frequency, version, attachments, and candidate code area.

Inspect screenshots and video. Use read-only workers for code history, test ideas, blast-radius mapping, and media review when useful. Each worker gets a narrow question and an explicit ban on external writes.

Read [how](../../../skills/how/SKILL.md) to trace the action through the repository. Read [why](../../../skills/why/SKILL.md) for regression history. Form competing cause hypotheses and name evidence that would separate them.

## 7. Reproduce

Bring up the target app through the control adapter. Confirm the correct app, workspace, account, data set, and feature state before acting. Use stable app markers.

Drive the reported path through real UI actions.

Before calling it reproduced:

1. Name the correct final state.
2. Name the broken final state.
3. Reach the point where they diverge.
4. Observe the broken state.
5. Reset enough state to make the second attempt independent.
6. Repeat the same path and observe the same broken state again.
7. Cross-check a real state value when possible.

An expected dialog, loading state, or setup step is not the bug. Use `budgets.repro_minutes`. If the symptom does not reproduce, report `could_not_reproduce`. If a required capability is missing, report `blocked`.

## 8. Capture evidence

For a successful repro: record the full path, capture a screenshot of the broken final state, save a short note with the exact steps, and keep artifacts in `control.artifact_directory`. Put those paths in `evidence_paths` so the workflow can upload them before runner teardown.

Have a read-only media reviewer answer one question: does the evidence visibly show the discriminating broken state? If the answer is no or uncertain, the repro is not confirmed.

## 9. Report the repro outcome

Put the operations status in `status_label`.

For `could_not_reproduce` or `blocked`, leave `source_comment_body` empty.

For a confirmed repro, put at most one unprompted source reply in `source_comment_body`: the issue reproduced, a link to evidence, at most three short findings, and the tracker issue when one exists. Do not ping an owner by default. The workflow posts it.

The Cursor pack then waited `budgets.rejection_window_minutes` while the automation stayed alive. `codex exec` exits at the end of the turn, so this run cannot wait. Re-read the snapshot now. If a person already claims the fix, stop. If nobody does, continue to the fix gates in this same turn. `budgets.rejection_window_minutes` is unused on GitHub Actions.

## 10. Verify an existing fix

When a fix artifact exists, follow [verify-existing-fix.md](verify-existing-fix.md). Verification must show the symptom on the baseline and its absence on the patched build. Both paths use the real UI twice. Do not edit the existing fix or fill `patch`. Set `mode` `verify` and `verify_verdict` to `confirmed`, `insufficient_fix`, or `inconclusive`.

## 11. Qualify a bounded fix

Attempt a fix only when all of these hold:

- The outcome is a plain confirmed repro.
- Media review confirmed the broken final state.
- No existing fix artifact appeared.
- No person claimed the fix on the source thread at the start of the fix phase.
- Runtime evidence identifies the root cause.
- The likely change fits `budgets.fix_minutes` and repository scope.
- The control adapter can run both baseline and patched builds.

If any condition fails, keep the repro report and leave `patch` empty.

## 12. Root-cause and implement

The workflow owns every external post, the commit, the branch push, and the pull request.

Confirm the mechanism with runtime evidence. Eliminate competing hypotheses before editing. Fix the root cause with the smallest justified change.

Apply [tdd](../../../skills/tdd/SKILL.md) before changing production behavior: record the expected failing test before the fix and its passing run afterward. A genuinely impractical test-first path requires a documented exception and an executed alternative check. Block delivery without either evidence path. Keep unrelated cleanup out. Stop if the change grows beyond the configured effort.

Put the unified git diff in `patch`. Set `commit_message`. Leave `mode` `fix`. Set `verify_verdict` `not_applicable`.

## 13. Prove the fix

Keep the original baseline evidence. On the patched build: run the same real UI path, repeat it twice, show that the broken state is gone, show the expected state in its place, capture an after recording and screenshot, and cross-check the same real state value. A compile, unit test, code review, or plausible diff is not after evidence.

Run focused tests, then smoke the blast radius around the changed behavior. Stop without a patch if a regression remains.

## 14. Draft pull request fields

Only after before-and-after proof:

- Review the final diff for unrelated changes and secrets.
- Fill `pr_title` and `pr_body`.
- The workflow opens a draft pull request. `repository.draft_only` is true. Never merge or deploy.
- Link the configured tracker issue in `pr_body`.
- Use `repository.pull_request_url_format` only as a format string. Do not invent a pull request number.
- Include the repro steps, root cause, test result, before and after evidence, and blast-radius checks.
- Run pull request text through [unslop](../../../skills/unslop/SKILL.md).

If the proof is incomplete, leave `patch` empty and set `status_label` to `Fix did not land`.

On success, set `status_label` to `Draft pull request opened`. Do not ask for a second source-issue or an extra source reply.

Read [Opening a PR](../../../skills/cstack/playbooks/opening-a-pr.md) for the PR shape. This workflow still forbids merge.

## 15. Cleanup

Always call the control adapter's cleanup capability. Keep artifacts only as long as `control.artifact_retention_hours` allows. Do not delete user work.

`codex exec` does not stay resident for `budgets.operations_follow_up_minutes`. A later question is a new event.

## Structured result

Return one JSON object. Required fields: `outcome`, `mode`, `status_label`, `source_comment_body`, `evidence_paths`, `patch`, `commit_message`, `pr_title`, `pr_body`, `verify_verdict`, `existing_fix_url`, `stop_reason`.

Empty strings and an empty `evidence_paths` array are required when a field does not apply. Do not omit required fields.

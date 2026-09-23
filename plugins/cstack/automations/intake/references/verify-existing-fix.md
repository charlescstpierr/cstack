# Verify an existing fix

Use this mode when an open pull request or merged commit plausibly fixes the report.

The existing artifact owns the fix. Verify it. Do not edit it, fill `patch`, or ask the workflow to open another pull request. Return the verify verdict in the reproduce schema. Perform no external write.

Follow [the Codex runtime contract](../../../skills/cstack/references/codex-runtime.md).

## Qualify the artifact

Require one concrete artifact:

- An open pull request with code changes that address the symptom
- A merged pull request
- A merged commit with matching code and intent

A thread claim, tracker status, branch name, or cause hypothesis without a pull request or commit is not enough.

When several artifacts exist, choose the one linked from the source thread or tracker. Otherwise choose the closest match to the affected code and state why.

## Protect the working tree

Use an isolated checkout. `codex exec --worktree` is the measured flag for an experimental isolated checkout. It conflicts with `--ephemeral`, `--ignore-user-config`, resume, and review. This Actions run uses the read-only sandbox, so the model cannot create a worktree or write `.git`. Record baseline and patched revisions from git history and from the existing artifact. Do not overwrite user changes.

Record:

- Baseline revision
- Patched revision
- Pull request or commit URL
- Build and environment inputs shared by both runs

Use regular `github.com` pull request links.

## Measure the baseline

For an open pull request, use its base branch as the baseline.

For a merged fix, use the revision immediately before the fix when that revision builds and represents the old behavior.

Through the configured control adapter:

1. Bring up the baseline app.
2. Confirm the correct app and environment.
3. Run the reported path through real UI actions.
4. Observe the discriminating symptom.
5. Reset and repeat it.
6. Capture baseline recording, screenshot, and state check.

If the symptom does not appear twice on the baseline, there is no baseline. Do not claim that the fix works.

## Measure the patched build

Build and run the pull request or fix commit with the same environment and data.

1. Run the same UI path.
2. Repeat it twice.
3. Confirm that the broken state is gone.
4. Confirm the expected state appears.
5. Capture after recording, screenshot, and the same state check.

Do not stop at compilation or tests. The after result must come from a running patched app.

## Outcomes

### Confirmed

The baseline reproduces twice and the patched build resolves it twice. Set `outcome` `verified_existing_fix`, `mode` `verify`, `verify_verdict` `confirmed`, and `status_label` to verified. Put the artifact URL in `existing_fix_url`. Put one concise source-thread reply in `source_comment_body`. Include the before and after result. Leave `patch` empty.

### Insufficient fix

The symptom appears on both baseline and patched builds. Set `outcome` `insufficient_fix`, `mode` `verify`, and `verify_verdict` `insufficient_fix`. Link the artifact in `existing_fix_url` and say it did not resolve the symptom. Put the normal confirmed-repro source update in `source_comment_body` if that field is still empty. Leave `patch` empty.

### Inconclusive

The baseline does not reproduce, the patched app cannot run, or the evidence does not show the discriminating state. Do not claim success. Set `outcome` `inconclusive`, `mode` `verify`, and `verify_verdict` `inconclusive`. State which half could not be measured in `stop_reason`. Leave `source_comment_body` empty unless a direct question in the snapshot requires an answer.

## Cleanup

Stop both builds, remove temporary profiles and captures according to retention policy, and return the repository to its prior state without discarding user work.

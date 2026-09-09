### Worktree and simulator cleanup

Follow [the Codex runtime contract](../references/codex-runtime.md).

**You own the disk and the safety gate.** Prune merged or abandoned git worktrees and stale iOS simulators to reclaim space. Deletion is irreversible, so every step guards against deleting something in use or holding uncommitted work.

1. Snapshot and audit. Record `df -h /`, then resolve the plugin root and run `bash <plugin-root>/scripts/run-tool.sh worktree-audit.sh`. The helper reads paths from `git worktree list` and classifies each worktree by size, age, merge state, uncommitted work, and PR state. It stages its locked sources under the workspace `.cstack/` directory.
2. The bucket is advice, not permission. Cross-check candidates against active native tasks when the session exposes task inspection. If active-task state is unavailable, keep uncertain worktrees.
3. Verify usage before deleting. A worktree used by an active task or subagent remains in use even when its name is absent from the sidebar. Use a bounded subagent to inspect a large available task trail when capacity permits. Never search unrelated conversations.
4. Pause on irreversible loss. `wip:N` means N tracked uncommitted edits. Show the diff and get a decision because removal loses those edits. `scratch:N` means N untracked files. Name them and require deletion authority. Delete clean, merged, unused worktrees only when the user's request authorizes cleanup.
5. Prune the confirmed set. Per path, `git worktree remove --force <path>`. If the dir survives on ignored build artifacts, `rm -rf` it, then `git worktree prune`. Branch refs survive, so no commits are lost. Confirm with `df -h /` and re-list.
6. Inspect simulators and caches only when they exist on this machine. Candidate simulator commands include `xcrun simctl --set testing delete all`, `xcrun simctl delete unavailable`, and `xcrun simctl runtime list`. Other candidates include Xcode `DerivedData`, `iOS DeviceSupport`, and package caches. Confirm exact targets and authority before deletion.

This is the one playbook that deletes user state with no code review to catch a slip, so the gates above are the review.

**Reply:** `df -h /` before and after with space reclaimed, the worktrees pruned, and a one-line reason for each held back (in-use by which chat, or uncommitted work).

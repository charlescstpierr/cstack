### Autopilot-stack

Follow [the Codex runtime contract](../references/codex-runtime.md).

**You own the stack and its verification. The operator owns landing.** Build the queue as one linear base-branch chain and stop at a verified handoff.

1. **Run one owner per change.** Use git and `gh`. Each bounded owner builds its change, pushes an early snapshot, opens an authorized ready PR before final proof, proves the real behavior, triages automated review through `../references/bugbot-triage.md`, applies the bundled prose and comment checks, and drives the PR green with `babysit.md`. Keep its `decisions.tsv` trail under `.cstack/`. Do not create or publish PRs unless the request grants that authority.
2. **Audit in the foreground.** Re-read this playbook, the recorded objective, owner state, PR heads, checks, and trails at useful boundaries. Count only observable side effects as progress. Replace a stalled owner only after inspecting its state. Use a native scheduler only when available and requested.
3. **Hold operator gates.** If the request asks only for a protocol or plan, return it and stop. If the request authorizes execution, continue without asking again. On an explicit stop, interrupt every owner and preserve `.cstack/` state.
4. **Verify each stack-ready head.** Pin the owner's report to the exact SHA. Run repository gates, live behavior checks, a trunk comparison, and a receipts-and-diff audit with independent native agents when capacity permits. Run lanes in waves. Findings return to the owner. Nothing enters the delivered stack without a clean verdict.
5. **Append; do not ship.** Owners never merge, arm auto-merge, or close PRs. A clean verdict permits the topology owner to append that PR to the linear stack in verified or operator-specified order.
6. **Use one topology writer.** Owners push only their branches and report the tip, base, and intended parent. The root is the only topology writer. Before a rebase or force-with-lease push, verify the remote branch tip with `git ls-remote`. Rebase the child onto the exact parent tip, push with `--force-with-lease`, and set its base with `gh pr edit <pr> --base <parent-branch>`. Only the root PR targets trunk.
7. **Absorb trunk drift from bottom to top.** Fetch current trunk and rebase the chain in order. The owner fixes conflicts in its files. Every rewrite changes descendant SHAs. Compare each PR's stable base-to-head `git patch-id` with the patch ID recorded at verdict time. Preserve the code verdict only when the patch ID is unchanged, then re-run mergeability and CI. Re-verify every changed patch.
8. **Deliver the chain.** Return one linear chain of verified PRs, reviewable bottom-up on GitHub. Keep verdicts in `.cstack/` unless the user authorized posting them. The operator reviews and lands the chain.

Use Autopilot-full for independent PRs with explicit landing authority. Use Autopilot-stack for coupled work, sequenced work, or retained landing authority.

**Reply:** Link the stack root and tip, give one verdict line per PR, and name excluded or parked work with its reason.

### Session pickup

Follow [the Codex runtime contract](../references/codex-runtime.md).

**You own the resume point. Read the prior trail, don't redo it.**

1. Locate the prior trail in the active task, `.cstack/`, or a pushed branch. Use a native task transcript only when the current session exposes it. Read the summary and latest messages first, then scan for decision points. Never search unrelated tasks or private workspace history. Use a bounded subagent to reduce a long available transcript when capacity permits.
2. Reconstruct operational state. The branch and worktree, what already landed (`git log`, `git diff` against the base), the open todos, the decisions made. The prior trail is authoritative input. Resist the bias to re-derive it.
3. Compare done work with the plan and name the resume point. Do not repeat completed implementation or expensive checks without evidence that the prior result is stale. Verify cheap drift-prone facts before relying on them.
4. Route the remaining work to the matching playbook and pick the verdict: continue the execution, ship a finished recommendation, ratify or override a prior conclusion, or postmortem a failed run. The pickup playbook ends here. The routed playbook owns the rest.
5. Verify the inherited claims against the original goal on the real artifact (the **principle-prove-it-works** skill). A passing prior self-report is not the proof.

**Reply:** where the prior agent stopped, what you inherited vs redid (ideally nothing redone), the resume point, and the outcome.

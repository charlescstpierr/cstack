### Pause safely

Follow [the Codex runtime contract](../references/codex-runtime.md).

**You own a clean stop. Leave a checkpoint a cold-start agent can resume from.** This is explicit only. On "keep going", "going to bed, keep going", or "don't stop", do not pause.

1. Stop at a safe boundary. Finish the current atomic step or back out of it. Never stop mid-edit in a known-broken state. Start nothing new, and cancel any nested subagents.
2. Take no irreversible action to pause. No PR and no push unless you already had one out.
3. Make the work durable. Stage only this task's paths and commit them as one clear `wip:` commit on the current branch so nothing is lost. Leave unrelated changes uncommitted and list them. If the tree is broken, say so in the commit body in one line.
4. Write the resume note under `.cstack/resume/<slug>.md`. Capture intent, progress, verified results, current state, next steps, key files, and hazards. If a show-me-your-work trail exists, link it instead of duplicating it.

**Reply:** where you are in the loop, what's on disk versus still in your head (paths, no diff dumps), the commits you made and whether the tree is clean, and the first action on resume. This is a pause, not a final report. Every claim carries its evidence or its label in the same sentence. Measured, inferred, or guess. A prediction or an unseen cause is a guess. Never hand the human a check you could run.

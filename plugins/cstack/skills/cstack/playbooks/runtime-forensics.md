### Runtime forensics

Follow [the Codex runtime contract](../references/codex-runtime.md).

**You own the diagnosis. Instrument the live process, don't theorize from source.** The deliverable is a cited diagnosis, not a fix.

1. Capture the live signal with an available native browser, simulator, profiler, or terminal tool. Use a CPU profile for a spinning process, a heap snapshot for a leak, or a browser trace for a visual glitch. Capture a real artifact.
2. Reduce the artifact to the smoking gun: the function on the hot path, the retainer chain from the leaked object to a GC root, the loop firing without input. Parse large artifacts in a subagent (the **guard-the-context-window** principle skill), keep the reduced finding in the main thread.
3. Prove the mechanism. Use available runtime evaluation or temporary instrumentation to confirm the hypothesis with the smallest reversible change.
4. Map the finding back to source: file, symbol, the line that allocates or schedules.
5. Throughput checkpoint stays one line: `throughput checkpoint: n/a, read-only forensics`.

**Reply:** the signal captured, the reduced finding, how you proved the mechanism, the source location, artifact paths. No fix unless asked. Hand back to Bug fix or Perf once the cause is known.

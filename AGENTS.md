# cstack development

cstack is a standalone Codex App and CLI plugin. Use Codex native tools and subagents. Do not add a separate orchestration runtime or hard-code model names for execution. Optional setup recommendations may name models only when validated against the live model and reasoning-effort catalog before selection.

Preserve the upstream MIT license and record provenance. Skills are explicitly invoked; installing the plugin must not activate its instructions in unrelated tasks. Respect the user's scope, project instructions, Codex Plan mode, and permissions.

Keep the port small. Reuse upstream helpers and their locked dependencies. Run the repository validator and the Bun tests and typecheck before claiming completion. Never modify a user's installed plugin cache, global instructions, or model configuration as a side effect of setup.

Repository map: `plugins/cstack/` is the distributable; `scripts/` and `tests/` validate packaging and native behavior; `UPSTREAM.json` and `PORTING.json` track source provenance. Work artifacts belong in ignored `.cstack/` directories. Native trials are separate from deterministic checks and must report actual task outcomes and capability gaps.

Python 3.9 or newer runs the helpers and the whole test suite. Parsing the Codex `config.toml` inside `scripts/verify-behavior.py` needs Python 3.11 or newer.

Run checks from this repository root, in this order. Install helper dependencies before any `tsc`. Return to the repository root before the root `tsc` invocation. These commands match `.github/workflows/validate.yml`.

```sh
bun scripts/validate.ts
python3 -m unittest discover -s tests -p 'test_*.py'
bun test tests
cd plugins/cstack/skills/cstack/scripts
bun install --frozen-lockfile
bun run test
bun run typecheck
cd ../../../../..
plugins/cstack/skills/cstack/scripts/node_modules/.bin/tsc -p tsconfig.json
bash -n plugins/cstack/scripts/run-tool.sh plugins/cstack/skills/cstack/scripts/worktree-audit.sh plugins/cstack/skills/show-me-your-work/scripts/log.sh
git diff --check
```

`bun run typecheck` is the watch-pr strict check. The `tsc -p tsconfig.json` line typechecks the repository `tsconfig.json` with the `tsc` binary that `bun install` just created, after `cd` back to the repository root. Python tests use the standard-library `unittest` runner. Completion requires the relevant observed behavior as well as green checks; fewer calls alone do not establish better results.

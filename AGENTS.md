# cstack development

cstack is a standalone Codex App and CLI plugin. Use Codex native tools and subagents. Do not add a separate orchestration runtime or hard-code model names for execution. Optional setup recommendations may name models only when validated against the live model and reasoning-effort catalog before selection.

Preserve the upstream MIT license and record provenance. Skills are explicitly invoked; installing the plugin must not activate its instructions in unrelated tasks. Respect the user's scope, project instructions, Codex Plan mode, and permissions.

Keep the port small. Reuse upstream helpers and their locked dependencies. Run the repository validator and the Bun tests and typecheck before claiming completion. Never modify a user's installed plugin cache, global instructions, or model configuration as a side effect of setup.

Repository map: `plugins/cstack/` is the distributable; `scripts/` and `tests/` validate packaging and native behavior; `UPSTREAM.json` and `PORTING.json` track source provenance. Work artifacts belong in ignored `.cstack/` directories. Native trials are separate from deterministic checks and must report actual task outcomes and capability gaps.

Run checks from this repository root:

```sh
bun scripts/validate.ts
python3 -m unittest discover -s tests -p 'test_*.py'
bun test
plugins/cstack/skills/cstack/scripts/node_modules/.bin/tsc -p tsconfig.json
plugins/cstack/skills/cstack/scripts/node_modules/.bin/tsc -p plugins/cstack/skills/cstack/scripts/watch-pr/tsconfig.json --noEmit --strict
```

If helper dependencies are absent, run `bun install --frozen-lockfile` in `plugins/cstack/skills/cstack/scripts/`. Python tests use the standard-library `unittest` runner. Completion requires the relevant observed behavior as well as green checks; fewer calls alone do not establish better results.

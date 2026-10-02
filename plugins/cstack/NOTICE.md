# Provenance

cstack is an independent Codex adaptation of pstack by Lauren Tan.

- Source: https://github.com/cursor/plugins/tree/889ec4b68fa5aab0e867dad71ec3fdf386ae48f3/pstack
- Upstream commit: `889ec4b68fa5aab0e867dad71ec3fdf386ae48f3`
- Upstream manifest version: `0.15.2`
- Original copyright: Copyright (c) 2026 Lauren Tan
- License: MIT. The original license is preserved in LICENSE.
- cstack plugin version: `0.7.0`
- Catalog: 29 skills, 23 principle references, 23 playbooks, two agent prompts

The adaptation replaces Cursor-specific execution instructions, model routing and plugin packaging with native Codex workflows. Modified files retain the original license. cstack is not an official Cursor or OpenAI product.

The source snapshot is recorded in the repository's UPSTREAM.json. docs/PORTING.md accounts for the skills, playbooks, agent prompts and unsupported integrations. Source attribution links are intentionally retained; they are not runtime dependencies.

`deslop` is original to cstack. It is not a port. pstack shipped `/deslop` in the separate `cursor-team-kit` plugin and had no portable source.

## Matt Pocock adaptations

Optional clarification, domain documentation, Horizon, architecture audit, project setup and selected review/authoring methods adapt Matt Pocock's skills, version 1.2.3, commit `3cca18b368ae95cdbdebbff572ccafa662551015`. Copyright (c) 2026 Matt Pocock. The MIT text is preserved in [LICENSE-MATT-POCOCK](LICENSE-MATT-POCOCK); [the adaptation inventory](sources/matt-pocock.json) records the source paths and hashes.

The native cstack port changes invocation names, tool calls and local state paths. Horizon retains decision-planning and human-input boundaries. The project setup uses managed document blocks and existing Codex model roles. Review axes reuse the selected cstack panel rather than adding another panel. No Matt plugin or setup is required at runtime.

[Original pinned source](https://github.com/mattpocock/skills/tree/3cca18b368ae95cdbdebbff572ccafa662551015).

## pstack-claude delivery adaptations

The landing records, pending-merge cancellation helper, related tests and merge-safety guidance adapt [michael-denyer/pstack-claude at 47fbcd46bbd10fbfd9e7af90714431e6d4c3788b](https://github.com/michael-denyer/pstack-claude/tree/47fbcd46bbd10fbfd9e7af90714431e6d4c3788b). That port and its additions are MIT-licensed, with Copyright (c) 2026 Lauren Tan preserved in [LICENSE](LICENSE). The [adaptation inventory](sources/pstack-claude.json) records source hashes; later watch-pr and decision-log fixes cite their own pstack-claude commit (`7b08003`, `65ea93c`, `9f6ddf7`) next to each hash. These additions do not change the primary pstack pin in UPSTREAM.json.

The repository maintenance synchronizer adapts the three-way comparison approach from the [upstream synchronizer](https://github.com/michael-denyer/pstack-claude/blob/47fbcd46bbd10fbfd9e7af90714431e6d4c3788b/tools/sync.mjs) at the same pstack-claude revision. Its source hash and the local Git regression tests are recorded in the repository-level `MAINTENANCE-SOURCES.json`; these developer tools are not part of the installed plugin.

## Review and selection methods

Arena's per-candidate verification before judging, anonymized candidates and reversed-order second judgment follow the test-then-select approach of CodeMonkeys ([arXiv 2501.14723](https://arxiv.org/abs/2501.14723)) and the anonymized ranking of [karpathy/llm-council](https://github.com/karpathy/llm-council). Interrogate's diff-reachable edge-case lens, partially handled set check, deletion check, verification-gap question and enumerate-then-prove method follow review lenses described in the [BMAD-METHOD changelog](https://github.com/bmad-code-org/BMAD-METHOD/blob/main/CHANGELOG.md) (MIT). The wording is written for cstack; no source text is copied, and no BMAD name or trademark is used.

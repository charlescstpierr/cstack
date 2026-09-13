# Provenance

cstack is an independent Codex adaptation of pstack by Lauren Tan.

- Source: https://github.com/cursor/plugins/tree/889ec4b68fa5aab0e867dad71ec3fdf386ae48f3/pstack
- Upstream commit: `889ec4b68fa5aab0e867dad71ec3fdf386ae48f3`
- Upstream manifest version: `0.15.2`
- Original copyright: Copyright (c) 2026 Lauren Tan
- License: MIT. The original license is preserved in LICENSE.
- cstack plugin version: `0.4.2`
- Catalog: 29 skills, 23 principle references, 23 playbooks, two agent prompts

The adaptation replaces Cursor-specific execution instructions, model routing and plugin packaging with native Codex workflows. Modified files retain the original license. cstack is not an official Cursor or OpenAI product.

The source snapshot is recorded in the repository's UPSTREAM.json. docs/PORTING.md accounts for the skills, playbooks, agent prompts and unsupported integrations. Source attribution links are intentionally retained; they are not runtime dependencies.

`deslop` is original to cstack. It is not a port. pstack shipped `/deslop` in the separate `cursor-team-kit` plugin and had no portable source.

## Matt Pocock adaptations

Optional clarification, domain documentation, Horizon, architecture audit, project setup and selected review/authoring methods adapt Matt Pocock's skills, version 1.2.3, commit `3cca18b368ae95cdbdebbff572ccafa662551015`. Copyright (c) 2026 Matt Pocock. The MIT text is preserved in [LICENSE-MATT-POCOCK](LICENSE-MATT-POCOCK); [the adaptation inventory](sources/matt-pocock.json) records the source paths and hashes.

The native cstack port changes invocation names, tool calls and local state paths. Horizon retains decision-planning and human-input boundaries. The project setup uses managed document blocks and existing Codex model roles. Review axes reuse the selected cstack panel rather than adding another panel. No Matt plugin or setup is required at runtime.

[Original pinned source](https://github.com/mattpocock/skills/tree/3cca18b368ae95cdbdebbff572ccafa662551015).

# Provenance

cstack is an independent Codex adaptation of pstack by Lauren Tan.

- Source: https://github.com/cursor/plugins/tree/12d587dfb20741cafc376c42c696c5f6e2a64487/pstack
- Upstream commit: `12d587dfb20741cafc376c42c696c5f6e2a64487`
- Upstream manifest version: `0.15.5`
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

Arena's per-candidate verification before judging, anonymized candidates and reversed-order second judgment follow the test-then-select approach of CodeMonkeys ([arXiv 2501.14723v1](https://arxiv.org/abs/2501.14723v1)) and the anonymized peer ranking described in [karpathy/llm-council at `92e1fccb1bdcf1bab7221aa9ed90f9dc72529131`](https://github.com/karpathy/llm-council/blob/92e1fccb1bdcf1bab7221aa9ed90f9dc72529131/README.md) (README sha256 `0f21b96fd783f74ed1599a7a831d75d9718a4876b42da5db2d931cb1442f4245`). That repository publishes no license, so only the idea is used.

Interrogate's diff-reachable edge-case lens, partially handled set check, deletion check, verification-gap question and enumerate-then-prove method follow review lenses described in [BMAD-METHOD's CHANGELOG at `1cbcfa272fe65787c06a1fa164a901f46117cca7`](https://github.com/bmad-code-org/BMAD-METHOD/blob/1cbcfa272fe65787c06a1fa164a901f46117cca7/CHANGELOG.md) (sha256 `848bf507adb48abcb82a3a9326b31aed5c345a37ab3551611e160d1a2bc28ed2`; entries #2524, #2525, #2535, #2646 and #2675; MIT, Copyright (c) 2025 BMad Code, LLC). The wording is written for cstack; no source text is copied, and no BMAD name or trademark is used.

## Verification methods

The pass / fail (including inconclusive) / blocked drive verdicts with blocker codes, the fresh read-only observation that judges the final state, secrets passed by name, helper promotion after a verified assertion, and the bug-bash protocol in `skills/maintain-verification-skill/references/bug-bash.md` follow methods published by [tester-army/e2e at `8d38206f460415b70706b45acb820bb0e24832ae`](https://github.com/tester-army/e2e/tree/8d38206f460415b70706b45acb820bb0e24832ae) (Apache-2.0, Copyright TesterArmy, Inc.), notably its [bug-bash reference](https://github.com/tester-army/e2e/blob/8d38206f460415b70706b45acb820bb0e24832ae/skills/e2e/references/bug-bash.md) (sha256 `713b3cfd325f30431c9719ea2897cb85c3488d9fcdade0927990bb2e1a524d01`). The wording is written for cstack and uses the project's own verification harness; no source text or code is copied, and no e2e runtime is required.

## Skill authoring and delivery methods

The baseline-first pressure test in `skills/cstack/references/rule-pressure-tests.md` (a realistic scenario with three or more combined pressures and a forced choice, run without the rule first, verbatim excuses, a minimal rule, an explicit negation for each new excuse and the meta question on how the rule should have been written) follows the method of [obra/superpowers v6.4.2 at `8ca22dba9a94f28898bbce59f2537ff4d87c747d`](https://github.com/obra/superpowers/blob/8ca22dba9a94f28898bbce59f2537ff4d87c747d/skills/writing-skills/testing-skills-with-subagents.md) (sha256 `c711346852c911b24a84aa161e0cff06a4cd7f4e2fa9e9c0a266cead5afcbade`; MIT, Copyright (c) 2025 Jesse Vincent). The wording is written for cstack; no source text is copied.

The pull-request body guidance in `skills/cstack/playbooks/opening-a-pr.md` (the smallest visual that makes the change clear, before-and-after evidence, one-way or two-way door) follows the [pr skill of mattpocock/skills at `d81f3a183412e71a5b1e84ca21bc1a35eea03a60`](https://github.com/mattpocock/skills/blob/d81f3a183412e71a5b1e84ca21bc1a35eea03a60/skills/engineering/pr/SKILL.md) (sha256 `ab63f1cf78647389edcd386c9427c5dfca27ed2836930c24773ffee834c19bcd`; MIT, Copyright (c) 2026 Matt Pocock), which credits the show-me skill by Dex Horthy (HumanLayer). The wording is written for cstack; no source text is copied.

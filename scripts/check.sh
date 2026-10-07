#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

bun scripts/generate-facts.mjs --check
bun scripts/validate.ts
python3 -m unittest discover -s tests -p 'test_*.py'
bun test tests
(
  cd plugins/cstack/skills/cstack/scripts
  bun install --frozen-lockfile
  bun run test
  bun run typecheck
)
plugins/cstack/skills/cstack/scripts/node_modules/.bin/tsc -p tsconfig.json

shell_scripts=(
  scripts/check.sh
  plugins/cstack/scripts/run-tool.sh
  plugins/cstack/skills/cstack/scripts/worktree-audit.sh
  plugins/cstack/skills/show-me-your-work/scripts/log.sh
  install.sh
)
bash -n "${shell_scripts[@]}"
docker run --rm -v "$PWD:/repo:ro" -w /repo \
  koalaman/shellcheck:v0.10.0@sha256:2097951f02e735b613f4a34de20c40f937a6c8f18ecb170612c88c34517221fb \
  --severity=warning "${shell_scripts[@]}"
docker run --rm -v "$PWD:/repo:ro" -w /repo \
  rhysd/actionlint:1.7.12@sha256:b1934ee5f1c509618f2508e6eb47ee0d3520686341fec936f3b79331f9315667 \
  -no-color .github/workflows/*.yml plugins/cstack/automations/intake/templates/github-intake.yml
git diff --check

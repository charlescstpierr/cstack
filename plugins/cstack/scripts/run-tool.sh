#!/usr/bin/env bash
set -euo pipefail

script_dir=${BASH_SOURCE[0]%/*}
[ "$script_dir" = "${BASH_SOURCE[0]}" ] && script_dir=.
script_dir=$(cd -P -- "$script_dir" && pwd)
exec python3 "$script_dir/run_tool.py" "$@"

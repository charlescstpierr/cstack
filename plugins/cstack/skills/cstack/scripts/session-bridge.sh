#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: session-bridge.sh lineage <codex|claude-code|cursor|opencode> <native-session-id> <owner/repo@branch>
       session-bridge.sh import <runtime> <native-session-id> <owner/repo@branch> independent
       session-bridge.sh import <runtime> <native-session-id> <owner/repo@branch> onto <ref>
       session-bridge.sh checkpoint <owner/repo@branch> <summary>
       session-bridge.sh log <owner/repo@branch>
       session-bridge.sh resume <owner/repo@branch> [<target-runtime> --accept-loss]
       session-bridge.sh fork <owner/repo@ref> <new-branch> [<target-runtime> --accept-loss]

Requires an installed and signed-in agit CLI. Targets are explicit; this bridge
never publishes. Publishing with agit push is a separate action. Cursor can be imported but
cannot be a resume/fork destination. A target runtime requires explicit loss acknowledgment.
USAGE
}

fail() {
  printf 'session-bridge: %s\n' "$1" >&2
  exit 2
}

require_ref() {
  [[ $1 =~ ^[[:alnum:]_-]+/[[:alnum:]_-]+@[^[:space:]]+$ ]] || fail 'explicit owner/repo@ref required'
}

require_runtime() {
  case "$1" in
    codex|claude-code|opencode) ;;
    cursor) [[ $2 == source ]] || fail 'Cursor is import-only; choose codex, claude-code or opencode as destination' ;;
    *) fail "unsupported runtime: $1" ;;
  esac
}

case "${1:-}" in
  -h|--help|help) usage; exit 0 ;;
  lineage)
    [[ $# == 4 ]] || fail 'lineage requires runtime, native session id and owner/repo@branch'
    require_runtime "$2" source
    [[ -n $3 && $3 != -* ]] || fail 'native session id required'
    require_ref "$4"
    command=(import "$3" --from "$2" --into "$4" --propose-lineage)
    ;;
  import)
    [[ $# == 5 || $# == 6 ]] || fail 'import requires runtime, native session id, owner/repo@branch and a lineage choice'
    require_runtime "$2" source
    [[ -n $3 && $3 != -* ]] || fail 'native session id required'
    require_ref "$4"
    command=(import "$3" --from "$2" --into "$4")
    if [[ $5 == independent && $# == 5 ]]; then
      command+=(--independent)
    elif [[ $5 == onto && $# == 6 && -n $6 && $6 != -* ]]; then
      command+=(--onto "$6")
    else
      fail 'choose independent or onto <verified-ref> after inspecting lineage'
    fi
    ;;
  checkpoint)
    [[ $# == 3 ]] || fail 'checkpoint requires owner/repo@branch and summary'
    require_ref "$2"
    [[ -n $3 ]] || fail 'checkpoint summary required'
    command=(commit "$2" "--milestone=$3")
    ;;
  log)
    [[ $# == 2 ]] || fail 'log requires owner/repo@branch'
    require_ref "$2"
    command=(log "$2")
    ;;
  resume)
    [[ $# == 2 || $# == 4 ]] || fail 'resume requires owner/repo@branch and optional target runtime with --accept-loss'
    require_ref "$2"
    command=(resume "$2")
    if [[ $# == 4 ]]; then
      require_runtime "$3" destination
      [[ $4 == --accept-loss ]] || fail 'explicit --accept-loss required before runtime conversion'
      command+=(--as "$3")
    fi
    ;;
  fork)
    [[ $# == 3 || $# == 5 ]] || fail 'fork requires owner/repo@ref, new branch and optional target runtime with --accept-loss'
    require_ref "$2"
    [[ $3 =~ ^[[:alnum:]_][[:alnum:]_./-]*$ ]] || fail 'valid new branch required'
    command=(fork "$2" -b "$3" --resume)
    if [[ $# == 5 ]]; then
      require_runtime "$4" destination
      [[ $5 == --accept-loss ]] || fail 'explicit --accept-loss required before runtime conversion'
      command+=(--as "$4")
    fi
    ;;
  *) usage >&2; exit 2 ;;
esac

command -v agit >/dev/null 2>&1 || fail 'agit CLI not found; install @einsia/agent-git and run agit login'
exec agit "${command[@]}"

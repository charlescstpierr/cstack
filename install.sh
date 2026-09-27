#!/usr/bin/env bash
# Installe, met à jour, diagnostique ou retire le plugin cstack de Codex App et CLI.
# Toutes les modifications passent par `codex plugin` ; le script n'écrit jamais dans ~/.codex.
set -euo pipefail

REPO="${CSTACK_REPO:-charlescstpierr/cstack}"
CODEX="${CSTACK_CODEX:-codex}"
MARKETPLACE="cstack"
PLUGIN="cstack@cstack"

usage() {
  cat <<EOF
Usage : install.sh <commande> [options]

Commandes :
  install [--ref REF | --local]   Installe cstack depuis GitHub (ou ce clone avec --local).
  update [--ref REF]              Met à jour vers la dernière révision, ou vers REF.
  doctor                          Vérifie les prérequis, l'accès au dépôt et l'installation.
  uninstall                       Retire le plugin et sa source. Les dossiers .cstack/ des projets restent.

Options :
  --ref REF   Branche, tag ou commit de ${REPO} à installer.
  --local     Installe depuis le dossier de ce script (copie locale, sans mise à jour Git).

Une ligne, dépôt privé (gh authentifié) :
  gh api repos/${REPO}/contents/install.sh -H "Accept: application/vnd.github.raw" | bash -s -- install
EOF
}

ok() { printf '  ✓ %s\n' "$1"; }
warn() { printf '  ! %s\n' "$1"; }
fail() { printf '  ✗ %s\n' "$1"; }
die() { printf 'cstack : %s\n' "$1" >&2; exit 1; }

run_codex() { "$CODEX" "$@"; }

require_codex() {
  command -v "$CODEX" >/dev/null 2>&1 || die "Codex CLI introuvable. Installez-le d'abord : npm install -g @openai/codex"
}

repo_reachable() {
  GIT_TERMINAL_PROMPT=0 git ls-remote --exit-code "https://github.com/${REPO}.git" HEAD >/dev/null 2>&1
}

require_repo_access() {
  command -v git >/dev/null 2>&1 || die "git introuvable ; Codex en a besoin pour cloner ${REPO}."
  repo_reachable || die "accès refusé à ${REPO}. Connectez Git à GitHub : gh auth login && gh auth setup-git"
}

marketplace_configured() {
  run_codex plugin marketplace list 2>/dev/null | awk -v name="$MARKETPLACE" '$1 == name { found = 1 } END { exit !found }'
}

plugin_status() {
  run_codex plugin list --marketplace "$MARKETPLACE" 2>/dev/null |
    awk -v id="$PLUGIN" '$1 == id { s = $2; for (i = 3; i < NF; i++) s = s " " $i; print s; exit }'
}

add_marketplace() {
  local ref="$1" local_source="$2" source
  if [[ -n "$local_source" ]]; then
    source="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    [[ -f "$source/.agents/plugins/marketplace.json" ]] || die "--local exige un clone de ${REPO} ; ${source} n'en est pas un."
  else
    require_repo_access
    source="$REPO${ref:+@$ref}"
  fi
  local out
  if ! out="$(run_codex plugin marketplace add "$source" 2>&1)"; then
    # Codex refuse de changer la source (ref ou clone) d'un catalogue déjà ajouté : on la remplace.
    grep -q "already added from a different source" <<<"$out" || { printf '%s\n' "$out" >&2; exit 1; }
    echo "Changement de source : ${source}"
    # Essai dans un CODEX_HOME jetable : une ref ou une source invalide ne doit pas coûter l'installation actuelle.
    local trial
    trial="$(mktemp -d)"
    if ! out="$(CODEX_HOME="$trial" run_codex plugin marketplace add "$source" 2>&1)"; then
      rm -rf "$trial"
      printf '%s\n' "$out" >&2
      die "source inutilisable : ${source}. L'installation actuelle est conservée."
    fi
    rm -rf "$trial"
    run_codex plugin marketplace remove "$MARKETPLACE" >/dev/null
    out="$(run_codex plugin marketplace add "$source" 2>&1)" || { printf '%s\n' "$out" >&2; exit 1; }
  fi
  printf '%s\n' "$out"
}

finish() {
  run_codex plugin add "$PLUGIN"
  echo
  echo "cstack est prêt. Ouvrez une nouvelle tâche Codex, puis tapez \$cstack:cstack."
}

cmd_install() {
  local ref="" local_source=""
  while (($#)); do
    case "$1" in
      --ref) [[ $# -ge 2 ]] || die "--ref attend une valeur."; ref="$2"; shift 2 ;;
      --local) local_source=1; shift ;;
      *) usage >&2; exit 2 ;;
    esac
  done
  [[ -z "$ref" || -z "$local_source" ]] || die "--ref et --local s'excluent."
  require_codex
  add_marketplace "$ref" "$local_source"
  finish
}

cmd_update() {
  local ref=""
  while (($#)); do
    case "$1" in
      --ref) [[ $# -ge 2 ]] || die "--ref attend une valeur."; ref="$2"; shift 2 ;;
      *) usage >&2; exit 2 ;;
    esac
  done
  require_codex
  marketplace_configured || die "cstack n'est pas installé. Lancez : install.sh install"
  if [[ -n "$ref" ]]; then
    add_marketplace "$ref" ""
  else
    local out
    if ! out="$(run_codex plugin marketplace upgrade "$MARKETPLACE" 2>&1)"; then
      # Une source locale n'a pas de Git à tirer : `plugin add` recopie le clone tel quel.
      grep -q "not configured as a Git marketplace" <<<"$out" || { printf '%s\n' "$out" >&2; exit 1; }
      echo "Source locale : recopie depuis le clone, sans mise à jour Git."
    fi
  fi
  finish
}

cmd_doctor() {
  local problems=0 version status
  echo "Diagnostic cstack"
  if command -v "$CODEX" >/dev/null 2>&1; then
    ok "Codex CLI : $(run_codex --version 2>/dev/null | tail -n 1)"
  else
    fail "Codex CLI introuvable (npm install -g @openai/codex)"; problems=1
  fi
  if ! command -v git >/dev/null 2>&1; then
    fail "git introuvable"; problems=1
  elif repo_reachable; then
    ok "accès Git à ${REPO}"
  else
    fail "accès Git refusé à ${REPO} (gh auth login && gh auth setup-git)"; problems=1
  fi
  if command -v python3 >/dev/null 2>&1 && python3 -c 'import sys; sys.exit(sys.version_info < (3, 9))' 2>/dev/null; then
    ok "Python : $(python3 -c 'import platform; print(platform.python_version())')"
  else
    warn "Python 3.9 ou plus récent absent : les assistants de cstack ne pourront pas tourner"
  fi
  if version="$(bun --version 2>/dev/null)"; then
    ok "Bun : ${version}"
  else
    warn "Bun absent : suivi de PR et orchestration indisponibles (https://bun.sh)"
  fi
  if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
    ok "gh authentifié"
  else
    warn "gh absent ou non authentifié : opérations GitHub indisponibles"
  fi
  if command -v "$CODEX" >/dev/null 2>&1; then
    status="$(plugin_status || true)"
    if [[ "$status" == installed,\ enabled* ]]; then
      ok "plugin ${PLUGIN} : ${status}"
    else
      fail "plugin ${PLUGIN} : ${status:-absent} (install.sh install)"; problems=1
    fi
  fi
  return "$problems"
}

cmd_uninstall() {
  (($# == 0)) || { usage >&2; exit 2; }
  require_codex
  run_codex plugin remove "$PLUGIN"
  if marketplace_configured; then
    run_codex plugin marketplace remove "$MARKETPLACE"
  fi
  echo "cstack est retiré. Les dossiers .cstack/ de vos projets sont conservés."
}

main() {
  local command="${1:-}"
  (($#)) && shift
  case "$command" in
    install) cmd_install "$@" ;;
    update) cmd_update "$@" ;;
    doctor) cmd_doctor "$@" ;;
    uninstall) cmd_uninstall "$@" ;;
    -h | --help | help) usage ;;
    *) usage >&2; exit 2 ;;
  esac
}

main "$@"

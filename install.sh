#!/usr/bin/env bash
# Installe, met à jour, diagnostique ou retire le plugin cstack de Codex et de Claude Code,
# donc aussi des tâches Codex et Claude de T3 Code. Chaque hôte présent est traité.
# Toutes les modifications passent par `codex plugin` et `claude plugin` ; le script n'écrit jamais
# dans ~/.codex ni dans ~/.claude.
set -euo pipefail

REPO="${CSTACK_REPO:-charlescstpierr/cstack}"
CODEX="${CSTACK_CODEX:-codex}"
CLAUDE="${CSTACK_CLAUDE:-claude}"
MARKETPLACE="cstack"
PLUGIN="cstack@cstack"

usage() {
  cat <<EOF
Usage : install.sh <commande> [options]

Commandes :
  install [--ref REF | --local]   Installe cstack depuis GitHub (ou ce clone avec --local),
                                  dans Codex et dans Claude Code s'ils sont présents.
  update [--ref REF]              Met à jour vers la dernière révision, ou vers REF.
  doctor                          Vérifie les prérequis, l'accès au dépôt et l'installation.
  uninstall                       Retire le plugin et sa source. Les dossiers .cstack/ des projets restent.

Options :
  --ref REF   Branche, tag ou commit de ${REPO} à installer.
  --local     Installe depuis le dossier de ce script (copie locale, sans mise à jour Git).

Sans clone :
  curl -fsSL https://raw.githubusercontent.com/${REPO}/main/install.sh -o install-cstack.sh && bash install-cstack.sh install
EOF
}

ok() { printf '  ✓ %s\n' "$1"; }
warn() { printf '  ! %s\n' "$1"; }
fail() { printf '  ✗ %s\n' "$1"; }
die() { printf 'cstack : %s\n' "$1" >&2; exit 1; }
# Relaie la sortie d'une commande échouée, puis s'arrête.
die_with() { printf '%s\n' "$1" >&2; exit 1; }

run_codex() { "$CODEX" "$@"; }
run_claude() { "$CLAUDE" "$@"; }

# Masque les identifiants d'une URL (https://user:token@hôte) avant tout affichage.
redact() { sed -E 's#://[^/@]+@#://***@#g' <<<"$*"; }

has_codex() { command -v "$CODEX" >/dev/null 2>&1; }
has_claude() { command -v "$CLAUDE" >/dev/null 2>&1; }

python_ok() { python3 -c 'import sys; sys.exit(sys.version_info < (3, 9))' 2>/dev/null; }

require_tools() {
  has_codex || has_claude ||
    die "Codex CLI introuvable, Claude Code aussi. Installez-en au moins un : npm install -g @openai/codex"
  python_ok || die "Python 3.9 ou plus récent est requis."
}

read -r -d '' STATE_PARSER <<'PY' || true
import json, os, sys
query, marketplace, plugin = sys.argv[1:]
data = json.load(sys.stdin)
if not isinstance(data, dict):
    raise ValueError("invalid plugin state")
required = ("marketplaces",) if query == "marketplace" else ("installed", "available")
if any(not isinstance(data.get(key), list) or not all(isinstance(entry, dict) for entry in data[key]) for key in required):
    raise ValueError("incomplete plugin state")
if query == "marketplace":
    for entry in data.get("marketplaces", []):
        if entry.get("name") == marketplace:
            source = entry.get("marketplaceSource", {})
            if (not isinstance(source, dict) or source.get("sourceType") not in ("git", "local")
                    or not all(isinstance(value, str) and value for value in (source.get("source"), entry.get("root")))):
                raise ValueError("invalid marketplace source")
            print("\t".join([source.get("sourceType", ""), source.get("source", ""), entry.get("root", "")]))
else:
    for entry in data.get("installed", []) + data.get("available", []):
        if entry.get("pluginId") == plugin:
            if not isinstance(entry.get("installed"), bool):
                raise ValueError("invalid installed state")
            if entry["installed"] and (not isinstance(entry.get("enabled"), bool) or not isinstance(entry.get("version"), str)):
                raise ValueError("invalid plugin state")
            if query == "plugin-cache":
                version = entry.get("version")
                if not entry["installed"] or not isinstance(version, str) or not version or version in (".", "..") or "/" in version or "\\" in version:
                    raise ValueError("invalid installed version")
                print(os.path.join(os.environ.get("CODEX_HOME") or os.path.expanduser("~/.codex"), "plugins", "cache", marketplace, "cstack", version))
                break
            if entry.get("installed"):
                state = "enabled" if entry.get("enabled") else "disabled"
                print("installed, {} {}".format(state, entry.get("version", "")).strip())
            else:
                print("not installed")
            break
PY

# Lit l'état de Codex dans sa sortie JSON plutôt que dans ses tableaux texte.
#   marketplace   : « type<TAB>source<TAB>racine » si le catalogue cstack est configuré, rien sinon.
#   plugin-status : « installed, enabled 0.6.0 », « not installed » ou rien.
# Échoue si Codex ou sa sortie sont illisibles : un état inconnu n'est jamais pris pour « absent ».
codex_state() {
  local query="$1" json
  case "$query" in
    marketplace) json="$(run_codex plugin marketplace list --json 2>/dev/null)" || return 1 ;;
    plugin-status|plugin-cache) json="$(run_codex plugin list --json --available 2>/dev/null)" || return 1 ;;
  esac
  python3 -c "$STATE_PARSER" "$query" "$MARKETPLACE" "$PLUGIN" <<<"$json" 2>/dev/null
}

# Catalogue cstack configuré, ou arrêt si l'état de Codex est illisible.
current_marketplace() {
  codex_state marketplace || die "impossible de lire l'état de Codex (codex plugin marketplace list --json)."
}

# Arguments `marketplace add` qui recréent le catalogue décrit par current_marketplace.
# Échoue si le commit d'une source Git est illisible : restaurer sans lui changerait le plugin.
previous_source() {
  local type source root ref
  IFS=$'\t' read -r type source root <<<"$1"
  [[ "$type" == git ]] || { printf '%s\n' "$source"; return 0; }
  # Le commit exact du clone de Codex : une branche aurait pu avancer depuis la dernière mise à jour.
  ref="$(git -C "$root" rev-parse HEAD 2>/dev/null)" || return 1
  printf '%s\n' "$source" --ref "$ref"
}

# Branche suivie par le catalogue Git configuré ; échoue sur un commit épinglé.
tracked_branch() {
  local type source root
  IFS=$'\t' read -r type source root <<<"$1"
  git -C "$root" symbolic-ref -q --short HEAD 2>/dev/null
}

reachable() { GIT_TERMINAL_PROMPT=0 GIT_SSH_COMMAND="ssh -o BatchMode=yes" git ls-remote --exit-code "$1" HEAD >/dev/null 2>&1; }

# Choisit le transport Git qui joint le dépôt : HTTPS d'abord, SSH ensuite.
remote_source() {
  command -v git >/dev/null 2>&1 || die "git introuvable ; Codex en a besoin pour cloner ${REPO}."
  if reachable "https://github.com/${REPO}.git"; then
    echo "$REPO"
  elif reachable "git@github.com:${REPO}.git"; then
    echo "git@github.com:${REPO}.git"
  else
    die "accès refusé à ${REPO} en HTTPS comme en SSH. Vérifiez le réseau ; si Git passe par un compte GitHub, lancez gh auth login && gh auth setup-git"
  fi
}

# Configure la source demandée puis installe le plugin depuis elle.
add_marketplace() {
  local ref="$1" local_source="$2" out remote current
  local -a source
  if [[ -n "$local_source" ]]; then
    source=("$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)")
    [[ -f "${source[0]}/.agents/plugins/marketplace.json" ]] || die "--local exige un clone de ${REPO} ; ${source[0]} n'en est pas un."
  else
    remote="$(remote_source)"
    source=("$remote")
    [[ -z "$ref" ]] || source+=(--ref "$ref")
  fi
  current="$(current_marketplace)"
  if [[ -n "$current" ]]; then
    local type old_source root
    IFS=$'\t' read -r type old_source root <<<"$current"
    [[ "$old_source" == "${source[*]}" ]] || echo "Changement de source : $(redact "${source[@]}")"
  fi
  switch_marketplace "$current" "${source[@]}"
}

switch_marketplace() {
  local current="$1"; shift
  replace_marketplace codex "$current" "$@"
}

# Both hosts use this transaction. Only their official CLIs change active profiles.
host_state() {
  local host="$1" query="$2"
  if [[ "$host" == codex ]]; then codex_state "$query"; else claude_state "$query"; fi
}

host_run() {
  local host="$1"; shift
  if [[ "$host" == codex ]]; then run_codex "$@"; else run_claude "$@"; fi
}

host_install_plugin() {
  if [[ "$1" == codex ]]; then run_codex plugin add "$PLUGIN"; else run_claude plugin install "$PLUGIN"; fi
}

host_remove_plugin() {
  if [[ "$1" == codex ]]; then run_codex plugin remove "$PLUGIN"; else run_claude plugin uninstall "$PLUGIN"; fi
}

# A local marketplace root may already differ from the installed plugin cache.
# Rebuild that plugin's source in the recovery catalogue from its installed bytes.
snapshot_installed_plugin() {
  local host="$1" snapshot="$2" cache
  cache="$(host_state "$host" plugin-cache)" || die "chemin du plugin installé illisible ; installation actuelle conservée."
  [[ -n "$cache" && -d "$cache" ]] || die "cache du plugin installé introuvable ; installation actuelle conservée."
  python3 - "$host" "$snapshot/source" "$cache" <<'PY'
import json, shutil, sys
from pathlib import Path
host, recovery, cache = sys.argv[1:]
root = Path(recovery)
manifest = root / (".agents/plugins/marketplace.json" if host == "codex" else ".claude-plugin/marketplace.json")
data = json.loads(manifest.read_text())
entries = [entry for entry in data["plugins"] if entry.get("name") == "cstack"]
if len(entries) != 1:
    raise ValueError("catalogue sans source cstack unique")
source = entries[0]["source"]
relative = source.get("path") if isinstance(source, dict) and source.get("source") == "local" else source
if not isinstance(relative, str) or not relative or Path(relative).is_absolute() or ".." in Path(relative).parts:
    raise ValueError("source du plugin installé non locale : restauration exacte impossible")
destination = root / relative
if destination.resolve() == root.resolve() or root.resolve() not in destination.resolve().parents:
    raise ValueError("source du plugin hors instantané")
if destination.is_symlink():
    destination.unlink()
elif destination.exists():
    shutil.rmtree(destination)
destination.parent.mkdir(parents=True, exist_ok=True)
shutil.copytree(cache, destination, symlinks=True)
PY
}

replace_marketplace() (
  # The subshell keeps traps and transaction state out of the next host's transaction.
  local host="$1" current="$2" status root="" type old_source prev="" out trial="" snapshot="" phase=prepare
  shift 2
  local -a source=("$@")
  umask 077
  status="$(host_state "$host" plugin-status)" || die "état du plugin illisible dans $host ; l'installation actuelle est conservée."
  [[ "$status" != "installed, disabled"* ]] || die "cstack est désactivé dans $host ; l'installation actuelle est conservée."
  [[ -n "$current" || "$status" != installed* ]] || die "plugin installé sans catalogue attesté dans $host ; état conservé."

  restore_transaction() {
    local status_now source_now configured
    # A failed CLI may have applied part of its operation before returning an error.
    host_remove_plugin "$host" >/dev/null 2>&1 || true
    host_run "$host" plugin marketplace remove "$MARKETPLACE" >/dev/null 2>&1 || true
    if [[ -n "$current" ]]; then
      host_run "$host" plugin marketplace add "$snapshot/source" >/dev/null 2>&1 || return 1
      [[ "$status" != installed* ]] || host_install_plugin "$host" >/dev/null 2>&1 || return 1
    fi
    source_now="$(host_state "$host" marketplace)" || return 1
    if [[ -z "$current" ]]; then
      [[ -z "$source_now" ]] || return 1
    elif [[ "$host" == codex ]]; then
      IFS=$'\t' read -r _ configured _ <<<"$source_now"
      [[ "$configured" == "$snapshot/source" ]] || return 1
    else
      [[ "$source_now" == "$snapshot/source" ]] || return 1
    fi
    status_now="$(host_state "$host" plugin-status)" || return 1
    if [[ "$status" == installed* ]]; then
      [[ "$status_now" == "$status" ]] || return 1
    else
      [[ "$status_now" != installed* ]] || return 1
    fi
  }

  finish_transaction() {
    local code=$?
    trap - EXIT INT TERM
    [[ -z "$trial" ]] || rm -rf "$trial"
    if [[ "$phase" == apply ]]; then
      if restore_transaction; then
        printf "cstack : échec ; l'ancienne installation est restaurée dans %s.\n" "$host" >&2
        if [[ -n "$snapshot" ]]; then
          printf 'Source de reprise conservée : %s/source ; source initiale : %s\n' "$snapshot" "$(redact "$prev")" >&2
        fi
      else
        printf 'cstack : restauration impossible dans %s ; reprise : %s\n' "$host" "${snapshot:-état initial absent, nettoyage manuel requis}" >&2
      fi
      # The restored marketplace now refers to this immutable recovery source.
      snapshot=""
      ((code != 0)) || code=1
    fi
    [[ -z "$snapshot" ]] || rm -rf "$snapshot"
    exit "$code"
  }
  trap finish_transaction EXIT
  trap 'exit 130' INT
  trap 'exit 143' TERM

  if [[ -n "$current" ]]; then
    if [[ "$host" == codex ]]; then
      IFS=$'\t' read -r type old_source root <<<"$current"
      prev="$(previous_source "$current")" || die "commit actuel illisible ; l'installation actuelle est conservée."
    else
      [[ "$current" != "?" ]] || die "source actuelle de Claude Code illisible ; l'installation actuelle est conservée."
      root="$(claude_state marketplace-root)" || die "racine du catalogue Claude Code illisible."
      prev="$current"
    fi
    [[ -n "$root" && -d "$root" ]] || die "instantané actuel introuvable dans $host ; l'installation actuelle est conservée."
    local state_dir="${XDG_STATE_HOME:-$HOME/.local/state}/cstack"
    mkdir -p "$state_dir"
    snapshot="$(mktemp -d "$state_dir/install-rollback.XXXXXXXX")"
    cp -a "$root/." "$snapshot/source"
    if [[ "$status" == installed* ]]; then
      snapshot_installed_plugin "$host" "$snapshot"
    fi
    printf '%s\n' "$prev" > "$snapshot/source-before.txt"
    printf '%s\n' "$status" > "$snapshot/status-before.txt"
  fi

  trial="$(mktemp -d)"
  if ! out="$({
    if [[ "$host" == codex ]]; then export CODEX_HOME="$trial"; else export CLAUDE_CONFIG_DIR="$trial"; fi
    host_run "$host" plugin marketplace add "${source[@]}" && host_install_plugin "$host"
  } 2>&1)"; then
    die_with "$(redact "$out")"$'\n'"cstack : installation du plugin impossible, source inutilisable. L'installation actuelle est conservée."
  fi
  phase=apply
  if [[ -n "$current" ]]; then
    if ! out="$(host_run "$host" plugin marketplace remove "$MARKETPLACE" 2>&1)"; then
      die_with "$(redact "$out")"$'\n'"cstack : retrait du catalogue dans $host impossible."
    fi
  fi
  if ! out="$({ host_run "$host" plugin marketplace add "${source[@]}" && host_install_plugin "$host"; } 2>&1)"; then
    die_with "$(redact "$out")"$'\n'"cstack : installation du plugin impossible dans $host."
  fi
  phase="done"
  redact "$out"
)

read -r -d '' CLAUDE_PARSER <<'PY' || true
import json, os, sys
query, marketplace, plugin = sys.argv[1:]
data = json.load(sys.stdin)
if not isinstance(data, list) or not all(isinstance(entry, dict) for entry in data):
    raise ValueError("invalid plugin state")
if query in ("marketplace", "marketplace-root"):
    for entry in data:
        if entry.get("name") == marketplace:
            if query == "marketplace-root":
                root = entry.get("installLocation")
                if not isinstance(root, str) or not root:
                    raise ValueError("missing marketplace snapshot")
                print(root)
                break
            # La source telle que `claude plugin marketplace add` la reprend ; « ? » si sa forme est inconnue.
            ref = "#" + entry["ref"] if entry.get("ref") else ""
            kind = entry.get("source")
            if kind == "github" and entry.get("repo"):
                print(entry["repo"] + ref)
            elif kind == "git" and entry.get("url"):
                print(entry["url"] + ref)
            elif kind == "directory" and entry.get("path"):
                print(entry["path"])
            else:
                print("?")
else:
    for entry in data:
        if entry.get("id") == plugin:
            if not isinstance(entry.get("enabled"), bool) or not isinstance(entry.get("version"), str):
                raise ValueError("invalid plugin state")
            if query == "plugin-cache":
                cache = entry.get("installPath")
                if not isinstance(cache, str) or not cache:
                    raise ValueError("missing installed cache")
                print(cache)
            else:
                print("installed, {} {}".format("enabled" if entry.get("enabled") else "disabled", entry.get("version", "")).strip())
PY

# État de Claude Code, lu dans sa sortie JSON.
#   marketplace   : la source du catalogue cstack (« ? » si sa forme est inconnue), rien s'il est absent.
#   plugin-status : « installed, enabled 0.8.0 » ou rien.
# Échoue si Claude Code ou sa sortie sont illisibles : un état inconnu n'est jamais pris pour « absent ».
claude_state() {
  local query="$1" json
  case "$query" in
    marketplace|marketplace-root) json="$(run_claude plugin marketplace list --json 2>/dev/null)" || return 1 ;;
    plugin-status|plugin-cache) json="$(run_claude plugin list --json 2>/dev/null)" || return 1 ;;
  esac
  python3 -c "$CLAUDE_PARSER" "$query" "$MARKETPLACE" "$PLUGIN" <<<"$json" 2>/dev/null
}

# Claude Code lit la ref après « # » : owner/repo#ref ou git@github.com:owner/repo.git#ref.
claude_source() {
  local ref="$1" local_source="$2" source
  if [[ -n "$local_source" ]]; then
    source="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    [[ -f "$source/.claude-plugin/marketplace.json" ]] || die "--local exige un clone de ${REPO} ; $source n'en est pas un."
  else
    source="$(remote_source)" || return 1
    source+="${ref:+#$ref}"
  fi
  printf '%s\n' "$source"
}

current_claude_marketplace() {
  claude_state marketplace || die "impossible de lire l'état de Claude Code (claude plugin marketplace list --json)."
}

# Ajoute le catalogue puis installe le plugin. Une ref ou --local remplace le catalogue existant.
claude_install() {
  local ref="$1" local_source="$2" source current
  source="$(claude_source "$ref" "$local_source")"
  current="$(current_claude_marketplace)"
  claude_switch "$current" "$source"
}

claude_switch() {
  replace_marketplace claude "$1" "$2"
}

claude_update() {
  local ref="$1" current root branch
  current="$(current_claude_marketplace)"
  if [[ -n "$ref" ]]; then
    claude_install "$ref" ""
  elif [[ "$current" == /* ]]; then
    claude_switch "$current" "$current"
  else
    root="$(claude_state marketplace-root)" || die "racine du catalogue Claude Code illisible."
    branch="$(git -C "$root" symbolic-ref -q --short HEAD 2>/dev/null)" ||
      die "cstack est épinglé dans Claude Code ; utilisez install.sh install --ref <branche>"
    claude_switch "$current" "${current%%#*}#$branch"
  fi
}


finish() {
  echo
  echo "cstack est prêt. Ouvrez une nouvelle tâche, dans T3 Code, Codex ou Claude Code, puis tapez :"
  ! has_codex || echo "  \$cstack:cstack   (Codex)"
  ! has_claude || echo "  /cstack:cstack   (Claude)"
}

# Lit --ref et --local dans ref et local_source, déclarées par l'appelant.
parse_options() {
  while (($#)); do
    case "$1" in
      --ref) [[ $# -ge 2 && -n "$2" ]] || die "--ref attend une valeur non vide."; ref="$2"; shift 2 ;;
      --local) local_source=1; shift ;;
      *) usage >&2; exit 2 ;;
    esac
  done
  [[ -z "$ref" || -z "$local_source" ]] || die "--ref et --local s'excluent."
}

cmd_install() {
  local ref="" local_source=""
  parse_options "$@"
  require_tools
  ! has_codex || add_marketplace "$ref" "$local_source"
  ! has_claude || claude_install "$ref" "$local_source"
  finish
}

cmd_update() {
  local ref="" local_source="" current="" claude_present=""
  parse_options "$@"
  [[ -z "$local_source" ]] || die "update ne prend pas --local ; utilisez install --local."
  require_tools
  ! has_codex || current="$(current_marketplace)"
  ! has_claude || claude_present="$(current_claude_marketplace)"
  [[ -n "$current$claude_present" ]] || die "cstack n'est pas installé. Lancez : install.sh install"
  [[ -z "$current" ]] || codex_update "$current" "$ref"
  [[ -z "$claude_present" ]] || claude_update "$ref"
  finish
}

codex_update() {
  local current="$1" ref="$2" branch url
  if [[ -n "$ref" ]]; then
    # Même avec une ref déjà configurée, `marketplace add` ne rafraîchirait pas le clone : on remplace.
    url="$(remote_source)"
    echo "Mise à jour : $(redact "$url") --ref ${ref}"
    switch_marketplace "$current" "$url" --ref "$ref"
  elif [[ "$current" == git$'\t'* ]]; then
    # La nouvelle pointe de la branche passe par le même remplacement validé qu'un changement de source.
    branch="$(tracked_branch "$current")" ||
      die "cstack est épinglé sur un commit et n'avance pas. Pour suivre une branche : install.sh install --ref main"
    IFS=$'\t' read -r _ url _ <<<"$current"
    echo "Mise à jour : $(redact "$url") --ref ${branch}"
    switch_marketplace "$current" "$url" --ref "$branch"
  else
    local type source root
    IFS=$'\t' read -r type source root <<<"$current"
    echo "Source locale : recopie depuis le clone, sans mise à jour Git."
    switch_marketplace "$current" "$source"
  fi
}

cmd_doctor() {
  local problems=0 version status
  (($# == 0)) || { usage >&2; exit 2; }
  echo "Diagnostic cstack"
  if ! has_codex; then
    if has_claude; then
      warn "Codex CLI absent : cstack s'installe seulement dans Claude Code"
    else
      fail "Codex CLI introuvable (npm install -g @openai/codex)"; problems=1
    fi
  elif version="$(run_codex --version 2>&1)"; then
    ok "Codex CLI : $(tail -n 1 <<<"$version")"
  else
    fail "Codex CLI inutilisable : $(tail -n 1 <<<"$version")"; problems=1
  fi
  if ! has_claude; then
    warn "Claude Code absent : cstack s'installe seulement dans Codex"
  elif version="$(run_claude --version 2>&1)"; then
    ok "Claude Code : $(tail -n 1 <<<"$version")"
  else
    fail "Claude Code inutilisable : $(tail -n 1 <<<"$version")"; problems=1
  fi
  if python_ok; then
    ok "Python : $(python3 -c 'import platform; print(platform.python_version())')"
  else
    fail "Python 3.9 ou plus récent introuvable"; problems=1
  fi
  if ! command -v git >/dev/null 2>&1; then
    fail "git introuvable : Codex en a besoin pour cloner ${REPO}"; problems=1
  elif (remote_source >/dev/null 2>&1); then
    ok "accès Git à ${REPO}"
  else
    fail "accès Git refusé à ${REPO} (vérifiez le réseau, ou gh auth login && gh auth setup-git)"; problems=1
  fi
  if ! version="$(bun --version 2>/dev/null)"; then
    warn "Bun absent : suivi de PR et orchestration indisponibles (https://bun.sh)"
  elif bun --help 2>/dev/null | grep -q -- --no-env-file; then
    ok "Bun : ${version}"
  else
    warn "Bun ${version} trop ancien : les assistants exigent --no-env-file (bun upgrade)"
  fi
  if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
    ok "gh authentifié"
  else
    warn "gh absent ou non authentifié : opérations GitHub indisponibles"
  fi
  if has_codex && python_ok; then
    status="$(codex_state plugin-status)" || status="état illisible"
    if [[ "$status" == installed,\ enabled* ]]; then
      ok "plugin ${PLUGIN} : ${status}"
    else
      fail "plugin ${PLUGIN} : ${status:-absent} (install.sh install)"; problems=1
    fi
  fi
  if has_claude && python_ok; then
    status="$(claude_state plugin-status)" || status="état illisible"
    if [[ "$status" == installed,\ enabled* ]]; then
      ok "plugin ${PLUGIN} dans Claude Code : ${status}"
    else
      fail "plugin ${PLUGIN} dans Claude Code : ${status:-absent} (install.sh install)"; problems=1
    fi
  fi
  return "$problems"
}

cmd_uninstall() {
  (($# == 0)) || { usage >&2; exit 2; }
  local current claude_current=""
  require_tools
  # Lire les deux états avant de retirer quoi que ce soit : un état illisible arrête tout.
  ! has_claude || claude_current="$(current_claude_marketplace)"
  if has_codex; then
    current="$(current_marketplace)"
    run_codex plugin remove "$PLUGIN"
    if [[ -n "$current" ]]; then
      run_codex plugin marketplace remove "$MARKETPLACE"
    fi
  fi
  if [[ -n "$claude_current" ]]; then
    run_claude plugin uninstall "$PLUGIN" >/dev/null 2>&1 || true
    run_claude plugin marketplace remove "$MARKETPLACE"
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

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
import json, sys
query, marketplace, plugin = sys.argv[1:]
data = json.load(sys.stdin)
if query == "marketplace":
    for entry in data.get("marketplaces", []):
        if entry.get("name") == marketplace:
            source = entry.get("marketplaceSource", {})
            print("\t".join([source.get("sourceType", ""), source.get("source", ""), entry.get("root", "")]))
else:
    for entry in data.get("installed", []) + data.get("available", []):
        if entry.get("pluginId") == plugin:
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
    plugin-status) json="$(run_codex plugin list --json --available 2>/dev/null)" || return 1 ;;
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
  # Même relancée à l'identique, l'installation ne doit pas réactiver un plugin désactivé.
  [[ -z "$current" ]] || plugin_state_before_refresh >/dev/null
  if out="$(run_codex plugin marketplace add "${source[@]}" 2>&1)"; then
    redact "$out"
    if ! run_codex plugin add "$PLUGIN"; then
      # Un catalogue créé par cet appel ne survit pas à l'échec de l'installation du plugin.
      [[ -n "$current" ]] || run_codex plugin marketplace remove "$MARKETPLACE" >/dev/null 2>&1 || true
      die "installation du plugin impossible."
    fi
    return
  fi
  # Codex refuse de changer la source (ref ou clone) d'un catalogue déjà configuré.
  [[ -n "$current" ]] || die_with "$(redact "$out")"
  echo "Changement de source : $(redact "${source[@]}")"
  switch_marketplace "$current" "${source[@]}"
}

# État du plugin avant une mise à jour ; arrêt s'il est illisible ou désactivé.
# `plugin add` réactive un plugin désactivé et la CLI n'offre aucun moyen de le désactiver de nouveau.
plugin_state_before_refresh() {
  local status
  status="$(codex_state plugin-status)" || die "état du plugin illisible (codex plugin list --json) ; l'installation actuelle est conservée."
  [[ "$status" != "installed, disabled"* ]] ||
    die "cstack est désactivé : une mise à jour le réactiverait. Réactivez-le dans Codex, ou retirez-le (install.sh uninstall), puis relancez."
  printf '%s\n' "$status"
}

# Remplace le catalogue configuré (décrit par $1) par la source qui suit, plugin compris.
# Toute étape ratée laisse ou remet l'installation précédente, à son commit exact.
switch_marketplace() {
  local current="$1" out trial trial_failed="" prev line was_installed="" status
  shift
  local -a source=("$@") previous
  prev="$(previous_source "$current")" || die "commit actuel illisible dans le clone de Codex ; l'installation actuelle est conservée."
  while IFS= read -r line; do previous+=("$line"); done <<<"$prev"
  # La restauration ne réinstalle le plugin que s'il l'était avant la commande.
  status="$(plugin_state_before_refresh)"
  [[ "$status" != installed* ]] || was_installed=1
  # Essai dans un CODEX_HOME jetable : une source invalide ne doit pas coûter l'installation actuelle.
  trial="$(mktemp -d)"
  # L'essai installe aussi le plugin : un catalogue valide sans cstack utilisable est refusé ici.
  out="$({ CODEX_HOME="$trial" run_codex plugin marketplace add "${source[@]}" &&
    CODEX_HOME="$trial" run_codex plugin add "$PLUGIN"; } 2>&1)" || trial_failed=1
  rm -rf "$trial"
  [[ -z "$trial_failed" ]] || die_with "$(redact "$out")"$'\n'"cstack : source inutilisable. L'installation actuelle est conservée."
  run_codex plugin marketplace remove "$MARKETPLACE" >/dev/null
  # Catalogue et plugin forment une seule transaction : tout échec restaure l'ancienne source.
  if ! out="$({ run_codex plugin marketplace add "${source[@]}" && run_codex plugin add "$PLUGIN"; } 2>&1)"; then
    redact "$out" >&2
    run_codex plugin marketplace remove "$MARKETPLACE" >/dev/null 2>&1 || true
    { run_codex plugin marketplace add "${previous[@]}" && { [[ -z "$was_installed" ]] || run_codex plugin add "$PLUGIN"; }; } >/dev/null 2>&1 ||
      die "échec, et l'ancienne source ($(redact "${previous[@]}")) n'a pas pu être restaurée : relancez install.sh install."
    [[ "$current" == git$'\t'* ]] ||
      die "échec ; l'ancienne source locale ($(redact "${previous[@]}")) est restaurée, recopiée depuis l'état actuel du clone."
    die "échec ; l'ancienne source ($(redact "${previous[@]}")) est restaurée à son commit précédent. Pour suivre de nouveau une branche : install.sh install --ref <branche>"
  fi
  redact "$out"
}

read -r -d '' CLAUDE_PARSER <<'PY' || true
import json, sys
query, marketplace, plugin = sys.argv[1:]
data = json.load(sys.stdin)
if query == "marketplace":
    for entry in data:
        if entry.get("name") == marketplace:
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
            print("installed, {} {}".format("enabled" if entry.get("enabled") else "disabled", entry.get("version", "")).strip())
PY

# État de Claude Code, lu dans sa sortie JSON.
#   marketplace   : la source du catalogue cstack (« ? » si sa forme est inconnue), rien s'il est absent.
#   plugin-status : « installed, enabled 0.8.0 » ou rien.
# Échoue si Claude Code ou sa sortie sont illisibles : un état inconnu n'est jamais pris pour « absent ».
claude_state() {
  local query="$1" json
  case "$query" in
    marketplace) json="$(run_claude plugin marketplace list --json 2>/dev/null)" || return 1 ;;
    plugin-status) json="$(run_claude plugin list --json 2>/dev/null)" || return 1 ;;
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
  if [[ -n "$current" && -n "$ref$local_source" ]]; then
    echo "Claude Code, changement de source : $(redact "$source")"
    claude_switch "$current" "$source"
    return
  fi
  run_claude plugin marketplace add "$source" || die "ajout du catalogue dans Claude Code impossible."
  if ! run_claude plugin install "$PLUGIN"; then
    # Un catalogue créé par cet appel ne survit pas à l'échec de l'installation du plugin.
    [[ -n "$current" ]] || run_claude plugin marketplace remove "$MARKETPLACE" >/dev/null 2>&1 || true
    die "installation dans Claude Code impossible."
  fi
}

# Remplace le catalogue Claude Code ($1, sa source actuelle) par la source $2, plugin compris.
# Comme côté Codex : essai dans un profil jetable, puis restauration de l'ancienne source si le remplacement échoue.
claude_switch() {
  local old_source="$1" source="$2" status was_installed="" trial out trial_failed=""
  [[ "$old_source" != "?" ]] || die "source actuelle de Claude Code illisible ; l'installation actuelle est conservée."
  status="$(claude_state plugin-status)" || die "état du plugin illisible dans Claude Code ; l'installation actuelle est conservée."
  [[ -z "$status" ]] || was_installed=1
  trial="$(mktemp -d)"
  out="$({ CLAUDE_CONFIG_DIR="$trial" run_claude plugin marketplace add "$source" &&
    CLAUDE_CONFIG_DIR="$trial" run_claude plugin install "$PLUGIN"; } 2>&1)" || trial_failed=1
  rm -rf "$trial"
  [[ -z "$trial_failed" ]] || die_with "$(redact "$out")"$'\n'"cstack : source inutilisable dans Claude Code. L'installation actuelle est conservée."
  run_claude plugin marketplace remove "$MARKETPLACE" >/dev/null
  if ! out="$({ run_claude plugin marketplace add "$source" && run_claude plugin install "$PLUGIN"; } 2>&1)"; then
    redact "$out" >&2
    run_claude plugin marketplace remove "$MARKETPLACE" >/dev/null 2>&1 || true
    { run_claude plugin marketplace add "$old_source" && { [[ -z "$was_installed" ]] || run_claude plugin install "$PLUGIN"; }; } >/dev/null 2>&1 ||
      die "échec dans Claude Code, et l'ancienne source ($(redact "$old_source")) n'a pas pu être restaurée : relancez install.sh install."
    die "échec dans Claude Code ; l'ancienne source ($(redact "$old_source")) est restaurée."
  fi
  redact "$out"
}

claude_update() {
  local ref="$1"
  if [[ -n "$ref" ]]; then
    claude_install "$ref" ""
  else
    run_claude plugin marketplace update "$MARKETPLACE" && run_claude plugin update "$PLUGIN" ||
      die "mise à jour dans Claude Code impossible."
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
    plugin_state_before_refresh >/dev/null
    echo "Source locale : recopie depuis le clone, sans mise à jour Git."
    run_codex plugin add "$PLUGIN"
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

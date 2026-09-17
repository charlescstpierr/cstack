#!/usr/bin/env bash
# Audit en lecture seule des worktrees à nettoyer. Classe chaque worktree git
# par taille, état de fusion, travail non commité et état distant/PR. Émet une
# table triée par taille avec un regroupement de revue conservateur. Ne supprime
# rien et ne récupère rien.
#
# Utilisation: worktree-audit.sh [chemin-dépôt]   (dépôt courant par défaut)
set -u

repo="${1:-$(git rev-parse --show-toplevel 2>/dev/null)}"
[ -z "$repo" ] && { echo "pas dans un dépôt git; passer un chemin de dépôt" >&2; exit 1; }
cd "$repo" || exit 1

worktrees() {
	git worktree list --porcelain -z | while IFS= read -r -d '' field; do
		case "$field" in worktree\ *) printf '%s\0' "${field#worktree }" ;; esac
	done
}

# Le worktree principal est la première entrée; tout le reste est candidat.
worktree_paths=()
while IFS= read -r -d '' wt; do worktree_paths+=("$wt"); done < <(worktrees)
[ "${#worktree_paths[@]}" -eq 0 ] && { echo "le dépôt n’a aucun worktree" >&2; exit 1; }
main_wt=${worktree_paths[0]}

# Utiliser la branche distante par défaut enregistrée localement sans muter les refs.
base_ref=$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null || true)
[ -z "$base_ref" ] && echo "avertissement: origin/HEAD est indisponible; la colonne fusionnée sera inconnue" >&2

# État des PR par branche, récupéré une fois. Vide si gh est indisponible.
prs=$(mktemp)
trap 'rm -f "$prs"' EXIT
gh pr list --author "@me" --state all --limit 1000 \
	--json number,state,headRefName 2>/dev/null > "$prs" || echo "[]" > "$prs"

now=$(date +%s)

printf "TAILLE\tÂGE\tFUSIONNÉ\tSALE\tDISTANT\tPR\tDERNIER_CHAT\tGROUPE\tWORKTREE\n"

for wt in "${worktree_paths[@]}"; do
	[ "$wt" = "$main_wt" ] && continue

	size=$(du -sh "$wt" 2>/dev/null | awk '{print $1}')
	head=$(git -C "$wt" rev-parse HEAD 2>/dev/null)
	head_ts=$(git -C "$wt" log -1 --format='%ct' HEAD 2>/dev/null || echo 0)
	age=$([ "$head_ts" -gt 0 ] 2>/dev/null && echo "$(( (now - head_ts) / 86400 ))d" || echo "?")

	# Les branches squash-merged ne sont pas ancêtres de la branche par défaut:
	# l’état de PR est donc le vrai signal; merge-base ne voit que les fusions
	# fast-forward/rebase.
	if [ -z "$base_ref" ]; then merged="?"
	elif git merge-base --is-ancestor "$head" "$base_ref" 2>/dev/null; then merged=YES
	else merged=no; fi

	# Distinguer le vrai WIP (edits suivis) du brouillon non suivi jetable.
	if porcelain=$(git -C "$wt" status --porcelain 2>/dev/null); then
		if [ -z "$porcelain" ]; then dirty=clean
		elif printf '%s\n' "$porcelain" | grep -qv '^??'; then
			dirty="wip:$(printf '%s\n' "$porcelain" | grep -cv '^??')"
		else dirty="scratch:$(printf '%s\n' "$porcelain" | grep -c '^??')"; fi
	else dirty=unknown; fi

	branch=$(git -C "$wt" symbolic-ref --quiet --short HEAD 2>/dev/null || echo "")
	if [ -z "$branch" ]; then remote=detached
	elif git -C "$wt" show-ref --verify --quiet "refs/remotes/origin/$branch"; then
		[ "$(git -C "$wt" rev-parse "origin/$branch" 2>/dev/null)" = "$head" ] \
			&& remote=pushed \
			|| remote="ahead$(git -C "$wt" rev-list --count "origin/$branch..HEAD" 2>/dev/null)"
	else remote=no-remote; fi

	pr=$([ -n "$branch" ] && python3 -c \
		'import json,sys; print(next(("#%s/%s" % (pr["number"], pr["state"]) for pr in json.load(open(sys.argv[2])) if pr.get("headRefName") == sys.argv[1]), ""))' \
		"$branch" "$prs" 2>/dev/null)
	[ -z "$pr" ] && pr="-"

	last=indisponible

	case "$dirty" in unknown) bucket=hold-unknown ;; wip:*) bucket=hold-wip ;; *)
		case "$pr" in *OPEN*) bucket=hold-open-pr ;; *)
			bucket=review ;;
		esac ;;
	esac

	printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
		"$size" "$age" "$merged" "$dirty" "$remote" "$pr" "$last" "$bucket" "$wt"
done | sort -t$'\t' -k1,1 -rh

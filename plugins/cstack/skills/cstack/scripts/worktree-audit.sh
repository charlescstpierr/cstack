#!/usr/bin/env bash
# Read-only worktree prune audit. Classifies every git worktree by size, merge
# state, uncommitted work, and remote/PR state. Emits a table sorted by size
# with a conservative review bucket. Never deletes or fetches anything.
#
# Usage: worktree-audit.sh [repo-path]   (defaults to the current repo)
set -u

repo="${1:-$(git rev-parse --show-toplevel 2>/dev/null)}"
[ -z "$repo" ] && { echo "not in a git repo; pass a repo path" >&2; exit 1; }
cd "$repo" || exit 1

worktrees() {
	git worktree list --porcelain -z | while IFS= read -r -d '' field; do
		case "$field" in worktree\ *) printf '%s\0' "${field#worktree }" ;; esac
	done
}

# Main worktree is the first entry; everything else is a candidate.
worktree_paths=()
while IFS= read -r -d '' wt; do worktree_paths+=("$wt"); done < <(worktrees)
[ "${#worktree_paths[@]}" -eq 0 ] && { echo "repo has no worktrees" >&2; exit 1; }
main_wt=${worktree_paths[0]}

# Use the locally recorded remote default without mutating refs.
base_ref=$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null || true)
[ -z "$base_ref" ] && echo "warn: origin/HEAD is unavailable; merged column will be unknown" >&2

# PR state by branch, fetched once. Empty if gh is unavailable.
prs=$(mktemp)
trap 'rm -f "$prs"' EXIT
gh pr list --author "@me" --state all --limit 1000 \
	--json number,state,headRefName 2>/dev/null > "$prs" || echo "[]" > "$prs"

now=$(date +%s)

printf "SIZE\tAGE\tMERGED\tDIRTY\tREMOTE\tPR\tLAST_CHAT\tBUCKET\tWORKTREE\n"

for wt in "${worktree_paths[@]}"; do
	[ "$wt" = "$main_wt" ] && continue

	size=$(du -sh "$wt" 2>/dev/null | awk '{print $1}')
	head=$(git -C "$wt" rev-parse HEAD 2>/dev/null)
	head_ts=$(git -C "$wt" log -1 --format='%ct' HEAD 2>/dev/null || echo 0)
	age=$([ "$head_ts" -gt 0 ] 2>/dev/null && echo "$(( (now - head_ts) / 86400 ))d" || echo "?")

	# Squash-merged branches are not ancestors of the default branch, so PR state is the
	# real signal; merge-base only catches fast-forward/rebase merges.
	if [ -z "$base_ref" ]; then merged="?"
	elif git merge-base --is-ancestor "$head" "$base_ref" 2>/dev/null; then merged=YES
	else merged=no; fi

	# Distinguish real WIP (tracked edits) from disposable untracked scratch.
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

	last=unavailable

	case "$dirty" in unknown) bucket=hold-unknown ;; wip:*) bucket=hold-wip ;; *)
		case "$pr" in *OPEN*) bucket=hold-open-pr ;; *)
			bucket=review ;;
		esac ;;
	esac

	printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
		"$size" "$age" "$merged" "$dirty" "$remote" "$pr" "$last" "$bucket" "$wt"
done | sort -t$'\t' -k1,1 -rh

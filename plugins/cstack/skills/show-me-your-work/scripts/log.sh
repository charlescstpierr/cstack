#!/usr/bin/env bash
# Ajouter une ligne bien formée au journal de décision show-me-your-work (TSV).
# Utilisation: log.sh <journal> <phase> <décision> <pourquoi> <preuve> <résultat>
set -euo pipefail

if [ "$#" -ne 6 ]; then
	printf 'utilisation: log.sh <journal> <phase> <décision> <pourquoi> <preuve> <résultat>\n' >&2
	exit 1
fi

logfile="$1"
shift

logdir="$(dirname "$logfile")"
if [ -n "$logdir" ] && [ "$logdir" != "." ] && [ ! -d "$logdir" ]; then
	mkdir -p "$logdir"
fi

cstack_dir="$logdir"
while [ -n "$cstack_dir" ] && [ "$cstack_dir" != "." ] && [ "$cstack_dir" != "/" ]; do
	if [ "${cstack_dir##*/}" = ".cstack" ] && [ -d "$cstack_dir" ] && [ ! -L "$cstack_dir/.gitignore" ] && [ ! -e "$cstack_dir/.gitignore" ]; then
		printf '*\n' > "$cstack_dir/.gitignore"
		break
	fi
	next="${cstack_dir%/*}"
	[ "$next" = "$cstack_dir" ] && break
	cstack_dir="$next"
done
if [ ! -f "$logfile" ]; then
	printf 'ts\tphase\tdecision\twhy\tevidence\tresult\n' > "$logfile"
fi

ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
# Retirer tabulations/nouvelles lignes/CR pour garder les cellules sur une
# seule ligne, et préfixer d’une apostrophe toute cellule dont le premier
# caractère serait interprété par un tableur comme une formule (=, +, -, @).
# La skill prévoit une lecture de ce journal dans des tableurs; les preuves
# contrôlées par un attaquant (titres de PR, noms de fichiers, texte généré)
# ne doivent donc pas devenir une formule exécutée quand un réviseur ouvre le
# fichier.
clean() {
	local v
	v=$(printf '%s' "$1" | tr '\t\n\r' '   ')
	case "$v" in
		=*|+*|-*|@*) printf "'%s" "$v" ;;
		*) printf '%s' "$v" ;;
	esac
}
printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
	"$ts" "$(clean "$1")" "$(clean "$2")" "$(clean "$3")" "$(clean "$4")" "$(clean "$5")" \
	>> "$logfile"

#!/usr/bin/env bash
# Append a well-formed row to a show-me-your-work decision log (TSV).
# Usage: log.sh <logfile> <phase> <decision> <why> <evidence> <result>
set -euo pipefail

if [ "$#" -ne 6 ]; then
	printf 'usage: log.sh <logfile> <phase> <decision> <why> <evidence> <result>\n' >&2
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
# Map C0/DEL, UTF-8 C1 (U+0080-U+009F as C2 80-9F), a lone 0x9B (CSI),
# and U+2028/U+2029 to spaces so cells stay one line. Prefix a cell whose
# first non-space char is =, +, -, or @ so a spreadsheet will not parse it
# as a formula after a leading control has been mapped to a space. Do not
# strip 0x80-0x9F in isolation: those bytes are UTF-8 continuations (Û is
# C3 9B). LC_ALL=C keeps tr and the byte walk byte-oriented.
line_separator=$(printf '\xe2\x80\xa8')
paragraph_separator=$(printf '\xe2\x80\xa9')
clean() {
	local v out i len width byte next tail
	v=$(printf '%s' "$1" | LC_ALL=C tr '[:cntrl:]' ' ')
	local LC_ALL=C LANG=C
	out=
	i=0
	len=${#v}
	while [ "$i" -lt "$len" ]; do
		printf -v byte '%d' "'${v:i:1}"
		[ "$byte" -lt 0 ] && byte=$((byte + 256))
		printf -v next '%d' "'${v:i+1:1}"
		[ "$next" -lt 0 ] && next=$((next + 256))
		width=1
		if [ "$byte" -ge 240 ]; then
			width=4
		elif [ "$byte" -ge 224 ]; then
			width=3
		elif [ "$byte" -ge 194 ]; then
			width=2
		fi
		[ $((i + width)) -gt "$len" ] && width=1
		if [ "$byte" -eq 155 ] ||
			{ [ "$byte" -eq 194 ] && [ "$next" -ge 128 ] && [ "$next" -le 159 ]; } ||
			[ "${v:i:3}" = "$line_separator" ] ||
			[ "${v:i:3}" = "$paragraph_separator" ]; then
			out="$out "
		else
			out="$out${v:i:width}"
		fi
		i=$((i + width))
	done
	tail="${out#"${out%%[! ]*}"}"
	case "$tail" in
		=*|+*|-*|@*) printf "'%s" "$out" ;;
		*) printf '%s' "$out" ;;
	esac
}
printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
	"$ts" "$(clean "$1")" "$(clean "$2")" "$(clean "$3")" "$(clean "$4")" "$(clean "$5")" \
	>> "$logfile"

#! /bin/bash

set -o errexit  # Exit on error, do not continue quietly
exec </dev/null   # Don't hang if a script tries to read from stdin

HERE="$(cd "$(dirname "$0")" && pwd)"
VALIDATE=$HERE/../st-organizers/release-preparation/parseme_validate.py
DIR_CUPT=$HERE/data_reannotation

cd "$HERE"

declare -r LANGS=("AR" "BG" "CS" "DE" "EL" "EN" "ES" "EU" "FA" "FR" "HE" "HI" "HR" "HU" "IT" "LT" "MT" "PL" "PT" "RO" "SL" "SV" "TR" "ZH")

# Same as `echo`, but output in bold
bold_echo() {
    (tput bold; echo "$@"; tput sgr0)
}

###########################################################
# run_devnull <command> [args...]
# Runs command and discards its output.
run_devnull() {
    bold_echo "=> $@" >&2
    "$@" >/dev/null  # Run command and discard output
}

# find all cupt files
cupt_files=$(find "$DIR_CUPT" -type f -name "*.cupt")
# loop through each file
while read -r f; do
    # remove redundant / characters from treebank file path
    f=$(readlink -m -f "$f")
    # validate cupt format
    run_devnull ${VALIDATE} --level 1 "$f"
done <<< "$cupt_files"
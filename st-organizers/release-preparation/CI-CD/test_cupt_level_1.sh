#! /bin/bash

exec </dev/null   # Don't hang if a script tries to read from stdin

HERE="$(cd "$(dirname "$0")" && pwd)"
VALIDATE=$HERE/parseme_validate.py
DIR_CUPT=$HERE/../../
REPO_NAME=$(basename $(readlink -f $DIR_CUPT))
# Extract the part after the last underscore
LANGUAGE="${REPO_NAME##*_}"
LEVEL=1
cd "$HERE"

# Same as `echo`, but output in bold
bold_echo() {
    echo -e "\033[1m$@\033[0m"
}

###########################################################
# run_devnull <command> [args...]
# Runs command and discards its output.
run_devnull() {
    bold_echo "=> $@" >&2
    "$@"
    # "$@" >/dev/null  # Run command and discard output
}

# Define an array to store the exit status of each command
exit_status=()

# find all cupt files
cupt_files=$(find "$DIR_CUPT" -path '*/not_to_release' -prune -o -type f -name "*.cupt" -print)
# loop through each file
while read -r f; do
    # remove redundant / characters from treebank file path
    f=$(readlink -m -f "$f")
    # validate cupt format
    run_devnull ${VALIDATE} --level $LEVEL --lang $LANGUAGE "$f"; exit_status+=($?)
    echo ""
done <<< "$cupt_files"

# Check the exit status of each command
for status in "${exit_status[@]}"; do
    if ((status != 0)); then
        echo -e "\033[31;1m========================================================================================\033[0m"
        echo -e "\033[31;1m=>=>=>One or more files had errors\033[0m"
        echo -e "\033[31;1m========================================================================================\033[0m"
        exit 1
    fi
done

echo -e "\033[32;1m========================================================================================\033[0m"
echo -e "\033[32;1m=>=>=>All files were validated at level $LEVEL\033[0m"
echo -e "\033[32;1m========================================================================================\033[0m"
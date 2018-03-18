#! /bin/bash
set -o errexit  # Exit on error, do not continue quietly
HERE="$(cd "$(dirname "$0")" && pwd)"

set -o nounset    # Using "$UNDEF" var raises error
set -o errexit    # Exit on error, do not continue quietly
exec </dev/null   # Don't hang if a script tries to read from stdin
export IFS=$'\n'  # Do not split variables on " " automatically (only on "\n")

cd "$HERE"

###########################################################


# Same as `echo`, but output in bold
bold_echo() {
    (tput bold; echo "$@"; tput sgr0)
}

# run_devnull <command> [args...]
# Runs command and discards its output.
run_devnull() {
    bold_echo "=> $@"
    "$@" >/dev/null  # Run command and discard output
}


#############################################################
###### Testing if we can run all scripts to completion ######
#############################################################

annot_files=(data/pt.folia.xml data/pt.parsemetsv)
annot_file2=(data/pt2.folia.xml)


for annot_file in "${annot_files[@]}"; do

    #===> pre-annot scripts
    run_devnull ../lang-leaders/pre-annot/checkSentenceMatching.py --lang PT --input "$annot_file"

    #===> post-annot scripts
    run_devnull ../lang-leaders/post-annot/folia2consistencyCheckWebpage.py --lang PT --input "$annot_file"
    run_devnull ../lang-leaders/post-annot/folia2consistencyCheckWebpage.py --lang PT --input "$annot_file" --find-skipped
    run_devnull ../lang-leaders/post-annot/folia2annotatorAdjudicationWebsite.py --lang PT --annotation-1 "$annot_file" --annotation-2 "$annot_file2"
done


#===> check all skipped methods
for skipped_method in Dependency UnlabeledDep BagOfDeps WindowGap5; do
    run_devnull ../lang-leaders/post-annot/folia2consistencyCheckWebpage.py --lang PT --input "${annot_file[0]}" --find-skipped --skipped-finding-method "$skipped_method"
done

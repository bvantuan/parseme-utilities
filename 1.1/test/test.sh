#! /bin/bash
set -o errexit  # Exit on error, do not continue quietly
HERE="$(cd "$(dirname "$0")" && pwd)"

set -o nounset    # Using "$UNDEF" var raises error
set -o errexit    # Exit on error, do not continue quietly
exec </dev/null   # Don't hang if a script tries to read from stdin
export IFS=$'\n'  # Do not split variables on " " automatically (only on "\n")

export LC_ALL=C.UTF-8   # Use a decent locale (and hope it's supported...)

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

    #===> st-organization scripts
    run_devnull ../st-organizers/folia2parsemetsv.py --lang PT --input "$annot_file"
    run_devnull ../st-organizers/folia2parsemetsv.py --lang PT --input "$annot_file" --keep-non-vmwes
    run_devnull ../st-organizers/parsemetsv2cupt.py --input "$annot_file" --artificial
    run_devnull ../st-organizers/parsemetsv2cupt.py --input "$annot_file" --artificial --underspecified-mwes

    #===> corpus-stats scripts
    run_devnull ../st-organizers/corpus-statistics/folia2idiomaticityStats.py --lang PT --input "$annot_file" --literal-finding-method WindowGap0  --out-mweoccurs _deleteme1
    run_devnull rm -rf _deleteme1
done

#===> (scripts that do not accept parsemetsv input...)
for json_file in data/ParsemeNotesCC.json data/ParsemeNotesAdj.json; do
    run_devnull ../lang-leaders/post-annot/jsonNotes2ReannotationWebpage.py --json-input "$json_file"
    run_devnull ../lang-leaders/post-annot/jsonNotes2ReannotationWebpage.py --json-input "$json_file" --xml-input data/pt.folia.xml
    run_devnull ../lang-leaders/post-annot/jsonNotes2ReannotationWebpage.py --json-input "$json_file" --only-special
    run_devnull ../lang-leaders/post-annot/jsonNotes2ReannotationWebpage.py --json-input "$json_file" --xml-input data/pt.folia.xml --generate-xml
    run_devnull rm -r ./AfterAutoUpdate
done

#===> release-preparation scripts (for some reason, does not accept folia xml format... This should be fixed)
run_devnull ../st-organizers/release-preparation/splitTrainTest.py --lang PT --input data/pt.parsemetsv --test-mwesize 15
run_devnull rm -rf OUT


#===> check all skipped methods
for skipped_method in Dependency UnlabeledDep BagOfDeps WindowGap5; do
    run_devnull ../lang-leaders/post-annot/folia2consistencyCheckWebpage.py --lang PT --input data/pt.folia.xml --find-skipped --skipped-finding-method "$skipped_method"
done

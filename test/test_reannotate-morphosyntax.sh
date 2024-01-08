#! /bin/bash

set -o errexit  # Exit on error, do not continue quietly
exec </dev/null   # Don't hang if a script tries to read from stdin

HERE="$(cd "$(dirname "$0")" && pwd)"

cd "$HERE"

#Working directory for the newly annotated files
SUBDIR=not_to_release/$(date +"%Y-%m-%d")-REANNOTATION

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

run_devnull ../lang-leaders/morphosyntax-update/reannotate-morphosyntax.sh --method udtreebank -l EN -s ./data_reannotation/parseme_test_en.cupt -t ./data_reannotation/ud-treebanks-v2.11/UD_English-LinES/ -u http://hdl.handle.net/11234/1-4923
diff ./data_reannotation/parseme_test_en.new.cupt ./data_reannotation/"$SUBDIR"/parseme_test_en.new.cupt 

run_devnull ../lang-leaders/morphosyntax-update/reannotate-morphosyntax.sh --method udtreebank -l EN -s ./data_reannotation/parseme_test2_en.cupt -t ./data_reannotation/ud-treebanks-v2.11/UD_English-LinES/ ./data_reannotation/ud-treebanks-v2.11/UD_English-EWT/ -u http://hdl.handle.net/11234/1-4923 http://hdl.handle.net/11234/1-5150
diff ./data_reannotation/parseme_test2_en.new.cupt ./data_reannotation/"$SUBDIR"/parseme_test2_en.new.cupt 

run_devnull ../lang-leaders/morphosyntax-update/reannotate-morphosyntax.sh --method udtreebank -l EU -s ./data_reannotation/parseme_test_eu.cupt -t ./data_reannotation/ud-treebanks-v2.11/UD_Basque-BDT -u http://hdl.handle.net/11234/1-4923
diff ./data_reannotation/parseme_test_eu.new.cupt ./data_reannotation/"$SUBDIR"/parseme_test_eu.new.cupt

run_devnull ../lang-leaders/morphosyntax-update/reannotate-morphosyntax.sh --method udtreebank -l PL -s ./data_reannotation/parseme_test_pl.cupt -t ./data_reannotation/ud-treebanks-v2.11/UD_Polish-PDB/ -u http://hdl.handle.net/11234/1-4923
diff ./data_reannotation/parseme_test_pl.new.cupt ./data_reannotation/"$SUBDIR"/parseme_test_pl.new.cupt

run_devnull ../lang-leaders/morphosyntax-update/reannotate-morphosyntax.sh --method udtreebank -l AR -s ./data_reannotation/parseme_test_ar.cupt -t ./data_reannotation/ud-treebanks-v2.11/UD_Arabic-PADT/ -u http://hdl.handle.net/11234/1-4923
diff ./data_reannotation/parseme_test_ar.new.cupt ./data_reannotation/"$SUBDIR"/parseme_test_ar.new.cupt

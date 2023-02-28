#! /bin/bash

set -o errexit  # Exit on error, do not continue quietly
exec </dev/null   # Don't hang if a script tries to read from stdin

HERE="$(cd "$(dirname "$0")" && pwd)"

cd "$HERE"

###########################################################
# run_devnull <command> [args...]
# Runs command and discards its output.
run_devnull() {
    bold_echo "=> $@" >&2
    "$@" >/dev/null  # Run command and discard output
}

run_devnull ../st-organizers/release-preparation/reannotate-morphosyntax.sh --method udtreebank -s ./data_reannotation/parseme_test_en.cupt -t ./data_reannotation/ud-treebanks-v2.11/UD_English-LinES/en_lines-ud-train.conllu -u http://hdl.handle.net/11234/1-4923 -p UD_English-LinES/en_lines-ud-train.conllu
diff ./data_reannotation/parseme_test_en.new.cupt ./data_reannotation/REANNOTATION/parseme_test_en.new.cupt

run_devnull ../st-organizers/release-preparation/reannotate-morphosyntax.sh --method udtreebank -s ./data_reannotation/parseme_test_eu.cupt -t ./data_reannotation/ud-treebanks-v2.11/UD_Basque-BDT -u http://hdl.handle.net/11234/1-4923
diff ./data_reannotation/parseme_test_eu.new.cupt ./data_reannotation/REANNOTATION/parseme_test_eu.new.cupt

run_devnull ../st-organizers/release-preparation/reannotate-morphosyntax.sh --method udtreebank -s ./data_reannotation/parseme_test_pl.cupt -t ./data_reannotation/ud-treebanks-v2.11/UD_Polish-PDB/ -u http://hdl.handle.net/11234/1-4923
diff ./data_reannotation/parseme_test_pl.new.cupt ./data_reannotation/REANNOTATION/parseme_test_pl.new.cupt

run_devnull ../st-organizers/release-preparation/reannotate-morphosyntax.sh --method udtreebank -s ./data_reannotation/parseme_test1_pl.cupt -t ./data_reannotation/parseme_test1_pl_pdb-ud.conllu -u http://hdl.handle.net/11234/1-4923 -p UD_Polish-PDB/pl_pdb-ud-dev.conllu
diff ./data_reannotation/parseme_test1_pl.new.cupt ./data_reannotation/REANNOTATION/parseme_test1_pl.new.cupt
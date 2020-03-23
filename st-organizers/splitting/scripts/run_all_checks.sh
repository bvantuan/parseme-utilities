#!/bin/bash


###############################################################
# This script runs all the validation checks on the results
# of the splitting process.
#
# Before you run the script, have a look at the PARAMETERS
# section, in which you may need to specify some paths.
#
# NOTE: before doing all the checks, you may also want to run:
#
#   $ git pull
#
# in each source repository, to make sure they are up-to-date.
###############################################################


###############################################################
# PARAMETERS
###############################################################


# To avoid encoding errors (if you don't need that, just
# comment it out).
export LC_ALL=en_GB.UTF-8


###############################################################
# ARGUMENTS
###############################################################


#Check the number of parameters
if [ ! $# -eq 3 ]; then
  echo Usage: `basename $0` 'LANG-LIST-FILE' 'ORIG-DIR' 'SPLIT-DIR'
  echo
  echo Perform the validation checks w.r.t.:
  echo "* ORIG-DIR: directory with the source corpora (parseme_corpus_fr, parseme_corpus_zh, ...)"
  echo "* SPLIT-DIR: directory with the corpora after splitting (FR, ZH, ...)"
  echo "* LANG-LIST-FILE: a file with the language codes, one per line (fr\n, zh\n, ...)"
  echo
  exit
fi

LANGS=$1
INP=$2
OUT=$3
# Path to the validation script
VALIDATE=$OUT/../bin/validate_cupt.py

###############################################################
# VALIDATION
###############################################################


# # Echo on
# set -x

# # Pull latest versions of all corpora
# apply-all-corpora.sh "git pull"

echo "# Create log folders if not present"
for lang in `cat $LANGS`
do  
  mkdir -p $OUT/${lang^^}/logs/
done

echo "# Calculate splitting stats"
./scripts/stats_all.sh $LANGS $OUT

echo "# Check if datasets identical before and after splitting"
./scripts/check_id.sh $LANGS $INP $OUT

echo "# Check for double annotations"
./scripts/dupl_check_all.sh $LANGS $OUT

echo "# Report double annotations"
# echo "# Double annotations:"
for lang in `cat $LANGS`
do
  echo ${lang^^}
  cat $OUT/${lang^^}/logs/*dupl.log
done

# Run the evaluation script
echo "# Run the evaluation scripts"
./scripts/eval_check_all.sh $LANGS $OUT

# Report warnings in evaluation files
echo "# Report warning in evaluation files"
for lang in `cat $LANGS`
do
  echo ${lang^^}
  cat $OUT/${lang^^}/logs/*eval.log | grep WARNING
done

# Run the validation script
echo "# Run the validation script"
./scripts/validate_all.sh $VALIDATE $LANGS $OUT

# Move to directory with splits
# cd data/preliminary-sharedtask-data

# Inspect all validation logs
echo "# Inspect validator's logs"
cat $OUT/*/logs/*valid* | grep -v "no errors"

# Check for "sent_id"
echo "# Looking for sent_id's"
grep -l "# sent_id =" -R $OUT


###############################################################
# POSTSCRIPT
###############################################################


echo
echo You may also want to manually compare:
echo 
echo "  * evaluation log files in $OUT/*/logs/*-eval.log"
echo "  * splitting stats in $OUT/*/logs/split-stats.log"
echo
echo to identify eventual inconsistencies concerning the reported numbers of
echo unseen MWEs and unseen ratios for the individual echo languages.

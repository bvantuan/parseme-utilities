#!/bin/bash

# Params

UNS_TEST=300
UNS_DEV=100
RND=100

VALIDATE=/home/kuba/work/parseme/gitlab/sharedtask-data-dev/1.2/bin/validate_cupt.py

#Check the number of parameters
if [ ! $# -eq 3 ]; then
  echo Usage: `basename $0` 'LANG-LIST-FILE' 'ST-1.1-DIR' 'OUT-DIR'
  echo
  echo Run the splitting script for each language in PARSEME 1.2.
  echo
  exit
fi

LANGS=$1
INP=$2
OUT=$3

# Echo
set -x

for LANG in `cat $LANGS`
do
  echo $LANG
  INP_DIR=$INP/parseme_corpus_$LANG
  mkdir $OUT/$LANG
  ./split_cupt.py split -i $INP_DIR/*.cupt -n $RND --unseen-test $UNS_TEST --unseen-dev $UNS_DEV --train-path $OUT/$LANG/train.cupt --dev-path $OUT/$LANG/dev.cupt --test-path $OUT/$LANG/test.cupt &> $OUT/$LANG/split.log
  $VALIDATE --input $OUT/$LANG/train.cupt &> $OUT/$LANG/train-validate.log
  $VALIDATE --input $OUT/$LANG/dev.cupt &> $OUT/$LANG/dev-validate.log
  $VALIDATE --input $OUT/$LANG/test.cupt &> $OUT/$LANG/test-validate.log
done

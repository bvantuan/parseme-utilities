#!/bin/bash

# Params
UNS_TEST=300
UNS_DEV=100
RND=100
OPTS="--alt"

#Check the number of parameters
if [ ! $# -eq 3 ]; then
  echo Usage: `basename $0` 'LANG-LIST-FILE' 'ORIG-DIR' 'SPLIT-DIR'
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
  LANG=${LANG^^}
  mkdir -p $OUT/$LANG
  ./split_cupt.py split $OPTS -i $INP_DIR/*.cupt -n $RND --unseen-test $UNS_TEST --unseen-dev $UNS_DEV --train-path $OUT/$LANG/train.cupt --dev-path $OUT/$LANG/dev.cupt --test-path $OUT/$LANG/test.cupt &> $OUT/$LANG/logs/split.log
done

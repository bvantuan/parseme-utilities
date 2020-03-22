#!/bin/bash

# Params

#Check the number of parameters
if [ ! $# -eq 2 ]; then
  echo Usage: `basename $0` 'LANG-LIST-FILE' 'SPLIT-DIR'
  echo
  echo Calculate the stats for all the languages in the list.
  echo
  exit
fi

LANGS=$1
OUT=$2

# Echo
# set -x

for LANG in `cat $LANGS`
do
  OUT_DIR=$OUT/${LANG^^}
  echo ${LANG^^}
  ./split_cupt.py stats --train-path $OUT_DIR/train.cupt --dev-path $OUT_DIR/dev.cupt --test-path $OUT_DIR/test.cupt &> $OUT_DIR/logs/split-stats.log
done

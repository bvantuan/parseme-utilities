#!/bin/bash

# Params

#Check the number of parameters
if [ ! $# -eq 2 ]; then
  echo Usage: `basename $0` 'LANG-LIST-FILE' 'SPLIT-DIR'
  echo
  echo Run evaluation.py script-based tests.
  echo
  exit
fi


LANGS=$1
OUT=$2
EVAL=${OUT}/../bin/evaluate.py

# Echo
# set -x

for LANG in `cat $LANGS`
do
  OUT_DIR=$OUT/${LANG^^}
  echo ${LANG^^}
  $EVAL --train $OUT_DIR/train.cupt --gold $OUT_DIR/test.cupt --pred $OUT_DIR/test.cupt &> $OUT_DIR/logs/test-eval.log
  $EVAL --train $OUT_DIR/train.cupt --gold $OUT_DIR/dev.cupt --pred $OUT_DIR/dev.cupt &> $OUT_DIR/logs/dev-eval.log
  $EVAL --gold $OUT_DIR/train.cupt --pred $OUT_DIR/train.cupt &> $OUT_DIR/logs/train-eval.log
done

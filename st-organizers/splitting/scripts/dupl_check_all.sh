#!/bin/bash

# Params

#Check the number of parameters
if [ ! $# -eq 2 ]; then
  echo Usage: `basename $0` 'LANG-LIST-FILE' 'SPLIT-DIR'
  echo
  echo Check for duplicate annotations.
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
  ./split_cupt.py dupl -i $OUT_DIR/train.cupt &> $OUT_DIR/logs/train-dupl.log
  ./split_cupt.py dupl -i $OUT_DIR/dev.cupt &> $OUT_DIR/logs/dev-dupl.log
  ./split_cupt.py dupl -i $OUT_DIR/test.cupt &> $OUT_DIR/logs/test-dupl.log
done

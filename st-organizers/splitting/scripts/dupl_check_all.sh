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
  ./split_cupt.py dupl -i $OUT_DIR/train.cupt &> $OUT_DIR/train-dupl.log
  ./split_cupt.py dupl -i $OUT_DIR/dev.cupt &> $OUT_DIR/dev-dupl.log
  ./split_cupt.py dupl -i $OUT_DIR/test.cupt &> $OUT_DIR/test-dupl.log
done

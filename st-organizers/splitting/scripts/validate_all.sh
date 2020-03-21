#!/bin/bash

# Params
VALIDATE=/home/kuba/work/parseme/gitlab/sharedtask-data-dev/1.2/bin/validate_cupt.py

#Check the number of parameters
if [ ! $# -eq 2 ]; then
  echo Usage: `basename $0` 'LANG-LIST-FILE' 'SPLIT-DIR'
  echo
  echo Run the splitting script for each language in PARSEME 1.2.
  echo
  exit
fi

LANGS=$1
OUT=$2

# Echo
set -x

for LANG in `cat $LANGS`
do
  echo $LANG
  LANG=${LANG^^}
  $VALIDATE --input $OUT/$LANG/train.cupt &> $OUT/$LANG/train-validate.log
  $VALIDATE --input $OUT/$LANG/dev.cupt &> $OUT/$LANG/dev-validate.log
  $VALIDATE --input $OUT/$LANG/test.cupt &> $OUT/$LANG/test-validate.log
done

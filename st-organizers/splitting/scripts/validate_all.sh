#!/bin/bash

#Check the number of parameters
if [ ! $# -eq 3 ]; then
  echo Usage: `basename $0` 'PATH-TO-VALIDATE_CUPT.PY' 'LANG-LIST-FILE' 'SPLIT-DIR'
  echo
  echo Run the splitting script for each language in PARSEME 1.2.
  echo
  exit
fi

VALIDATE=$1
LANGS=$2
OUT=$3

# # Echo
# set -x

for LANG in `cat $LANGS`
do
  echo $LANG
  LANG=${LANG^^}
  $VALIDATE --input $OUT/$LANG/train.cupt &> $OUT/$LANG/logs/train-validate.log
  $VALIDATE --input $OUT/$LANG/dev.cupt &> $OUT/$LANG/logs/dev-validate.log
  $VALIDATE --input $OUT/$LANG/test.cupt &> $OUT/$LANG/logs/test-validate.log
done

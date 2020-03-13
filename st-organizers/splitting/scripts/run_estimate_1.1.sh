#!/bin/bash

# Params

UNS_TEST=300
UNS_DEV=100
RND=50

#Check the number of parameters
if [ ! $# -eq 2 ]; then
  echo Usage: `basename $0` 'ST-1.1-DIR' 'OUT-DIR'
  echo
  echo Run the estimation script for each language in PARSEME 1.1.
  echo
  exit
fi

OUT=$2

# Echo
set -x

for lang_dir in $1[A-Z][A-Z]
do
  LANG="$(basename -- $lang_dir)"
  mkdir $OUT/$LANG
  # ./split_cupt.py estimate --unseen-mwes 300 -n 50 -i $lang_dir/*[vnt].cupt | tail -n 4
  ./split_cupt.py split -i $lang_dir/*[vnt].cupt -n $RND --unseen-test $UNS_TEST --unseen-dev $UNS_DEV --train-path $OUT/$LANG/train.cupt --dev-path $OUT/$LANG/dev.cupt --test-path $OUT/$LANG/test.cupt
done

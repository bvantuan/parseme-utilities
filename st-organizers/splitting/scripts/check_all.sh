#!/bin/bash

# Params

#Check the number of parameters
if [ ! $# -eq 3 ]; then
  echo Usage: `basename $0` 'LANG-LIST-FILE' 'ORIG-DIR' 'SPLIT-DIR'
  echo
  echo Run checking if datasets identical for each language in the given list.
  echo
  exit
fi

LANGS=$1
INP=$2
OUT=$3

# Echo
# set -x

for LANG in `cat $LANGS`
do
  INP_DIR=$INP/parseme_corpus_$LANG
  OUT_DIR=$OUT/$LANG
  echo ${LANG^^}: `./split_cupt.py check -o $INP_DIR/*.cupt -s $OUT_DIR/*.cupt | tail -n 1`
done

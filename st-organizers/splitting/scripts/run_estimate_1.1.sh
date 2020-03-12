#!/bin/bash

#Check the number of parameters
if [ ! $# -eq 1 ]; then
  echo Usage: `basename $0` 'ST-1.1-DIR'
  echo
  echo Run the estimation script for each language in PARSEME 1.1.
  echo
  exit
fi

# Echo
set -x

for lang_dir in $1/[A-Z][A-Z]
do
  ./split_cupt.py estimate --unseen-mwes 300 -n 50 -i $lang_dir/*[vnt].cupt | tail -n 4
done

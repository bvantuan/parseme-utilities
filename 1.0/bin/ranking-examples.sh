#!/bin/bash

for l in BG CS DE EL EN ES FA FR HE HR HU IT LT MT PL PT RO SE SL TR YI; do
  printf "%s -> " $l
  grep "	$l	[^	]" ../guidelines-hypertext/examples-full.tsv | wc -l
done |
sort -k 3,3 -nr

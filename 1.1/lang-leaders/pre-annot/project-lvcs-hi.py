#!/usr/bin/env python3

import sys
import collections
import pdb

PARSEMETSV = sys.argv[1]
CONLLU = sys.argv[2]
sentence=collections.OrderedDict()

with open(PARSEMETSV) as parsemetsv, open(CONLLU) as conllu: 
  for parsemetsv_line, conllu_line in zip(parsemetsv, conllu):
    if conllu_line.startswith("#") :
      print(conllu_line,end="")
    elif not conllu_line.strip():
      mwe_count=1
      for (word_id,word) in sentence.items():
        if word[6] == 'compound' and sentence[word[5]][4] == "V":
           w1_id = min(word_id,word[5])
           w2_id = max(word_id,word[5])
           for w_id in w1_id, w2_id:  # if there is no MWE annot on the word
             if sentence[w_id][3] == "_":
               sentence[w_id][3] = ""     # replace underscore by ""
           # append new MWE annotation to third column
           # append instead of replace to avoid overwriting tokens that belong
           # to more than 1 MWE
           sentence[w1_id][3] += str(mwe_count) 
           sentence[w2_id][3] += str(mwe_count) 
           sentence[str(min(int(w1_id),int(w2_id)))][3] += ":LVC.full" # first word has categ.     
           mwe_count += 1 
      for word in sentence.values():
        print("\t".join(word[:5]))
      print(conllu_line.strip())
      sentence=collections.OrderedDict()
    else:
      word = parsemetsv_line.strip().split("\t") + \
             conllu_line.strip().split("\t")[6:8]
      word_id=word[0][1:]
      sentence[word_id]= word



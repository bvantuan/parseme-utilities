#! /usr/bin/env python3

import argparse
import collections
import json
import pdb

import os, sys, math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../lib"))
import dataalign


parser = argparse.ArgumentParser(description="""
    Read input files and generate stats (in nb. of tokens) for MWE length, 
    MWE distance between first and last token, and MWE number of gaps. With
    --verbose, also lists individual MWEs and their stats (length, distance, 
    gaps)
    """)
    
parser.add_argument("--lang", choices=sorted(dataalign.LANGS), metavar="LANG", required=True,
    help="""ID of the target language (e.g. EN, FR, PL, DE...)""")
parser.add_argument("--filter-categs", type=str, default=None,
    help="""Only extract VMWEs with category labels in comma-separated list""")
parser.add_argument("--filter-lemmas", type=str, default=None,
    help="""Only extract VMWEs containing *all* lemmas in comma-separated list""")
parser.add_argument("--input", type=str, nargs="+", required=True,
    help="""Path to input files (cupt or parsemetsv), with annotated VMWEs""")
parser.add_argument("--conllu", type=str, nargs="+",
    help="""Path to parallel input CoNLL files (if input not in cupt)""")
parser.add_argument("--verbose", action="store_true",
    help="""Output all instances of VMWEs separately, with their stats.""")    
parser.add_argument("--threshold", type=int, default=3,
    help="""Theshold value after histogram points are cumulated (default: 3).""")    
    
    

#####################################################

class Main:
  def __init__(self, args):
    self.args = args
    # type: canonicized_tuple -> [MWEOccur]
    self.canonic2occurs = collections.defaultdict(list)
    self.categs = [] if self.args.filter_categs is None else self.args.filter_categs.split(",")
    self.verbose = self.args.verbose
    self.thresh = self.args.threshold # Threshold after which we want to cumulate stats (shown as extra point)
    if self.categs :
      print("INFO: extraction limited to categories: {}".format(self.categs),file=sys.stderr)
    self.lemmas = [] if self.args.filter_lemmas is None else self.args.filter_lemmas.split(",")
    if self.lemmas :
      print("INFO: extraction limited to VMWEs containing all lemmas: {}".format(self.lemmas),file=sys.stderr)    
    if self.verbose :
      print("INFO: verbose mode, showing stats for all VMWEs separately",file=sys.stderr)    

#####################################################

  def run(self):
    # length: distribution of VMWE length (i.e. nb of lexicalized components)
    # dist: distribution of VMWE distance (i.e. difference between positions of last--first lexicalized components)    
    # gaps: distribution of VMWE gap length (i.e. nb of non-lexicalized components between first/last lexicalized ones)
    distr = {"length":{},"dist":{},"gaps":{}}
    stat = {}
    vmwe_total = 0
    dummykey = self.thresh * 10000
    for sentence in self.iter_sentences():
      for mwe_occur in sentence.mweoccurs: 
        if ( not self.categs or mwe_occur.category in self.categs ) and\
           ( not self.lemmas or set(self.lemmas) <= set(mwe_occur.fixed.likely_lemmatizedform) ) :
          stat["length"] = len(mwe_occur.indexes)
          stat["dist"] = mwe_occur.indexes[-1] - mwe_occur.indexes[0] 
          stat["gaps"] = stat["dist"] + 1 - stat["length"]
          for statkey in distr.keys():
            distr[statkey][stat[statkey]] = distr[statkey].setdefault(stat[statkey],0)+1
            if stat[statkey] >= self.thresh:
              distr[statkey][dummykey] = distr[statkey].setdefault(dummykey,0)+1
          vmwe_total += 1
          if self.verbose:
            # Sequence of tokens including non-lexicalized ones, with
            # lexicalized ones in brackets [token]
            form = "_".join("[{}]".format(sentence.tokens[i]["FORM"]) \
                            if i in mwe_occur.indexes \
                            else sentence.tokens[i]["FORM"] \
                              for i in range(mwe_occur.indexes[0],
                                             mwe_occur.indexes[-1]+1))
            print("length={:02} distance={:02} gaps={:02} category={:10} normalized={:20} form={}".format(                  
                  stat["length"], stat["dist"], stat["gaps"], mwe_occur.category,
                  "_".join(mwe_occur.reordered.likely_lemmatizedform),
                  form))
          
    print("Total number of VMWEs: {}".format(vmwe_total))
    for statkey in ["length","dist","gaps"] :      
      print("\n### VMWE {} (nb. of lexicalized components):".format(statkey))
      print("\n".join(["  * {}: {} ({:.2f}%)".format(i if i != dummykey else "≥{}".format(self.thresh),
                                                     distr[statkey][i],
                                                     100*distr[statkey][i]/vmwe_total) for i in sorted(distr[statkey].keys())]
                     )
           )
      distr[statkey].pop(dummykey,None) # Remove cumulated dummy point, so that it does not cound in the average
      average = sum(map(lambda i: i[0]*i[1], distr[statkey].items()))/vmwe_total
      stddev = math.sqrt((sum(map(lambda i: i[0]*i[0]*i[1], distr[statkey].items()))/(vmwe_total)-average*average))
      print("> Average {}: {:.2f}".format(statkey, average))
      print("> Stddev {}: {:.2f}".format(statkey, stddev))      


#####################################################

  def iter_sentences(self, verbose=True):
    r"""Yield all sentences in `self.args.input` (aligned, if CoNLL-U was provided)"""
    conllu_paths = self.args.conllu or dataalign.calculate_conllu_paths(self.args.input, warn=verbose)
    return dataalign.IterAlignedFiles(self.args.lang, self.args.input, conllu_paths, keep_nvmwes=True, debug=verbose)

#####################################################

if __name__ == "__main__":
  Main(parser.parse_args()).run()

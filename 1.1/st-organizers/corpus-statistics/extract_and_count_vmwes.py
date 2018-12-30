#! /usr/bin/env python3

import argparse
import collections
import json
import pdb

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../lib"))
import dataalign


parser = argparse.ArgumentParser(description="""
    Read input files and generate a list of VMWEs ranked by frequency. 
    Filters can be passed as command line options to only extract some
    categories or some head verb lemmas.
    """)
    
parser.add_argument("--lang", choices=sorted(dataalign.LANGS), metavar="LANG", required=True,
    help="""ID of the target language (e.g. EN, FR, PL, DE...)""")
parser.add_argument("--filter-categs", type=str, default=None,
    help="""Only extract VMWEs with category labels in comma-separated list""")
parser.add_argument("--filter-lemmas", type=str, default=None,
    help="""Only extract VMWEs containing *all* lemmas in comma-separated list""")
parser.add_argument("--parsemetsv", type=str, nargs="+", required=True,
    help="""Path to input files in PARSEME TSV with annotated VMWEs""")
parser.add_argument("--no-reorder", action="store_true",
    help="""Do not reorder VMWE components to be in canonical order""")    
parser.add_argument("--canonical", action="store_true",
    help="""Do not lemmatize, use canonical form instead (only some lemmatized components)""")    
parser.add_argument("--sentences", action="store_true",
    help="""Show list occurrence sentences after each VMWE""")
parser.add_argument("--conllu", type=str, nargs="+",
    help="""Path to parallel input CoNLL files""")

#####################################################

class Main:
  def __init__(self, args):
    self.args = args
    # type: canonicized_tuple -> [MWEOccur]
    self.canonic2occurs = collections.defaultdict(list)
    self.categs = [] if self.args.filter_categs is None else self.args.filter_categs.split(",")
    if self.categs :
      print("INFO: extraction limited to categories: {}".format(self.categs),file=sys.stderr)
    self.lemmas = [] if self.args.filter_lemmas is None else self.args.filter_lemmas.split(",")
    if self.lemmas :
      print("INFO: extraction limited to VMWEs containing all lemmas: {}".format(self.lemmas),file=sys.stderr)    

#####################################################

  def run(self):
    for sentence in self.iter_sentences():
      for mwe_occur in sentence.mwe_occurs(self.args.lang): 
        if ( not self.categs or mwe_occur.category in self.categs ) : 
          order = mwe_occur.fixed if self.args.no_reorder else mwe_occur.reordered
          # test if filtering lemmas contained in VMWE lemmas
          if ( not self.lemmas or set(self.lemmas) <= set(order.likely_lemmatizedform) ) : 
            inflect = order.likely_canonicform if self.args.canonical else order.likely_lemmatizedform
            self.canonic2occurs[tuple(inflect)].append(mwe_occur)
    for canonic, mwe_occurs in self.canonic2occurs.items():
      categs = set(map(lambda x:x.category,mwe_occurs))
      print("{}: {} ({})".format(",".join(categs), "_".join(canonic), len(mwe_occurs)))
      if self.args.sentences :
        for occur in mwe_occurs :
          print("  * {}: {}".format(occur.sentence.nth_sent,str(occur.sentence)))
        print()


#####################################################

  def iter_sentences(self, verbose=True):
    r"""Yield all sentences in `self.args.parsemetsv` (aligned, if CoNLL-U was provided)"""
    conllu_paths = self.args.conllu or dataalign.calculate_conllu_paths(self.args.parsemetsv, warn=verbose)
    for elem in dataalign.IterAlignedFiles(self.args.lang, self.args.parsemetsv, conllu_paths, keep_nvmwes=True, debug=verbose):
      if isinstance(elem, dataalign.Sentence):
        yield elem

#####################################################

if __name__ == "__main__":
  Main(parser.parse_args()).run()

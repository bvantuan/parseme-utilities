#!/usr/bin/env python3



import os, sys, argparse, pdb
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../lib/"))
import dataalign

parser = argparse.ArgumentParser(description="""
  This script reads a cupt file and projects all VMWE annotations
  present on multiword tokens (ranges) onto the corresponding words
  covered by the range. The VMWE annotation is not present on the 
  multiword token.
""")
    
parser.add_argument("--cupt", type=str, nargs="+", required=True,
    help="""Path to input CUPT files with annotated VMWEs""")
parser.add_argument("--lang", type=str, required=True,
    help="""Language of the input corpus""")


#####################################################

class Main:
  def __init__(self, args):
    self.args = args        

#####################################################

  def run(self):
    out_sents = []     
    for sentence in self.iter_sentences():
      sentence.mweoccurs = [m.with_mwes_from_ranges_absorbed_into_tokens() for m in sentence.mweoccurs]
      out_sents.append(sentence)        
    dataalign.ConllupWriter().write_sentences(out_sents)

#####################################################

  def iter_sentences(self, verbose=True):
    r"""Yield all sentences in `self.args.cupt`"""    
    for elem in dataalign.IterAlignedFiles(self.args.lang, self.args.cupt, None, keep_nvmwes=True, debug=verbose):
      if isinstance(elem, dataalign.Sentence):
        yield elem

#####################################################

if __name__ == "__main__":
  Main(parser.parse_args()).run()

        

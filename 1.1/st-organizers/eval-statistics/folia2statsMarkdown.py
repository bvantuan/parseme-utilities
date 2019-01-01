#! /usr/bin/env python3

import argparse
import collections

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../lib"))
import dataalign

parser = argparse.ArgumentParser(description="""
        Count interesting information for FoLiA input file (used to generate stats.md).""")
parser.add_argument("--lang", choices=sorted(dataalign.LANGS), metavar="LANG", required=True,
        help="""Name of the target language (e.g. EN, FR, PL, DE...)""")
parser.add_argument("--input", type=str, nargs="+", required=True,
        help="""Path to input files (in FoLiA XML or PARSEME TSV format)""")
parser.add_argument("--conllu", type=str, nargs="+",
        help="""Path to parallel input CoNLL files""")


class Main:
    def __init__(self, args):
        self.args = args
        self.sents = 0
        self.tokens = 0
        self.counter = collections.Counter()

    def run(self):
        self.conllu_paths = self.args.conllu \
                or dataalign.calculate_conllu_paths(self.args.input, warn=False)
        for sentence in dataalign.IterAlignedFiles(self.args.lang,
                self.args.input, self.conllu_paths, keep_nvmwes=False, debug=False):
            for mweoccur in sentence.mweoccurs:
                self.counter[mweoccur.category] += 1
            self.sents += 1
            self.tokens += len(sentence.tokens)
        #print("### {}".format(" ".join(self.args.input)))
        print("* Sentences: {}".format(self.sents))
        print("* Tokens: {}".format(self.tokens))
        print("* Total VMWEs: {}".format(sum(self.counter.values())))        
        for name, count in sorted(self.counter.items()):
            print("  * `{}`: {}".format(name, count))



#####################################################

if __name__ == "__main__":
    Main(parser.parse_args()).run()

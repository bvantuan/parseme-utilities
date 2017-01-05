#! /usr/bin/env python3

import argparse
import collections

import dataalign

parser = argparse.ArgumentParser(description="""
        Count interesting information for FoLiA input file.""")
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
        for elem in dataalign.iter_aligned_files(self.args.input, self.conllu_paths,
                keep_nvmwes=False, debug=False):
            for mweannot in elem.mweannots:
                self.counter[mweannot.category] += 1
            self.sents += 1
            self.tokens += len(elem.tokens)

        for name, count in sorted(self.counter.items()):
            print("  * `{}`: {}".format(name, count))
        print("  * **TOTAL**: {}".format(sum(self.counter.values())))
        print("  * Sentences: {}".format(self.sents))
        print("  * Tokens: {}".format(self.tokens))


#####################################################

if __name__ == "__main__":
    Main(parser.parse_args()).run()

#! /usr/bin/env python3

import argparse

import os, sys
sys.path.insert(0, os.path.dirname(__file__)+"/../../lib")
import dataalign

parser = argparse.ArgumentParser(description="""
        Check if every sentence in PARSEME-TSV has a matching sentence in CoNLL-U.""")
parser.add_argument("--lang", choices=sorted(dataalign.LANGS), metavar="LANG", required=True,
        help="""Name of the target language (e.g. EN, FR, PL, DE...)""")
parser.add_argument("--input", type=str, nargs="+", required=True,
        help="""Path to input files (in FoLiA XML or PARSEME TSV format)""")
parser.add_argument("--conllu", type=str, nargs="+",
        help="""Path to parallel input CoNLL files""")


class Main:
    def __init__(self, args):
        self.args = args

    def run(self):
        self.conllu_paths = self.args.conllu or dataalign.calculate_conllu_paths(self.args.input)
        if not self.conllu_paths:
            exit("ERROR: You must specify CoNLL-U files to be checked against PARSEME-TSV")

        aligned = dataalign.AlignedIterator.from_paths(self.args.input, self.conllu_paths)
        sent_aligner = dataalign.SentenceAligner(aligned.main, aligned.conllu)

        print("-"*40)
        print("INFO: TSV data contains {} sentences".format(len(sent_aligner.main_sentences)))
        print("INFO: CoNLL-U data contains {} sentences".format(len(sent_aligner.conllu_sentences)))
        print("-"*40)

        sent_aligner.print_mismatches()


#####################################################

if __name__ == "__main__":
    Main(parser.parse_args()).run()

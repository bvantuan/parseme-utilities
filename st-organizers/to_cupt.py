#! /usr/bin/env python3

import argparse
import io
import sys
import subprocess

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../lib"))
import dataalign

parser = argparse.ArgumentParser(description="""
        Convert input file(s) to CoNLL-UP format
        (also aligns with CoNLL-U files, if available).""")
parser.add_argument("--debug", action="store_true",
        help="""Print extra debug information in stderr""")
parser.add_argument("--lang", choices=sorted(dataalign.LANGS), metavar="LANG", required=True,
        help="""Name of the target language (e.g. EN, FR, PL, DE...)""")
parser.add_argument("--discard-non-mwes", action="store_true",
        help="""Discard NonMWE entries in the output""")
parser.add_argument("--keepranges", action="store_true",
        help="""Keep MWE annotations on multiword tokens (ranges), e.g. contractions""")        
parser.add_argument("--colnames", nargs="+",
        help="""Column names in the order they should appear in the output CoNLL-UP""")
parser.add_argument("--input", type=str, nargs="+", required=True,
        help="""Path to input files (in FoLiA-XML/PARSEME-TSV/CUPT/CoNLL-UP format)""")
parser.add_argument("--conllu", type=str, nargs="+",
        help="""Path to parallel input CoNLL files""")


class Main:
    def __init__(self, args):
        self.args = args
        self.counter = {}

    def run(self):
        self.conllu_paths = self.args.conllu or dataalign.calculate_conllu_paths(self.args.input, False)
        iaf = dataalign.IterAlignedFiles(
            self.args.lang, self.args.input, self.conllu_paths,
            keep_nvmwes=(not self.args.discard_non_mwes), debug=self.args.debug)

        colnames = self.args.colnames or iaf.aligned_iterator.main_iterators[0].corpusinfo.colnames
        dataalign.ConllupWriter(colnames=colnames,keepranges=self.args.keepranges).write_sentences(iaf)


#####################################################

if __name__ == "__main__":
    Main(parser.parse_args()).run()

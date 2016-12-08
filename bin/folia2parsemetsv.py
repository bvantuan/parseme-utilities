#! /usr/bin/env python3

import argparse
import sys
import dataalign

parser = argparse.ArgumentParser(description="""
        Convert input file format to PARSEME TSV.""")
parser.add_argument("--debug", action="store_true",
        help="""Print extra debug information in stderr""")
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
        conllu_path = self.args.conllu or dataalign.calculate_conllu_paths(self.args.input)
        for elem in dataalign.iter_aligned_files(self.args.input, conllu_path, debug=self.args.debug):
            if isinstance(elem, dataalign.Comment):
                print("#", elem.text)
            else:
                for word in elem.tokens:
                    surface_form = word.surface or dataalign.EMPTY
                    nsp = "nsp" if word.nsp else dataalign.EMPTY
                    mwe_ids = ";".join(word.mwe_codes) or dataalign.EMPTY
                    print(word.rank, surface_form, nsp, mwe_ids, sep="\t")
                print()


#####################################################

if __name__ == "__main__":
    Main(parser.parse_args()).run()

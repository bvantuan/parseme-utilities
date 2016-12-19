#! /usr/bin/env python3

import argparse
import io
import sys
import subprocess

import dataalign

parser = argparse.ArgumentParser(description="""
        Split input files into OUT/{train,test}.{parsemetsv,conllu}.""")
parser.add_argument("--lang", choices=sorted(dataalign.LANGS), metavar="LANG", required=True,
        help="""Name of the target language (e.g. EN, FR, PL, DE...)""")
parser.add_argument("--test-mwesize", type=int, default=500,
        help="""Number of MWEs to leave in test files""")
parser.add_argument("--input", type=str, required=True,
        help="""Path to input files (in FoLiA XML or PARSEME TSV format)""")
parser.add_argument("--conllu", type=str,
        help="""Path to parallel input CoNLL files""")


class Main:
    def __init__(self, args):
        self.args = args

    def run(self):
        subprocess.check_call("mkdir -p ./OUT", shell=True)
        self.iter_conllu = open(self.args.conllu) if self.args.conllu else None
        self.tsv_output = open("./OUT/test.parsemetsv", "w+")
        self.conllu_output = open("./OUT/test.conllu", "w+") if self.iter_conllu else None

        mwe_count = 0
        doing_test = True
        with open(self.args.input) as tsv_file:
            for tsv_line in tsv_file:
                tsv_fields = tsv_line.strip().split("\t")
                conllu_line = next(self.iter_conllu) if self.iter_conllu else None

                print(tsv_line, end="", file=self.tsv_output)
                if conllu_line: print(conllu_line, end="", file=self.conllu_output)

                if doing_test:
                    if not tsv_line.strip() and mwe_count >= self.args.test_mwesize:
                        self.tsv_output.close()
                        if self.conllu_output: self.conllu_output.close()
                        self.tsv_output = open("./OUT/train.parsemetsv", "w+")
                        self.conllu_output = open("./OUT/train.conllu", "w+") if self.iter_conllu else None
                        self.stats(mwe_count, doing_test)
                        mwe_count = 0
                        doing_test = False

                if ":" in tsv_fields[-1]:
                    mwe_count += sum((":" in x) for x in tsv_fields[-1].split(";"))
        self.stats(mwe_count, doing_test)

    def stats(self, mwe_count, doing_test):
        print("STATS:", "OUT/"+ ("test.*" if doing_test else "train.*"),
                "with {} MWEs".format(mwe_count), file=sys.stderr)


#####################################################

if __name__ == "__main__":
    Main(parser.parse_args()).run()

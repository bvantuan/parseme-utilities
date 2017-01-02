#! /usr/bin/env python3

import argparse
import sys
import subprocess

import dataalign

parser = argparse.ArgumentParser(description="""
        Split input files into OUT/{train,gold}.{parsemetsv,conllu}.""")
parser.add_argument("--lang", choices=sorted(dataalign.LANGS), metavar="LANG", required=True,
        help="""Name of the target language (e.g. EN, FR, PL, DE...)""")
parser.add_argument("--gold-first-sentence", type=int, default=1,
        help="""Desired first sentence to use as blind & gold data (default: sentence 1)""")
parser.add_argument("--gold-mwesize", type=int, default=500,
        help="""Desired number of MWEs in blind & gold data""")
parser.add_argument("--input", type=str, required=True,
        help="""Path to input files (in FoLiA XML or PARSEME TSV format)""")
parser.add_argument("--conllu", type=str,
        help="""Path to parallel input CoNLL files""")


class Main:
    def __init__(self, args):
        self.args = args

    def run(self):
        info_train, info_gold = self.split_train_gold()
        subprocess.check_call("mkdir -p ./OUT", shell=True)
        for name, info in (("gold", info_gold), ("train", info_train)):
            self.process_fileinfo(name, info)

    def process_fileinfo(self, name, info):
        r"""Example: process_fileinfo("train", FileInfo(...))"""
        self.generate_file(name, "parsemetsv", info.tsv_lines)
        if info.conllu_lines:
            self.generate_file(name, "conllu", info.conllu_lines)
        self.stats(info.mwecount, (name == "gold"))

    def generate_file(self, name, ext, lines):
        with open("./OUT/{}.{}".format(name, ext), "w+") as output:
            for line in lines:
                print(line, end="", file=output)


    def stats(self, mwe_count, doing_gold):
        print("STATS:", "OUT/"+ ("gold.*" if doing_gold else "train.*"), file=sys.stderr)
        total = 0
        for mwetype,count in sorted(mwe_count.items()) :
            if mwetype != "TOTAL" :
                print("  * {}: {}".format(mwetype,count), file=sys.stderr)
        print("  * **TOTAL: {} VMWEs**".format(mwe_count["TOTAL"]), file=sys.stderr)


    def split_train_gold(self):
        r"""Return a pair (train: FileInfo, gold: FileInfo)"""
        info_train, info_gold = FileInfo(), FileInfo()
        info = info_train

        for sent_id, (tsv, conllu) in enumerate(self.iter_sentences(), 1):
            if sent_id == self.args.gold_first_sentence:
                info = info_gold
            if info.mwecount["TOTAL"] >= self.args.gold_mwesize:
                info = info_train

            info.tsv_lines.extend(tsv)
            info.conllu_lines.extend(conllu)

            for tsv_line in tsv:
                for x in tsv_line.strip().split("\t")[-1].split(";") :
                    if ":" in x :
                        mweid,mwetype = x.split(":")
                        info.mwecount[mwetype] = info.mwecount.get(mwetype,0) + 1
                        info.mwecount["TOTAL"] += 1
        return info_train, info_gold


    def iter_sentences(self):
        r"""Yield pairs (tsv: List[str], conllu: List[str])."""
        tsv, conllu = [], []
        iter_conllu = open(self.args.conllu) if self.args.conllu else None
        with open(self.args.input) as iter_parsemetsv:
            for tsv_line in iter_parsemetsv:
                tsv.append(tsv_line)
                if iter_conllu:
                    conllu.append(next(iter_conllu))

                if not tsv_line.strip():
                    yield tsv, conllu
                    tsv, conllu = [], []
        if tsv:
            yield tsv, conllu


class FileInfo:
    r"""Mutable namedtuple (tsv_lines, conllu_lines, mwecount)."""
    def __init__(self):
        self.tsv_lines = []
        self.conllu_lines = []
        self.mwecount = {"TOTAL":0}


#####################################################

if __name__ == "__main__":
    Main(parser.parse_args()).run()

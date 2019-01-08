#! /usr/bin/env python3

import argparse
import io
import sys
import subprocess

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../lib"))
import dataalign

parser = argparse.ArgumentParser(description="""
        Convert input file format to PARSEME TSV
        (also aligns with CoNLL-U files, if available).""")
parser.add_argument("--debug", action="store_true",
        help="""Print extra debug information in stderr""")
parser.add_argument("--tgz", action="store_true",
        help="""Generate a DATA.tgz file (to be sent to the SharedTask leaders)""")
parser.add_argument("--lang", choices=sorted(dataalign.LANGS), metavar="LANG", required=True,
        help="""Name of the target language (e.g. EN, FR, PL, DE...)""")
parser.add_argument("--keep-non-vmwes", action="store_true",
        help="""Keep NonVMWE entries in the output (by default, they are removed)""")
parser.add_argument("--input", type=str, nargs="+", required=True,
        help="""Path to input files (in FoLiA XML or PARSEME TSV format)""")
parser.add_argument("--conllu", type=str, nargs="+",
        help="""Path to parallel input CoNLL files""")


class Main:
    def __init__(self, args):
        self.args = args
        self.counter = {}

    def run(self):
        self.tgz_begin()
        self.conllu_paths = self.args.conllu or dataalign.calculate_conllu_paths(self.args.input)
        for sentence in dataalign.IterAlignedFiles(self.args.lang, self.args.input, self.conllu_paths,
                keep_nvmwes=self.args.keep_non_vmwes, debug=self.args.debug):
            for kv_pair in sentence.kv_pairs:
                print(kv_pair.to_tsv())
            for token, mwecodes in sentence.tokens_and_mwecodes():
                surface_form = token.surface or dataalign.EMPTY
                nsp = "nsp" if token.nsp else dataalign.EMPTY
                mwe_ids = ";".join(mwecodes) or dataalign.EMPTY
                self.counter_increment(mwecodes)
                print(token.rank, surface_form, nsp, mwe_ids, sep="\t")
            print()
        self.counter_print()
        self.tgz_end()

    def counter_increment(self,mwecodes):
        for mwecode in mwecodes:
            if ":" in mwecode:
                mweid,mwetype = mwecode.split(":")
                if mwetype not in self.counter.keys():
                    self.counter[mwetype] = 1
                else:
                    self.counter[mwetype] += 1
                    
    def counter_print(self):
        total = 0
        for k,v in self.counter.items():
            print("  * `{}`: {}".format(k,v),file=sys.stderr)
            total += v
        print("  * **Total**: {} VMWEs".format(total),file=sys.stderr)
        
    def tgz_begin(self):
        if self.args.tgz:
            shell("rm -rf /tmp/parsemetgz")
            shell("mkdir -p /tmp/parsemetgz")
            sys.stdout = open("/tmp/parsemetgz/data.parsemetsv", "w+")
            sys.stderr = Tee(sys.stderr, open("/tmp/parsemetgz/STDERR", "w+"))

    def tgz_end(self):
        if self.args.tgz:
            from pipes import quote
            sys.stdin.close()
            sys.stdout.close()
            if self.conllu_paths:
                shell("cat {} >/tmp/parsemetgz/data.conllu"
                        .format(" ".join(quote(c) for c in self.conllu_paths)))
            with open("/tmp/parsemetgz/CMDLINE", "w+") as f:
                print("NAMESPACE:", self.args, file=f)
                print("CMDLINE:", sys.argv, file=f)
                print("CONLLU:", self.conllu_paths, file=f)
            shell("tar -zcf ./DATA.tgz -C /tmp parsemetgz")


def shell(cmd):
    subprocess.check_call(cmd, shell=True)


class Tee(io.TextIOWrapper):
    r"""Same as a unix `tee`"""
    def __init__(self, main_fileobj, other_fileobj):
        self.fileobjs = [main_fileobj, other_fileobj]
        super().__init__(main_fileobj)

    def write(self, data):
        for fileobj in self.fileobjs:
            fileobj.write(data)
            fileobj.flush()


#####################################################

if __name__ == "__main__":
    Main(parser.parse_args()).run()

#! /usr/bin/env python3

import argparse
import collections

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../lib"))
import dataalign


parser = argparse.ArgumentParser(description="""
        List MWE occurrences in the output.
        Useful e.g. to find examples of MWEs in context.
        You should pipe the output through `less -SR`.
        """)
parser.add_argument("--lang", choices=sorted(dataalign.LANGS), metavar="LANG", required=True,
        help="""ID of the target language (e.g. EN, FR, PL, DE...)""")
parser.add_argument("--input", type=str, nargs="+", required=True, metavar='PATH',
        help="""Path to input files (in CUPT, PARSEME-TSV or FoLiA XML format)""")



class Main:
    def __init__(self, args):
        self.args = args

    def run(self):
        try:
            self.do_run()
        except KeyboardInterrupt as e:
            exit(0)  # Quit on keyboard interrupt
        except IOError as e:
            import errno
            if e.errno == errno.EPIPE:
                exit(0)  # Ignore broken pipes
            raise

    def do_run(self):
        for sentence in dataalign.IterAlignedFiles(self.args.lang, self.args.input, None):
            for mweoccur in sentence.mweoccurs:
                self.print_entry(sentence, mweoccur)

    def print_entry(self, sentence: dataalign.Sentence, mweoccur: dataalign.MWEOccur):
        mwe_indexes = set(mweoccur.indexes)
        mwe_text = " ".join(sentence.tokens[i]['FORM'] for i in mweoccur.indexes)
        sent_text = " ".join(self.color(t, (i in mwe_indexes))
                             for i, t in enumerate(sentence.tokens))
        print("{:<10s} | \x1b[38;5;208m{:<20s}\x1b[m | {}".format(
            mweoccur.category, mwe_text.lower(), sent_text))


    def color(self, token: dataalign.Token, in_mwe: bool):
        text = token['FORM']
        return "\x1b[7m{}\x1b[m".format(text) if in_mwe else text



#####################################################

if __name__ == "__main__":
    Main(parser.parse_args()).run()

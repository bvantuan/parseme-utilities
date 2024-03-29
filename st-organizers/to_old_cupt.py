#! /usr/bin/env python3

import argparse
import io
import re
import sys
import subprocess

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../lib"))
import dataalign

RE_SENT_ID = re.compile('^ *(source_)?sent_id *= *(.*)')
UD_COLS = dataalign.ConlluIterator.UD_KEYS


parser = argparse.ArgumentParser(description="""
        Convert input file format from PARSEME-TSV (edition 1.0)
        to the UD-PARSEME-TSV format (edition 1.1).""")
parser.add_argument("--lang", choices=sorted(dataalign.LANGS), metavar="LANG", required=True,
        help="""Name of the target language (e.g. EN, FR, PL, DE...)""")
parser.add_argument("--underspecified-mwes", action='store_true',
        help="""If set, represent empty PARSEME:MWE slots as "_" instead of "*".""")
parser.add_argument("--gen-text", action='store_true',
        help="""If set, automatically create missing 'text' metadata for each sentence.""")
parser.add_argument("--gen-sentid", action='store_true',
        help="""If set, automatically create missing 'sent_id' metadata for each sentence.""")
        # (SC: Gen-text/sentid is not done by default, because some people will actually have some metadata,
        # but in a weird format, so I think it's better to point it out with an error, at first).
parser.add_argument("--input", type=str, nargs="+", required=True,
        help="""Path to input files (in FoLiA XML or PARSEME TSV format)""")
parser.add_argument("--conllu", type=str, nargs="+",
        help="""Path to parallel input CoNLL files""")


class Main:
    def __init__(self, args):
        self.args = args

    def run(self):
        missing_mwe_annot = "_" if self.args.underspecified_mwes else "*"
        self.conllu_paths = self.args.conllu or dataalign.calculate_conllu_paths(self.args.input)
        print('# global.columns =', ' '.join(UD_COLS + ['PARSEME:MWE']))

        for sentence in dataalign.IterAlignedFiles(
                self.args.lang, self.args.input, self.conllu_paths,
                default_mwe_category='TODO', keep_nvmwes=True):

            if sentence.kvs_with_key("sent_id") == 0:
                self.check_artificial_flag(sentence, 'sent_id', self.args.gen_sentid, "--gen-sentid")
            if sentence.kvs_with_key("text") == 0:
                self.check_artificial_flag(sentence, 'text', self.args.gen_text, "--gen-text")

            for kv_pair in sentence.kv_pairs:
                if kv_pair.key == 'sent_id':
                    kv_pair._key = "source_sent_id"
            sentence.print_conllup_comments(sent_id_key="source_sent_id")

            for token, mwecodes in sentence.tokens_and_mwecodes():
                columns = [token.get(c, None) for c in UD_COLS]
                columns.append(';'.join(mwecodes) if mwecodes else missing_mwe_annot)
                columns = [c or "_" for c in columns]
                print('\t'.join(columns))
            print()


    def check_artificial_flag(self, sent: dataalign.Sentence, metadata_key: str, skip_check: bool, flag: str):
        if not skip_check:
            sent.warn(
                "Sentence #{} is missing the `{}` metadata. " \
                "Fix your input file, or use the {} flag to " \
                "auto-generate the required CoNLL-U metadata." \
                 .format(sent.nth_sent, metadata_key, flag), error=True)



#####################################################

if __name__ == "__main__":
    Main(parser.parse_args()).run()

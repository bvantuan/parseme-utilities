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
RE_TEXT = re.compile('^ *text *= *(.*)')


parser = argparse.ArgumentParser(description="""
        Convert input file format from PARSEME-TSV (edition 1.0)
        to the UD-PARSEME-TSV format (edition 1.1).""")
parser.add_argument("--underspecified-mwes", action='store_true',
        help="""If set, represent empty PARSEME:MWE slots as "_" instead of "*".""")
parser.add_argument("--artificial", action='store_true',
        help="""If set, automatically create missing 'text' and 'sent_id' metadata.""")
        # (SC: This is not set by default, because some people actually will have the metadata,
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
        UD_COLS = 'ID FORM LEMMA UPOS XPOS FEATS HEAD DEPREL DEPS MISC'.split()
        print('# global.columns =', ' '.join(UD_COLS + ['PARSEME:MWE']))

        for sentence in dataalign.iter_aligned_files(
                self.args.input, self.conllu_paths,
                default_mwe_category='TODO', keep_nvmwes=True):

            #TODO sentence.print_tsv_comments()
            written_sentid = written_text = False
            for comment in sentence.toplevel_comments:
                text = comment.text
                m = RE_SENT_ID.match(text)
                if m:
                    text = 'source_sent_id = . . {}'.format(m.group(2).strip().split()[-1])
                    written_sentid = True
                if RE_TEXT.match(text):
                    written_text = True
                print("#", text)

            if not written_sentid:
                self.write_artificial_sentid(sentence)
            if not written_text:
                self.write_artificial_text(sentence)

            for token, mwecodes in sentence.tokens_and_mwecodes():
                columns = [token.get(c, None) for c in UD_COLS]
                columns.append(';'.join(mwecodes) if mwecodes else missing_mwe_annot)
                columns = [c or "_" for c in columns]
                print('\t'.join(columns))
            print()


    def write_artificial_sentid(self, sent: dataalign.Sentence):
        self.check_artificial_flag(sent, 'sent_id')
        sent_id = "autogen--{}--{}".format(os.path.basename(sent.file_path), sent.nth_sent)
        print("# source_sent_id = . . {}".format(sent_id))

    def write_artificial_text(self, sent: dataalign.Sentence):
        self.check_artificial_flag(sent, 'text')
        text = ''.join(self.iter_calc_text(sent))
        print("# text = {}".format(text))

    def iter_calc_text(self, sent: dataalign.Sentence):
        for token in sent.tokens:
            yield token.surface + ('' if token.nsp else ' ')

    def check_artificial_flag(self, sent: dataalign.Sentence, metadata_key: str):
        if not self.args.artificial:
            sent.warn(
                "Sentence #{} is missing the `{}` metadata. " \
                "Fix your input file, or use the --artificial flag to " \
                "auto-generate the required CoNLL-U metadata." \
                 .format(sent.nth_sent, metadata_key), error=True)



#####################################################

if __name__ == "__main__":
    Main(parser.parse_args()).run()

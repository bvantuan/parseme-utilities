#! /usr/bin/env python3

import argparse
import io
import re
import sys
import subprocess
from lxml import etree as ElementTree

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../lib"))
import dataalign
from dataalign import folia

POS_SET_URL = "https://github.com/proycon/parseme-support/raw/master/parseme-pos.foliaset.xml"
CATEG_SET_URL = "https://github.com/proycon/parseme-support/raw/master/parseme-mwe-alllanguages2018.foliaset.xml"
XML_CONLLUP_SEP = dataalign.FoliaIterator.XML_CONLLUP_SEP

parser = argparse.ArgumentParser(description="""
        Convert input file format to FoLiA XML format
        (also add info from CoNLL-U files, if available).""")
parser.add_argument("--input", type=str, nargs="+", required=True,
        help="""Path to input files (in FoLiA XML or PARSEME TSV format)""")
parser.add_argument("--lang", choices=sorted(dataalign.LANGS), metavar="LANG", required=True,
        help="""Name of the target language (e.g. EN, FR, PL, DE...)""")
parser.add_argument("--conllu", type=str, nargs="+",
        help="""Path to parallel input CoNLL files""")


class Main:
    def __init__(self, args):
        self.args = args

    def run(self):
        self.conllu_paths = self.args.conllu or dataalign.calculate_conllu_paths(self.args.input)
        doc_id = dataalign.basename_without_ext(self.args.input[0])
        doc = folia.Document(id=doc_id if doc_id.isalpha() else "_")
        main_text = doc.add(folia.Text)

        if self.args.lang in ["FA", "HE", "YI"]:
            doc.metadata['direction'] = 'rtl'
        doc.metadata['status'] = 'untouched'
        doc.declare(folia.Entity, set=CATEG_SET_URL)
        doc.declare(folia.AnnotationType.POS, set=POS_SET_URL)

        iaf = dataalign.IterAlignedFiles(
            self.args.lang, self.args.input, self.conllu_paths, keep_nvmwes=True, debug=False)
        colnames = iaf.aligned_iterator.main_iterators[0].corpusinfo.colnames
        doc.metadata['conllup-colnames'] = XML_CONLLUP_SEP.join(colnames)

        for tsv_sentence in iaf:
            folia_sentence = main_text.add(folia.Sentence)
            for tsv_w in tsv_sentence.tokens:
                folia_w = folia_sentence.add(folia.Word, text=tsv_w["FORM"], space=(not tsv_w.nsp))

                # Note we swap "\t" and XML_CONLLUP_SEP, for easier human inspection of <conllup-fields>
                conllup_text = XML_CONLLUP_SEP.join(tsv_w.get(col, "_").replace(XML_CONLLUP_SEP, "\t") for col in colnames)
                foreign = ElementTree.Element('foreign-data')
                foreign.append(ElementTree.Element('conllup-columns', columns=conllup_text))
                folia_w.add(folia.ForeignData, node=foreign)

            if tsv_sentence.mweoccurs:
                folia_mwe_list = folia_sentence.add(folia.EntitiesLayer)
                for mweo in tsv_sentence.mweoccurs:
                    mweo.metadata.to_folia(mweo, folia_sentence, folia_mwe_list)

            for keyval in tsv_sentence.kv_pairs:
                if isinstance(keyval, dataalign.CommentMetadata):
                    keyval.to_folia(folia_sentence)
                elif keyval.key != 'global.columns':
                    foreign = ElementTree.Element('foreign-data')
                    foreign.append(ElementTree.Element('kv-pair', key=keyval.key, value=keyval.value))
                    folia_sentence.add(folia.ForeignData, node=foreign)

        print(doc.xmlstring())


#####################################################

if __name__ == "__main__":
    Main(parser.parse_args()).run()

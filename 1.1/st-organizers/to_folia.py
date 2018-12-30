#! /usr/bin/env python3

from pynlpl.formats import folia

import argparse
import io
import re
import sys
import subprocess
from lxml import etree as ElementTree

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../lib"))
import dataalign

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
        output = folia.Document(id=dataalign.basename_without_ext(self.args.input[0]))
        main_text = output.add(folia.Text)

        iaf = dataalign.IterAlignedFiles(
            self.args.lang, self.args.input, self.conllu_paths, keep_nvmwes=True, debug=False)
        colnames = iaf.aligned_iterator.main_iterators[0].corpusinfo.colnames
        foreign = ElementTree.Element('foreign-data')
        foreign.append(ElementTree.Element('conllup-colnames', value="\t".join(colnames)))
        main_text.add(folia.ForeignData, node=foreign)

        for tsv_sentence in iaf:
            # TODO CHECK tsvlib in github XXX
            folia_sentence = main_text.add(folia.Sentence)
            for tsv_w in tsv_sentence.tokens:
                folia_w = folia_sentence.add(folia.Word, text=tsv_w["FORM"], space=tsv_w.nsp)

                conllup_text = "\t".join(tsv_w.get(col, "_") for col in colnames)
                foreign = ElementTree.Element('foreign-data')
                foreign.append(ElementTree.Element('conllup-fields', value=conllup_text))
                folia_w.add(folia.ForeignData, node=foreign)

                # TODO: add MWEs
                # TODO: add comments

                mwe_occurs = list(tsv_sentence.mwe_occurs())
                if mwe_occurs:
                    folia_mwe_list = folia_sentence.add(folia.EntitiesLayer)
                    for mweo in mwe_occurs:
                        assert mweo.category, "Conversion to FoLiA requires all MWEs to have a category"  # checkme
                        folia_words = [folia_sentence[i] for i in mweo.indexes]
                        folia_mwe_list.append(folia.Entity, *folia_words, cls=mweo.category, annotatortype=folia.AnnotatorType.MANUAL)

        print(output.xmlstring())


#####################################################

if __name__ == "__main__":
    Main(parser.parse_args()).run()

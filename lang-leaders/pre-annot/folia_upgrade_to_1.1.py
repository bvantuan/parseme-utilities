#! /usr/bin/env python3

import argparse
import subprocess
from pynlpl.formats import folia

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../lib"))
import dataalign

parser = argparse.ArgumentParser(description="""
        Convert XML files from 1.0 to 1.1 format.
        The output is written to `./PARSEME_CONVERTED_1.1`.
        """)
parser.add_argument("--input", type=str, required=True,
        help="""Path to the input file (in FoLiA XML format)""")


ENTITY_SET_DEFINITION = 'https://github.com/proycon/parseme-support/raw/master/parseme-mwe-alllanguages2018.foliaset.xml'

class Main:
    def __init__(self, args):
        self.args = args

    def run(self):
        dirname = './PARSEME_CONVERTED_1.1' + os.path.dirname(self.args.input)
        subprocess.check_call(["mkdir", "-p", dirname])
        foliadoc = folia.Document(file=self.args.input)
        self.upgrade(foliadoc)
        basename = os.path.basename(self.args.input)
        foliadoc.save(os.path.join(dirname, basename))


    def upgrade(self, foliadoc):
        foliadoc.annotations = [(k,v) for (k,v) in foliadoc.annotations if k != folia.Entity.ANNOTATIONTYPE]
        foliadoc.declare(folia.Entity, set=ENTITY_SET_DEFINITION)
        for entity in foliadoc.select(folia.Entity):
            entity.set = ENTITY_SET_DEFINITION
            if entity.cls in dataalign.Categories.RENAMED:
                entity.cls = dataalign.Categories.RENAMED[entity.cls]
            elif entity.cls not in dataalign.Categories.KNOWN:
                print("WARNING: unknown MWE category", entity.cls, file=sys.stderr)


#####################################################

if __name__ == "__main__":
    Main(parser.parse_args()).run()

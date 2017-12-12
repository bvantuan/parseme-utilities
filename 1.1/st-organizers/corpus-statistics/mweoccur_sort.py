#! /usr/bin/env python3

import argparse
import collections
import os
import re
import sys

HERE = os.path.dirname(os.path.realpath(__file__))


parser = argparse.ArgumentParser(description="""
        Sort mweoccur file (stdin) based on 'annotation-methods' column.""")


class Main(object):
    def __init__(self, args):
        self.args = args
        self.header = next(sys.stdin).strip().split("\t")
        self.idx_methods = self.header.index('annotation-methods')
        print(*self.header, sep='\t')


    def run(self):
        lines = [x.strip().split("\t") for x in sys.stdin]
        lines = [x for x in lines if not 'Human' in x[self.idx_methods]]
        lines.sort(key=self.sort_key)
        for line in lines:
            print(*line, sep='\t')


    def sort_key(self, line):
        methods = line[self.idx_methods].split(',')
        wingaps = [int(m[len('WindowGap'):]) for m in methods if m.startswith('WindowGap')]
        # Sort first the lines that have Dependency/UnlabeledDeps/BagOfDeps,
        # then sort WindowGapX before WindowGapY if X < Y
        return [int('Dependency' not in methods), int('UnlabeledDeps' not in methods),
                int('BagOfDeps' not in methods), min(wingaps + [9999])]


#####################################################

if __name__ == "__main__":
    Main(parser.parse_args()).run()

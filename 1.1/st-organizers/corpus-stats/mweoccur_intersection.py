#! /usr/bin/env python3

import argparse
import collections
import os
import re
import sys

try:
    import matplotlib_venn
except ImportError:
    exit('ERROR: please run: sudo pip3 install matplotlib_venn')

from matplotlib import pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

HERE = os.path.dirname(os.path.realpath(__file__))


parser = argparse.ArgumentParser(description="""
        Calculate intersection between Dependency and WinGap approaches.""")
parser.add_argument("--language", type=str,
        help="""Name of the language (e.g. FR)""")
parser.add_argument("--input-dependency", type=argparse.FileType('r'),
        help="""mweoccurs file for Dependency""")
parser.add_argument("--input-window", type=argparse.FileType('r'), nargs='+',
        help="""mweoccurs file for WinGapX""")
parser.add_argument("--output-pdf",
        help="""path to output PDF file""")


class MweOccurFile(collections.namedtuple('MweOccurFile', 'filepath finder_name occurs')):
    r'''MweOccurFile represents data coming from a mweoccurs file.
    
    Attributes:
    @type filepath: str
    @type finder_name: str
    @type occurs: Set[str]
    '''


class Main(object):
    def __init__(self, args):
        self.args = args

    def run(self):
        dep = self._read(self.args.input_dependency)
        others = [self._read(f) for f in self.args.input_window]
        self.print_intersections([dep] + others)

        if self.args.output_pdf:
            with PdfPages(self.args.output_pdf) as pdf:
                for other in others:
                    self.plot(pdf, dep, other)


    def print_intersections(self, all_mweoccurfiles):
        r'''Output intersections between pairs in `all_mweoccurfiles`.
        @type other: List[MweOccurFile]
        '''
        import itertools
        print(*'Language FinderLeft FinderRight Left Left/LM Left+Mid Mid Mid+Right Right/RM Right'.split(), sep='\t')

        for first, other in itertools.combinations(all_mweoccurfiles, 2):
            n_both = len(first.occurs.intersection(other.occurs))
            n_left = len(first.occurs) - n_both
            n_right = len(other.occurs) - n_both

            print(self.args.language, first.finder_name, other.finder_name,
                  n_left, '{:.0f}%'.format(100*n_left/(len(first.occurs) or 1)), len(first.occurs), n_both,
                  len(other.occurs), '{:.0f}%'.format(100*n_right/(len(other.occurs) or 1)), n_right, sep='\t')


    def plot(self, pdf, first: MweOccurFile, other: MweOccurFile):
        r'''Output intersections between `first` and `other`.'''
        n_both = len(first.occurs.intersection(other.occurs))
        n_left = len(first.occurs) - n_both
        n_right = len(other.occurs) - n_both

        c = matplotlib_venn.venn2(subsets=(n_left, n_right, n_both), set_labels=(first.finder_name, other.finder_name))
        c.get_patch_by_id('01').set_color('red')
        c.get_patch_by_id('10').set_color('blue')
        for id in ['10', '11', '01']:
            if id!='11' or n_both!=0:
                c.get_patch_by_id(id).set_edgecolor('black')
                c.get_patch_by_id(id).set_alpha(0.3)

        if n_both!=0:
            c.get_patch_by_id('11').set_color('purple')
            c.get_patch_by_id('11').set_edgecolor('none')

        c.get_label_by_id('10').set_text('{}\n({:.0f}%)'.format(n_left, 100*n_left/(len(first.occurs) or 1)))
        c.get_label_by_id('01').set_text('{}\n({:.0f}%)'.format(n_right, 100*n_right/(len(other.occurs) or 1)))
        plt.title('Language: ' + self.args.language)
        pdf.savefig()
        plt.cla()


    def _read(self, fileobj):
        r'''Read fileobj and return a MweOccurFile.'''
        with fileobj:
            occurs = frozenset(line.split('\t')[4] for line in fileobj if '\tLITERAL\t' in line)
            filename = fileobj.name.split('/')[-2]
            return MweOccurFile(fileobj.name, filename, occurs)



#####################################################

if __name__ == "__main__":
    Main(parser.parse_args()).run()

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
parser.add_argument("--input-mweoccurs", type=argparse.FileType('r'),
        help="""all_mweoccurs file""")
parser.add_argument("--output-pdf",
        help="""path to output PDF file""")


class MweOccurFile(collections.namedtuple('MweOccurFile', 'filepath finder_name literal_occurs all_occurs')):
    r'''MweOccurFile represents data coming from a mweoccurs file.
    
    Attributes:
    @type filepath: str
    @type finder_name: str
    @type literal_occurs: Set[str]
    @type all_occurs: Set[str]
    '''


class Main(object):
    def __init__(self, args):
        self.args = args

    def run(self):
        human, dep, others = self._read(self.args.input_mweoccurs)
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
            n_both = len(first.literal_occurs.intersection(other.literal_occurs))
            n_left = len(first.literal_occurs) - n_both
            n_right = len(other.literal_occurs) - n_both

            print(self.args.language, first.finder_name, other.finder_name,
                  n_left, '{:.0f}%'.format(100*n_left/(len(first.literal_occurs) or 1)), len(first.literal_occurs), n_both,
                  len(other.literal_occurs), '{:.0f}%'.format(100*n_right/(len(other.literal_occurs) or 1)), n_right, sep='\t')


    def plot(self, pdf, first: MweOccurFile, other: MweOccurFile):
        r'''Output intersections between `first` and `other`.'''
        n_both = len(first.literal_occurs.intersection(other.literal_occurs))
        n_left = len(first.literal_occurs) - n_both
        n_right = len(other.literal_occurs) - n_both

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

        c.get_label_by_id('10').set_text('{}\n({:.0f}%)'.format(n_left, 100*n_left/(len(first.literal_occurs) or 1)))
        c.get_label_by_id('01').set_text('{}\n({:.0f}%)'.format(n_right, 100*n_right/(len(other.literal_occurs) or 1)))
        plt.title('Language: ' + self.args.language)
        pdf.savefig()
        plt.cla()


    def _read(self, fileobj):
        r'''Read fileobj and return a MweOccurFile.'''
        method2literalsentences = collections.defaultdict(set)
        method2allsentences = collections.defaultdict(set)
        IDX_LITERAL, IDX_METHODS, IDX_SENT = 3, 4, 5

        with fileobj:
            header = next(fileobj).split('\t')
            assert header[IDX_LITERAL] == 'idiomatic-or-literal', header
            assert header[IDX_METHODS] == 'annotation-methods', header
            assert header[IDX_SENT] == 'sentence-with-mweoccur', header

            for line in fileobj:
                line = line.split('\t')
                for method in line[IDX_METHODS].split(','):
                    method2allsentences[method].add(line[IDX_SENT])
                    if 'LITERAL' in line[IDX_LITERAL]:
                        method2literalsentences[method].add(line[IDX_SENT])

        mappings = {method: MweOccurFile(
                                fileobj.name,  method,
                                frozenset(method2literalsentences[method]),
                                frozenset(method2allsentences[method]))
                    for method in method2allsentences}

        human, dep = mappings.pop('Human'), mappings.pop('Dependency')
        return human, dep, [v for (k,v) in sorted(mappings.items())]



#####################################################

if __name__ == "__main__":
    Main(parser.parse_args()).run()

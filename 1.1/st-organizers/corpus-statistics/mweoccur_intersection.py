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
parser.add_argument("--language", type=str, required=True,
        help="""Name of the language (e.g. FR)""")
parser.add_argument("--input-mweoccurs", type=argparse.FileType('r'),
        help="""all_mweoccurs file""")
parser.add_argument("--output-pdf-literal",
        help="""path to output PDF file""")
parser.add_argument("--output-pdf-idiomatic",
        help="""path to output PDF file""")


class MweOccurFile(collections.namedtuple('MweOccurFile', 'filepath finder_name literal_occurs idiomat_occurs')):
    r'''MweOccurFile represents data coming from a mweoccurs file.
    
    Attributes:
    @type filepath: str
    @type finder_name: str
    @type literal_occurs: Set[str]
    @type idiomat_occurs: Set[str]
    '''


class Main(object):
    def __init__(self, args):
        self.args = args

    def run(self):
        human, dep, others = self._read(self.args.input_mweoccurs)
        print(*'Considering Language FinderLeft FinderRight Left Left/LM Left+Mid Mid Mid+Right Right/RM Right'.split(), sep='\t')
        self.print_intersections('LITERAL+IDIOMATIC', [human] + ([dep] if dep else []) + others, lambda x: x.idiomat_occurs)
        self.print_intersections('LITERAL', [human] + ([dep] if dep else []) + others, lambda x: x.literal_occurs)

        if self.args.output_pdf_idiomatic:
            with PdfPages(self.args.output_pdf_idiomatic) as pdf:
                page_with_text(pdf, 'Comparing Humans (IDIOMATIC) with Predictions (IDIOMATIC)')
                for other in others:
                    self.plot(pdf, human, other, lambda x: x.idiomat_occurs)

        if self.args.output_pdf_literal:
            with PdfPages(self.args.output_pdf_literal) as pdf:
                if dep:
                    page_with_text(pdf, 'Comparing Dependency (LITERAL) with OtherPredictions (LITERAL)')
                    for other in others:
                        self.plot(pdf, dep, other, lambda x: x.literal_occurs)


    def print_intersections(self, considering_x, all_mweoccurfiles, occurs):
        r'''Output intersections between pairs in `all_mweoccurfiles`.
        @type other: List[MweOccurFile]
        @type occurs: Function[MweOccurFile, Set[str]]
        '''
        import itertools
        for first, other in itertools.combinations(all_mweoccurfiles, 2):
            n_both = len(occurs(first).intersection(occurs(other)))
            n_left = len(occurs(first)) - n_both
            n_right = len(occurs(other)) - n_both

            print(considering_x, self.args.language, first.finder_name, other.finder_name,
                  n_left, '{:.0f}%'.format(100*n_left/(len(occurs(first)) or 1)), len(occurs(first)), n_both,
                  len(occurs(other)), '{:.0f}%'.format(100*n_right/(len(occurs(other)) or 1)), n_right, sep='\t')


    def plot(self, pdf, first: MweOccurFile, other: MweOccurFile, occurs):
        r'''Output intersections between `first` and `other`.
        @type occurs: Function[MweOccurFile, Set[str]]
        '''
        n_both = len(occurs(first).intersection(occurs(other)))
        n_left = len(occurs(first)) - n_both
        n_right = len(occurs(other)) - n_both

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

        c.get_label_by_id('10').set_text('{}\n({:.0f}%)'.format(n_left, 100*n_left/(len(occurs(first)) or 1)))
        c.get_label_by_id('01').set_text('{}\n({:.0f}%)'.format(n_right, 100*n_right/(len(occurs(other)) or 1)))
        plt.title('Language: ' + self.args.language)
        pdf.savefig()
        plt.cla()


    def _read(self, fileobj):
        r'''Read fileobj and return a tuple
        of type: (MweOccurFile, Optional[MweOccurFile], List[MweOccurFile]).
        '''
        method2literalsentences = collections.defaultdict(set)
        method2idiomatsentences = collections.defaultdict(set)
        IDX_LITERAL, IDX_METHODS, IDX_SENT = 3, 4, 5

        with fileobj:
            header = next(fileobj).split('\t')
            assert header[IDX_LITERAL] == 'idiomatic-or-literal', header
            assert header[IDX_METHODS] == 'annotation-methods', header
            assert header[IDX_SENT] == 'sentence-with-mweoccur', header

            for line in fileobj:
                line = line.split('\t')
                for method in line[IDX_METHODS].split(','):
                    if 'LITERAL' in line[IDX_LITERAL]:
                        method2literalsentences[method].add(line[IDX_SENT])
                    else:
                        method2idiomatsentences[method].add(line[IDX_SENT])

        mappings = {method: MweOccurFile(
                                fileobj.name,  method,
                                frozenset(method2literalsentences[method]),
                                frozenset(method2idiomatsentences[method]))
                    for method in set(method2idiomatsentences)|set(method2literalsentences)}

        human, dep = mappings.pop('Human'), mappings.pop('Dependency', None)
        return human, dep, [v for (k,v) in sorted(mappings.items())]


def page_with_text(pdf, text):
    fig = plt.figure()
    ax = fig.add_subplot(111)
    fig.subplots_adjust(top=0.85)
    ax.text(0, .5, text, fontsize=10)
    plt.axis('off')
    pdf.savefig()
    plt.cla()


#####################################################

if __name__ == "__main__":
    Main(parser.parse_args()).run()

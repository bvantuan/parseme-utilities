#! /usr/bin/env python3

import argparse
import collections
import os
import re
import sys

import matplotlib_venn
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
parser.add_argument("--output", required=True,
        help="""mweoccurs file for WinGapX""")


class Main(object):
    def __init__(self, args):
        self.args = args

    def run(self):
        dep = set(self._read(self.args.input_dependency))

        with PdfPages(self.args.output) as pdf:
            for f_other in self.args.input_window:
                other = set(self._read(f_other))
                n_both = len(dep.intersection(other))
                gap = re.search(r'Gap(\d+)', f_other.name).group(1)

                print('{}:  (Dep  {:<7d} {{Both {} Both) {:>7d}  Other}}       ----   (Both={:.0f}%)  {{Both={:.0f}%}}'
                      .format(self.args.language, len(dep)-n_both, n_both, len(other)-n_both, 100*n_both/len(dep), 100*n_both/len(other)))

                left, right = len(dep-other), len(other-dep)
                c = matplotlib_venn.venn2(subsets=(left, right, n_both), set_labels=('Dependency', 'Window\nGap='+gap))
                c.get_patch_by_id('01').set_color('red')
                c.get_patch_by_id('10').set_color('blue')
                c.get_patch_by_id('11').set_color('purple')
                for id in ['10', '11', '01']:
                    c.get_patch_by_id(id).set_edgecolor('black')
                    c.get_patch_by_id(id).set_alpha(0.3)
                c.get_patch_by_id('11').set_edgecolor('none')

                c.get_label_by_id('10').set_text('{}\n({:.0f}%)'.format(left, 100*left/len(dep)))
                c.get_label_by_id('01').set_text('{}\n({:.0f}%)'.format(right, 100*right/len(other)))
                plt.title('Language: ' + self.args.language)
                pdf.savefig()
                plt.cla()


    def _read(self, fileobj):
        return [line for line in fileobj if '\tLITERAL\t' in line]



#####################################################

if __name__ == "__main__":
    Main(parser.parse_args()).run()

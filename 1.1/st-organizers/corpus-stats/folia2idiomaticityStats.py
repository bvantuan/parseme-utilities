#! /usr/bin/env python3

import argparse
import collections

import os, sys
sys.path.insert(0, os.path.dirname(__file__)+"/../../lib")
import dataalign


parser = argparse.ArgumentParser(description="""
        Read input files and generate output files with interesting
        information about idiomatic vs non-annotated literal occurrences of MWEs.

        This script should be run AFTER consistency checks.
        Any non-annotated occurrence of "Skipped MWEs" will be
        treated as compositional.
        """)
parser.add_argument("--lang", choices=sorted(dataalign.LANGS), metavar="LANG", required=True,
        help="""ID of the target language (e.g. EN, FR, PL, DE...)""")
parser.add_argument("--literal-finding-method", type=str, required=True,
        help="""Method of finding literal cases. One of {Dependency, WinGap0, WinGap1, WinGap2...}""")
parser.add_argument("--input", type=str, nargs="+", required=True, metavar='PATH',
        help="""Path to input files (preferably in FoLiA XML format, but PARSEME TSV works too)""")
parser.add_argument("--conllu", type=str, nargs="+", metavar='PATH',
        help="""Path to parallel input CoNLL files""")
parser.add_argument("--out-categories", type=argparse.FileType('w'), metavar='PATH',
        help="""Path to output TSV with summary of idiomaticity per category""")
parser.add_argument("--out-mwes", type=argparse.FileType('w'), metavar='PATH',
        help="""Path to output TSV with idiomaticity per MWE""")
parser.add_argument("--out-mweoccurs", type=argparse.FileType('w'), metavar='PATH',
        help="""Path to output TSV with every idiomatic (annotated) & literal (discovered) case""")



class Main:
    def __init__(self, args):
        self.args = args
        self.mwes = []  # type: list[MWELexicalItem]
        self.seen_mweoccur_ids = set()  # type: set[str]


    def run(self):
        (self.mwes, _) = dataalign.read_mwelexitems(
                self.args.lang, dataalign.iter_sentences(self.args.input, self.args.conllu))
        self.seen_mweoccur_ids.update(o.id() for mwe in self.mwes for o in mwe.mweoccurs)
        skip_sents = dataalign.iter_sentences(self.args.input, self.args.conllu, verbose=False)
        self.find_literals(skip_sents)

        if self.args.out_categories:
            self.print_categories()
        if self.args.out_mwes:
            self.print_mwes()
        if self.args.out_mweoccurs:
            self.print_mweoccurs()


    def find_literals(self, sentences):
        r"""Find MWE occurrences."""
        if self.args.literal_finding_method == 'Dependency':
            finder = dataalign.DependencyBasedSkippedFinder(self.args.lang, self.mwes)
        else:
            assert self.args.literal_finding_method.startswith('WinGap'), self.args.literal_finding_method
            max_gaps = int(self.args.literal_finding_method[len('WinGap'):])
            finder = dataalign.WindowBasedSkippedFinder(self.args.lang, self.mwes, max_gaps)

        for mwe, mweoccur in finder.find_skipped_in(sentences):
            # Only add 'Skipped' if a MWE was not seen at this position
            if mweoccur.id() not in self.seen_mweoccur_ids:
                self.seen_mweoccur_ids.add(mweoccur.id())
                mwe.add_skipped_mweoccur(mweoccur)


    def print_categories(self):
        r'''Print TSV with "Skipped" info for each category'''
        count_idio, count_lit = collections.Counter(), collections.Counter()

        print("category", "n-literal", "n-idiomatic", "n-total",
              "idiomaticity-rate", sep='\t', file=self.args.out_categories)
        for mwe in sorted(self.mwes, key=lambda m: m.canonicform):
            for mweoccur in mwe.mweoccurs:
                D = count_idio if (mweoccur.category != 'Skipped') else count_lit
                D[self._categ(mweoccur, mwe)] += 1
                D['TOTAL'] += 1

        categs = list(sorted(set(count_idio.keys()) - set(['TOTAL']))) + ['TOTAL']
        for categ in categs:
            idio, lit = count_idio[categ], count_lit[categ]
            print(categ, lit, idio, lit+idio, idio/(lit+idio), sep='\t', file=self.args.out_categories)


    def print_mwes(self):
        r'''Print TSV with "Skipped" info for each MWELexicalItem'''
        total, total_annotated = 0, 0
        print("MWE", "major-POS-tag", "major-category", "n-literal", "n-idiomatic", "n-total", "idiomaticity-rate",
              "example-literal", sep='\t', file=self.args.out_mwes)
        for mwe in sorted(self.mwes, key=lambda m: m.canonicform):
            n_annotated = sum(1 for o in mwe.mweoccurs if o.category != 'Skipped')
            n = len(mwe.mweoccurs)
            total += n
            total_annotated += n_annotated

            example_skipped = '---'
            if n != n_annotated:
                example_skipped = self._example(next(o for o in mwe.mweoccurs if o.category == 'Skipped'))

            postag = dataalign.most_common(self._postag(o) for o in mwe.mweoccurs)
            category = dataalign.most_common(o.category for o in mwe.mweoccurs if o.category != 'Skipped')
            print(" ".join(mwe.canonicform), postag, category, n-n_annotated, n_annotated, n, n_annotated/n,
                  example_skipped, sep="\t", file=self.args.out_mwes)

        print("TOTAL", '---', '---', total-total_annotated, total_annotated, total, total_annotated/total,
              '---', sep="\t", file=self.args.out_mwes)


    def print_mweoccurs(self):
        r'''Print TSV with "Skipped" info for each MWEOccur'''
        print('MWE', 'POS-tag', 'idiomatic-or-literal', 'category', 'example',
              'source', sep="\t", file=self.args.out_mweoccurs)
        for mwe in sorted(self.mwes, key=lambda m: m.canonicform):
            for mweoccur in mwe.mweoccurs:
                self._output_mweoccur(mwe, mweoccur)

    def _output_mweoccur(self, mwe, mweoccur):
        r'''_output_mweoccur(MWELexicalItem, MWEOccur)'''
        idlit = 'LITERAL' if (mweoccur.category == 'Skipped') else 'IDIOMAT'
        categ = self._categ(mweoccur, mwe)

        source = '{}:{}'.format(os.path.basename(mweoccur.sentence.file_path), mweoccur.sentence.lineno)
        print(" ".join(mwe.canonicform), self._postag(mweoccur), idlit, categ,
              self._example(mweoccur), source, sep="\t", file=self.args.out_mweoccurs)


    def _postag(self, mweoccur):
        r'''_postag(MWEOccur) -> str'''
        return " ".join(t.univ_pos for t in mweoccur.reordered.tokens if t.univ_pos) or 'MISSING'


    def _categ(self, mweoccur, mwe):
        r'''_categ(MWEOccur, MWELexicalItem) -> str
        * Return mweoccur.category if different from "Skipped"
        * Else returns majority category
        '''
        if mweoccur.category != 'Skipped':
            return mweoccur.category
        all_categs = [o.category for o in mwe.mweoccurs if o.category != 'Skipped']
        return dataalign.most_common(all_categs)


    def _example(self, mweoccur):
        r'''_example(MWEOccur) -> str'''
        return " ".join(('['+t.surface+']' if i in mweoccur.indexes else t.surface).replace('\t', '<TAB>') \
                        for (i,t) in enumerate(mweoccur.sentence.tokens))



#####################################################

if __name__ == "__main__":
    Main(parser.parse_args()).run()

#! /usr/bin/env python3

import argparse
import collections
import json
import subprocess

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../lib"))
import dataalign

parser = argparse.ArgumentParser(description="""
        Split input files into SPLIT/{train,test,dev}.cupt.""")
parser.add_argument("--lang", choices=sorted(dataalign.LANGS), metavar="LANG", required=True,
        help="""Name of the target language (e.g. EN, FR, PL, DE...)""")
parser.add_argument("--subcorpora-json", required=True,
        help="""JSON file describing subcorpora (see calcSubcorporaJson.py)""")
parser.add_argument("--input", nargs="+", type=str, required=True,
        help="""Path to input files (in CUPT format)""")


class Main:
    def __init__(self, args):
        self.args = args
        subcorpora_json = json.load(open(self.args.subcorpora_json))
        self.subcorpora = [Subcorpus(x) for x in subcorpora_json["subcorpora"]]
        self.first2subcorpus = {rng["first"]: sc for sc in self.subcorpora for rng in sc.ranges}
        self.last2subcorpus = {rng["last"]: sc for sc in self.subcorpora for rng in sc.ranges}

    def run(self):
        sents = list(dataalign.iter_aligned_files(
            self.args.input, None, keep_nvmwes=False))

        # Calculate number of sentences and MWEs for subcorpora
        for sent, subcorpus in self.iter_sentence_with_subcorpus(sents):
            subcorpus.n_sents += 1
            subcorpus.n_mwes += len(sent.mweannots)
        total_n_mwes = sum(sc.n_mwes for sc in self.subcorpora)

        # Calculate split sizes for all subcorpora
        split = decide_split(total_n_mwes)
        for subcorpus in self.subcorpora:
            mul = subcorpus.n_mwes / total_n_mwes
            subcorpus.subsplit = IntSplit(
                train=int(split.train*mul),
                test=int(split.test*mul),
                dev=int(split.dev*mul))

        largest_subcorpus = max(self.subcorpora, key=lambda sc: sc.n_mwes)
        delta_test = split.test - sum(sc.subsplit.test for sc in self.subcorpora)
        delta_dev = split.dev - sum(sc.subsplit.dev for sc in self.subcorpora)
        largest_subcorpus.subsplit.test += delta_test
        largest_subcorpus.subsplit.dev += delta_dev

        for subcorpus in self.subcorpora:
            print("COUNT-MWEs: {regex}: train={ss.train} test={ss.test} dev={ss.dev}".format(
                regex=subcorpus.regex, ss=subcorpus.subsplit), file=sys.stderr)
        print("COUNT-MWEs: TOTAL: train={ss.train} test={ss.test} dev={ss.dev}" \
              .format(ss=split), file=sys.stderr)

        # Dedicate each sentence to one of {test,train,dev}
        dedic_sents = []
        for sent, subcorpus in self.iter_sentence_with_subcorpus(sents):
            if subcorpus.subsplit.test > 0:
                dedic_sents.append(DedicatedSentence(sent, 'test'))
                subcorpus.subsplit.test -= len(sent.mweannots)
            elif subcorpus.subsplit.dev > 0:
                dedic_sents.append(DedicatedSentence(sent, 'dev'))
                subcorpus.subsplit.dev -= len(sent.mweannots)
            else:
                dedic_sents.append(DedicatedSentence(sent, 'train'))

        # Print sentences
        subprocess.check_call("mkdir -p ./SPLIT", shell=True)
        for splittype in 'test dev train'.split():
            with open("./SPLIT/{}.cupt".format(splittype), "w+") as output:
                dataalign.ConllupWriter(output=output).write_sentences([
                    s for (s, stype) in dedic_sents if stype == splittype])


    def iter_sentence_with_subcorpus(self, sentences: list):
        r"""Yield (Sentence, Subcorpus) pairs."""
        cur_subcorpus = None
        for sent in sentences:
            sentid = sent.unique_toplevel_metadata('source_sent_id').split()[-1]
            if sentid in self.first2subcorpus:
                assert cur_subcorpus is None, ("Sentence inside multiple subcorpora", sentid)
                cur_subcorpus = self.first2subcorpus[sentid]
            assert cur_subcorpus, ("Sentence not in any subcorpus", sentid)
            yield sent, cur_subcorpus
            if sentid in self.last2subcorpus:
                cur_subcorpus = None
        assert cur_subcorpus is None



class Subcorpus:
    r"""Subcorpus information."""
    def __init__(self, json_dict):
        self.regex = json_dict["regex"]  # type: str
        self.ranges = json_dict["ranges"]  # type: list[dict]
        self.n_sents = 0
        self.n_mwes = 0
        self.subsplit = None  # type: Split


class IntSplit:
    r"""Like a tuple of (int, int, int), but allows assignment."""
    def __init__(self, train: int, test: int, dev: int):
        self.train, self.test, self.dev = train, test, dev

def decide_split(n_mwes: int) -> IntSplit:
    r"""Return an IntSplit."""
    if n_mwes < 500:
        tenth = n_mwes//10
        return IntSplit(train=tenth, test=n_mwes-tenth, dev=0)
    if n_mwes < 1500:
        return IntSplit(train=n_mwes-500, test=500, dev=0)
    if n_mwes < 3000:
        return IntSplit(train=n_mwes-1000, test=500, dev=500)
    tenth = n_mwes//10
    return IntSplit(train=n_mwes-2*tenth, test=tenth, dev=tenth)


DedicatedSentence = collections.namedtuple('DedicatedSentence', 'sent dedicated_to')



#####################################################

if __name__ == "__main__":
    Main(parser.parse_args()).run()

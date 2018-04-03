#! /usr/bin/env python3

import argparse
import collections
import json
import re
import subprocess

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../lib"))
import dataalign

parser = argparse.ArgumentParser(description="""
        Calculate subcorpora.json file representing all subcorpora
        (with different genres or domains). The train/test/dev split
        will take this subcorpora division into account.""")
parser.add_argument("--lang", choices=sorted(dataalign.LANGS), metavar="LANG", required=True,
        help="""Name of the target language (e.g. EN, FR, PL, DE...)""")
parser.add_argument("--regexes", nargs="*", default=(),
        help="""Regexes to try before automatic detection""")
parser.add_argument("--input", type=str, required=True,
        help="""Path to input file (in some conllu-like format)""")


class Main:
    def __init__(self, args):
        self.args = args


    def run(self):
        regex2groups = collections.OrderedDict()
        last_regex, last_group = None, None

        with open(self.args.input) as fileobj:
            for line in fileobj:
                if re.match('#.*sent_id.*=', line):
                    sent_id = line.strip().split("=")[-1].split()[-1]
                    regex = self.calc_regex(sent_id)
                    if regex == last_regex:
                        last_group["last"] = sent_id
                        last_group["n-sents"] += 1
                    else:
                        last_regex, last_group = regex, group(sent_id)
                        groups = regex2groups.setdefault(regex, [])
                        groups.append(last_group)

        for regex in self.args.regexes:
            if regex not in regex2groups:
                dataalign.msg_stderr('WARNING', 'Regex does not match anything: {!r}'.format(regex))

        objs = [{"regex": k, "ranges": v} for (k, v) in regex2groups.items()]
        j = {'subcorpora': objs}
        json.dump(j, sys.stdout, indent=3)
        print()


    def calc_regex(self, sent_id: str) -> str:
        r"""Return a regex that matches `sent_id`."""
        for regex in self.args.regexes:
            if re.match(regex+'$', sent_id):
                return regex
        return re.sub(r'\d+$', r'(\d+)', sent_id)


def group(sent_id):
    r"""Represent a group of `sent_id`s that match the same regex."""
    return collections.OrderedDict(
        [("first", sent_id), ("last", sent_id), ("n-sents", 0)])


#####################################################

if __name__ == "__main__":
    Main(parser.parse_args()).run()

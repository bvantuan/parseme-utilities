#!/usr/bin/env python3

from typing import Tuple, List, Iterable, FrozenSet

import argparse
# import sys
import random

from collections import Counter

import conllu
from conllu import TokenList
import parseme.cupt as cupt


#################################################
# ARGUMENTS
#################################################


parser = argparse.ArgumentParser(description='split_cupt')
subparsers = parser.add_subparsers(dest='command', help='available commands')

parser_estimate = subparsers.add_parser('estimate', help='estimate test size')
parser_estimate.add_argument(
    "-i",
    dest="input_paths",
    required=True,
    nargs='+',
    help="input .cupt file(s)",
    metavar="FILE"
)
parser_estimate.add_argument(
    "--unknown-mwes",
    dest="unk_mwes",
    type=int,
    required=True,
    help="Target number of unknown MWEs"
)
parser_estimate.add_argument(
    "-n", "--random-num",
    dest="random_num",
    type=int,
    default=10,
    help="Perform each (random) split the given number of times"
)

parser_split = subparsers.add_parser('split', help='split dataset')
parser_split.add_argument(
    "-i",
    dest="input_paths",
    required=True,
    nargs='+',
    help="input .cupt file(s)",
    metavar="FILE"
)
parser_split.add_argument(
    "--test-size",
    dest="test_size",
    type=int,
    required=True,
    help="Test size (# of sentences)"
)
parser_split.add_argument(
    "--unknown-mwes",
    dest="unk_mwes",
    type=int,
    required=True,
    help="Target number of unknown MWEs"
)
parser_split.add_argument(
    "-n", "--random-num",
    dest="random_num",
    type=int,
    default=10,
    help="Perform random splits the given number of times"
)
parser_split.add_argument(
    "--train-path",
    dest="train_path",
    required=True,
    help="output train .cupt path",
    metavar="FILE"
)
parser_split.add_argument(
    "--test-path",
    dest="test_path",
    required=True,
    help="output test .cupt path",
    metavar="FILE"
)


#################################################
# UTILS
#################################################


def avg(xs):
    """Calculate the average of the given list."""
    assert len(xs) > 0
    return sum(xs) / len(xs)


def random_split(data_set: list, k: int) -> Tuple[list, list]:
    """
    Take a list of elements and divide it randomly to two parts, where
    the size of the first part should be equal to `k`.

    >>> xs = list(range(10))
    >>> ls, rs = random_split(xs, 4)
    >>> len(ls) == 4
    True
    >>> len(rs) == 6
    True
    """
    # Check the input arguments
    assert k >= 0 and k <= len(data_set)
    # We don't want to modify the input list, hence we create a copy
    copy = data_set[:]
    random.shuffle(copy)
    return (copy[:k], copy[k:])


def unknown_mwes(test_set: TokenList, train_set: TokenList) -> int:
    """Calculate the numer of unknown MWEs in the `test_set`
    w.r.t. the `train_set`.
    """

    def types_in(data_set: TokenList) -> Iterable[cupt.MWE]:
        for sent in data_set:
            for mwe in cupt.retrieve_mwes(sent).values():
                yield type_of(sent, mwe)

    train_types = Counter(types_in(train_set))
    test_types = Counter(types_in(test_set))

    all_num = sum(test_types[typ] for typ in test_types)
    seen_num = sum(
        test_types[typ]
        for typ in test_types
        if typ in train_types
    )

    return all_num - seen_num


# Helper type annotations
Lemma = str
MweTyp = FrozenSet[Lemma]


def type_of(sent: TokenList, mwe: cupt.MWE) -> MweTyp:
    """Convert the given MWE instance to the corresponding MWE type."""
    # Create a dictionary from token IDs to actual tokens
    tok_map = {}
    for tok in sent:
        tok_map[tok['id']] = tok
    # Retrieve the set of lemmas
    mwe_typ = [
        tok_map[tok_id]['lemma']
        for tok_id in mwe.span
    ]
    return frozenset(mwe_typ)


#################################################
# ESTIMATE
#################################################


def do_estimate(args):

    # Collect the dataset
    data_set = []  # type: List[TokenList]
    for input_path in args.input_paths:
        with open(input_path, "r", encoding="utf-8") as data_file:
            for sent in conllu.parse_incr(data_file):
                data_set.append(sent)

    # Perform binary search for an appropriate size of the test set
    p, q = 1, len(data_set)-1   # inclusive [p, q] range
    while p + 2 <= q:    # TODO: p < q would be enough?
        test_size = (p + q) // 2
        # Estimate the number of unknown MWEs
        unk_num = round(avg([
            unknown_mwes(*random_split(data_set, test_size))
            for _ in range(args.random_num)
        ]))
        # Reporting
        print(f"# [{test_size}] => {unk_num}")
        # Consider smaller/larger test sizes
        if unk_num > args.unk_mwes:
            q = test_size
        elif unk_num < args.unk_mwes:
            p = test_size
        else:
            break

    # Report the final test size
    test_size = (p + q) // 2
    print(f"Entire data size: {len(data_set)}")
    print(f"Optimal test size: {test_size}")


#################################################
# SPLIT
#################################################


def do_split(args):

    # Determine the header line
    with open(args.input_paths[0], "r", encoding="utf-8") as data_file:
        header = data_file.readline().strip()

    # Collect the dataset
    data_set = []  # type: List[TokenList]
    for input_path in args.input_paths:
        with open(input_path, "r", encoding="utf-8") as data_file:
            for sent in conllu.parse_incr(data_file):
                data_set.append(sent)

    # Determine the best split
    train_fin = None
    test_fin = None
    unk_num_fin = None
    for _ in range(args.random_num):
        test, train = random_split(data_set, args.test_size)
        unk_num = unknown_mwes(test, train)
        if unk_num_fin is None or \
                abs(args.unk_mwes - unk_num) < \
                abs(args.unk_mwes - unk_num_fin):
            print(f"# unseen MWEs: {unk_num}")
            train_fin, test_fin = train, test
            unk_num_fin = unk_num
        if unk_num_fin == args.unk_mwes:
            break

    def write_to(data_set, file_path):
        print(f"Writing to {file_path}...")
        with open(file_path, "w", encoding="utf-8") as data_file:
            data_file.write(header + "\n")
            for sent in data_set:
                data_file.write(sent.serialize())

    print(f"Numer of unseen MWEs in test: {unk_num_fin}")

    write_to(train_fin, args.train_path)
    write_to(test_fin, args.test_path)


#################################################
# MAIN
#################################################

if __name__ == '__main__':
    args = parser.parse_args()
    if args.command == 'estimate':
        do_estimate(args)
    elif args.command == 'split':
        do_split(args)

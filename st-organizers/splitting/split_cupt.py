#!/usr/bin/env python3

from typing import Tuple, List, Iterable, FrozenSet

import argparse
import random

from collections import Counter, OrderedDict

import conllu
from conllu import TokenList
import parseme.cupt as cupt


#################################################
# CONSTANTS
#################################################


# Preserve metadata with the following keys
RELEVANT_META = ['source_sent_id', 'text']


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
    "--unseen-mwes",
    dest="uns_mwes",
    type=int,
    required=True,
    help="Target number of unseen MWEs"
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
    "--unseen-mwes",
    dest="uns_mwes",
    type=int,
    required=True,
    help="Target number of unseen MWEs"
)
# parser_split.add_argument(
#     "--over",
#     dest="over",
#     action="store_true",
#     help="Only take splits with the number of unseen MWEs over --unseen-mwes"
# )
parser_split.add_argument(
    "--unseen-ratio",
    dest="uns_ratio",
    type=float,
    required=False,
    help="Target unseen/seen ratio"
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


def unseen_mwes(test_set: TokenList, train_set: TokenList) \
        -> Tuple[int, float]:
    """Calculate the number of unseen MWEs in the `test_set`
    w.r.t. the `train_set`, as well as the unseen/seen ratio.
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
    unseen_num = all_num - seen_num
    unseen_ratio = float(unseen_num) / all_num

    # print("UNSEEN:", [
    #     (typ, test_types[typ])
    #     for typ in test_types
    #     if typ not in train_types
    # ])

    return unseen_num, unseen_ratio


# Lemma, or base form.
Lemma = str

# We represent MWE type as a mapping from Lemma's to their counts.  The mapping
# is represented as a set of (lemma, count) pairs (since there's no FrozenDict
# in the standard library).
#
# TODO: Consider using lexemes (with POS) instead of lemmas.
#
MweTyp = FrozenSet[Tuple[Lemma, int]]


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
    return frozenset(Counter(mwe_typ))


def collect_data(input_paths: List[str]) -> List[TokenList]:
    """Retrieve all the sentences in the given input .cupt/.conllu files."""
    data_set = []  # type: List[TokenList]
    for input_path in input_paths:
        with open(input_path, "r", encoding="utf-8") as data_file:
            for sent in conllu.parse_incr(data_file):
                data_set.append(sent)
    return data_set


def filter_relevant_meta(sent: TokenList, keys: List[str]):
    """Keep only the metadata entries with the relevant `keys`."""
    meta = OrderedDict()
    for key in keys:
        if key in sent.metadata:
            meta[key] = sent.metadata[key]
    sent.metadata = meta


#################################################
# ESTIMATE
#################################################


def do_estimate(args):

    # Collect the dataset
    data_set = collect_data(args.input_paths)

    def avg_unseen_and_ratio(data_set, test_size):
        """Average no. of unseen MWEs and unseen/seen ratio."""
        uns_num_ratio = []
        for _ in range(args.random_num):
            test, train = random_split(data_set, test_size)
            uns_num_ratio.append(unseen_mwes(test, train))
        uns_num, uns_ratio = zip(*uns_num_ratio)
        return round(avg(uns_num)), avg(uns_ratio)

    # Perform binary search for an appropriate size of the test set
    p, q = 1, len(data_set)-1   # inclusive [p, q] range
    test_size, uns_num = None, None
    uns_rat = None
    while p < q:
        test_size = (p + q) // 2
        # Estimate the number of unseen MWEs
        uns_num, uns_rat = avg_unseen_and_ratio(data_set, test_size)
        # Reporting
        print(f"# test size {test_size} => {uns_num} unseen "
              f"& {uns_rat:f} unseen/seen ratio")
        # Consider smaller/larger test sizes
        if uns_num > args.uns_mwes:
            q = test_size - 1
        elif uns_num < args.uns_mwes:
            p = test_size + 1
        else:
            break

    # Report the final test size
    print(f"Entire data size: {len(data_set)}")
    print(f"Optimal test size: {test_size}")
    print(f"Average no. of unseen MWEs: {uns_num}")
    print(f"Average unseen/seen ratio: {uns_rat}")


#################################################
# SPLIT
#################################################


def do_split(args):

    # Determine the header line
    with open(args.input_paths[0], "r", encoding="utf-8") as data_file:
        header = data_file.readline().strip()

    # Collect the dataset
    data_set = collect_data(args.input_paths)

    # # Re-estimate the no. of unseen MWEs if --over is used, in which case
    # # only the splits with the unseen no. or MWEs over the provided no.
    # # are considered.
    # if args.over:
    #     nums = [
    #         unseen_mwes(*random_split(data_set, args.test_size))
    #         for _ in range(args.random_num)
    #     ]
    #     uns_mwes = round(avg(list(
    #         filter(lambda x: x >= args.uns_mwes, nums)
    #     )))
    #     print(f"# Target no. of unseen MWEs set to {uns_mwes} due to --over")
    # else:
    uns_mwes = args.uns_mwes
    target_ratio = args.uns_ratio

    def dist(uns_num, uns_rat):
        uns_dist = abs(uns_mwes - uns_num) / uns_mwes
        if target_ratio:
            rat_dist = abs(target_ratio - uns_rat) / target_ratio
            # print("uns_dist:", uns_dist)
            # print("rat_dist:", rat_dist)
            return uns_dist + rat_dist
        else:
            return uns_dist

    # Determine the best split
    train_fin = None
    test_fin = None
    uns_num_fin = None
    uns_rat_fin = None
    for _ in range(args.random_num):
        test, train = random_split(data_set, args.test_size)
        uns_num, uns_rat = unseen_mwes(test, train)
        replace = False
        if uns_num_fin is None:
            replace = True
        elif dist(uns_num, uns_rat) < dist(uns_num_fin, uns_rat_fin):
            replace = True
        if replace:
            print(f"# {uns_num} unseen & {uns_rat} unseen/seen ratio")
            train_fin, test_fin = train, test
            uns_num_fin = uns_num
            uns_rat_fin = uns_rat
        if not target_ratio and uns_num_fin == uns_mwes:
            break

    def write_to(data_set, file_path):
        print(f"Writing to {file_path}...")
        with open(file_path, "w", encoding="utf-8") as data_file:
            data_file.write(header + "\n")
            for sent in data_set:
                filter_relevant_meta(sent, RELEVANT_META)
                data_file.write(sent.serialize())

    print(f"Number of unseen MWEs in test: {uns_num_fin}")
    print(f"Unseen/seen MWE ratio in test: {uns_rat_fin}")

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

#!/usr/bin/env python3

from typing import Tuple, List, Iterable, FrozenSet, NamedTuple

import argparse
import random
import sys

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
# MWE TYPE
#################################################


# Lemma, or base form.
Lemma = str

# We represent MWE type as a mapping from Lemma's to their counts.  The mapping
# is represented as a set of (lemma, count) pairs (since there's no FrozenDict
# in the standard library).
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


#################################################
# GENERIC UTILS
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
# STATS
#################################################


class Stats(NamedTuple):
    seen: int
    unseen: int

    def __add__(self, other):
        return Stats(
            seen=self.seen + other.seen,
            unseen=self.unseen + other.unseen,
        )

    def __radd__(self, other):
        if other == 0:
            return self
        else:
            return self.__add__(other)

    def total(self):
        return self.seen + self.unseen


#################################################
# SPLITTING UTILS
#################################################


def types_in(sent: TokenList) -> List[MweTyp]:
    """MWE types in the given sentence."""
    # try:
    return [type_of(sent, mwe)
            for mwe in cupt.retrieve_mwes(sent).values()]
    # except Exception as inst:
    #     msg = f"ERROR: {inst}"
    #     sent_id = sent.metadata.get('source_sent_id') or \
    #         sent.metadata.get('sent_id')
    #     print(
    #         f"WARNING: ignoring sentence with id={sent_id} ({msg})",
    #         file=sys.stderr)


def stats_by_sent(test_set: TokenList, train_set: TokenList) \
        -> Iterable[Stats]:
    """Calculate the seen/unseen stats for each sentence in the given
    test set w.r.t the given train set.
    """
    train_types = set(
        typ
        for sent in train_set
        for typ in types_in(sent)
    )
    for test_sent in test_set:
        test_types = Counter(types_in(test_sent))
        all_num = sum(test_types[typ] for typ in test_types)
        seen_num = sum(
            test_types[typ]
            for typ in test_types
            if typ in train_types
        )
        unseen_num = all_num - seen_num
        yield Stats(seen_num, unseen_num)


def total_stats(test_set: TokenList, train_set: TokenList) -> Stats:
    """Calculate total `Stats` for the given test_set w.r.t. train_set."""
    return sum(stats_by_sent(test_set, train_set))


def unseen_num_and_ratio(test: TokenList, train: TokenList) \
        -> Tuple[int, float]:
    """Return unseen and unseen/all MWE stats."""
    stats = total_stats(test, train)
    return stats.unseen, stats.unseen / stats.total()


def split_wrt(
    data_set: TokenList,
    train_set: TokenList,
    unseen_num: int
) -> Tuple[TokenList, TokenList]:
    """Split the dataset into two parts (p1, p2) so that the number of
    unseen MWEs in p1 w.r.t `train_set` is closest to the target number.
    """
    p1, p2 = data_set, []
    stats_list = list(stats_by_sent(p1, train_set))
    n = sum(stats_list).unseen
    assert n >= unseen_num
    while n > unseen_num:
        sent, stats = p1.pop(), stats_list.pop()
        n -= stats.unseen
        p2.append(sent)
    return p1, p2


#################################################
# ESTIMATION
#################################################


def estimate(data_set, uns_mwes, random_num=10, verbose=False) \
        -> Tuple[int, int, float]:
    """Estimate the size of the test set so that test contains roughtly the
    given number of unseen expressions w.r.t the entire dataset - test set.

    Returns a tuple (test_size, avg_unseen_num, avg_unseen_ratio).
    """

    def avg_unseen_and_ratio(data_set, test_size):
        """Average no. of unseen MWEs and unseen/all ratio."""
        uns_num_ratio = []
        for _ in range(random_num):
            test, train = random_split(data_set, test_size)
            uns_num_ratio.append(unseen_num_and_ratio(test, train))
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
        if verbose:
            print(f"# size {test_size} => {uns_num} unseen "
                  f"& {uns_rat:f} unseen ratio")
        # Consider smaller/larger test sizes
        if uns_num > uns_mwes:
            q = test_size - 1
        elif uns_num < uns_mwes:
            p = test_size + 1
        else:
            break

    return test_size, uns_num, uns_rat

    # # Report the final test size
    # print(f"Entire data size: {len(data_set)}")
    # print(f"Optimal test size: {test_size}")
    # print(f"Average no. of unseen MWEs: {uns_num}")
    # print(f"Average unseen/all ratio: {uns_rat}")


#################################################
# SPLIT
#################################################


class Split(NamedTuple):
    train: List[TokenList]
    dev: List[TokenList]
    test: List[TokenList]


def make_split(data_set, dev_test_size, uns_mwes) -> Split:
    """Split the given dataset so the resulting test set has the given size
    and also the given number of unseen expressions.  If there are any
    remaining unseen MWEs, put them in the dev set."""
    test, train = random_split(data_set, dev_test_size)
    test, dev = split_wrt(test, train, uns_mwes)
    return Split(train, dev, test)


def grace(split: Split, target_test_uns, target_dev_uns) -> float:
    """How well the given split satisfy the given specification
    (no. of unseen MWEs in test and no. of unseen MWEs in dev).

    The result is a non-negative number, with 0 representing
    the best fit.
    """
    def test_dist(test_uns):
        return abs(target_test_uns - test_uns) / target_test_uns

    def dev_dist(dev_uns):
        return abs(target_dev_uns - dev_uns) / target_dev_uns

    test_uns = total_stats(split.test, split.train).unseen
    dev_uns = total_stats(split.dev, split.train).unseen
    return test_dist(test_uns) + dev_dist(dev_uns)

    # def dist(uns_num, uns_rat):
    #     uns_dist = abs(uns_mwes - uns_num) / uns_mwes
    #     if target_ratio:
    #         rat_dist = abs(target_ratio - uns_rat) / target_ratio
    #         # print("uns_dist:", uns_dist)
    #         # print("rat_dist:", rat_dist)
    #         return uns_dist + rat_dist
    #     else:
    #         return uns_dist


def find_split(
        data_set, dev_test_size, test_uns, dev_uns, random_num=10) -> Split:
    """Find the best split for the given specification.

    Arguments:
        test_size: target test size
        test_uns: target no. of unseen MWEs in test
        dev_uns: target no. of unseen MWEs in dev
        random_num: how many random splits to try
    """
    best_grace = float('inf')
    best_split = None
    for _ in range(random_num):
        split = make_split(data_set, dev_test_size, test_uns)
        new_grace = grace(split, test_uns, dev_uns)
        if new_grace < best_grace:
            best_grace = new_grace
            best_split = split
        if best_grace == 0:
            break
    return best_split


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
# parser_split.add_argument(
#     "--test-size",
#     dest="test_size",
#     type=int,
#     required=True,
#     help="Test size (# of sentences)"
# )
parser_split.add_argument(
    "--unseen-test",
    dest="test_uns",
    type=int,
    required=True,
    help="Target number of unseen MWEs in TEST"
)
parser_split.add_argument(
    "--unseen-dev",
    dest="dev_uns",
    type=int,
    required=True,
    help="Target number of unseen MWEs in DEV"
)
# parser_split.add_argument(
#     "--over",
#     dest="over",
#     action="store_true",
#     help="Only take splits with the number of unseen MWEs over --unseen-mwes"
# )
# parser_split.add_argument(
#     "--unseen-ratio",
#     dest="uns_ratio",
#     type=float,
#     required=False,
#     help="Target unseen/all ratio"
# )
parser_split.add_argument(
    "-n", "--random-num",
    dest="random_num",
    type=int,
    default=10,
    help="Number of random split; increase to get more reliable results"
)
parser_split.add_argument(
    "--train-path",
    dest="train_path",
    help="output TRAIN .cupt path",
    metavar="FILE"
)
parser_split.add_argument(
    "--test-path",
    dest="test_path",
    help="output TEST .cupt path",
    metavar="FILE"
)
parser_split.add_argument(
    "--dev-path",
    dest="dev_path",
    help="output DEV .cupt path",
    metavar="FILE"
)


#################################################
# DO ESTIMATE
#################################################


def do_estimate(args):
    data_set = collect_data(args.input_paths)
    test_size, uns_num, uns_rat = \
        estimate(data_set, args.uns_mwes, args.random_num)
    # Report the final test size
    print(f"Entire data size: {len(data_set)}")
    print(f"Optimal test size: {test_size}")
    print(f"Average no. of unseen MWEs: {uns_num}")
    print(f"Average unseen/all ratio: {uns_rat}")


#################################################
# DO SPLIT
#################################################


def do_split(args):

    # Determine the header line
    with open(args.input_paths[0], "r", encoding="utf-8") as data_file:
        header = data_file.readline().strip()

    # Collect the dataset
    print("# Read the input dataset...")
    data_set = collect_data(args.input_paths)

    # # Estimate the test size
    # print("# Estimate the test size...")
    # test_size, _, _ = estimate(
    #     data_set,
    #     args.test_uns,
    #     random_num=args.random_num,
    #     verbose=True,
    # )

    # Estimate the dev+test size
    print("# Estimate the dev+test size:")
    test_dev_size, _, _ = estimate(
        data_set,
        args.test_uns + args.dev_uns,
        random_num=args.random_num,
        verbose=True,
    )

    print("# Find the right split...")
    split = find_split(
        data_set, test_dev_size, args.test_uns,
        args.dev_uns, args.random_num,
    )

    print(f"Train size: {len(split.train)}")
    print(f"Dev size: {len(split.dev)}")
    print(f"Test size: {len(split.test)}")

    num, rat = unseen_num_and_ratio(split.test, split.train)
    print(f"Number of unseen MWEs in test: {num}")
    print(f"Unseen/all MWE ratio in test: {rat}")

    num, rat = unseen_num_and_ratio(split.dev, split.train)
    print(f"Number of unseen MWEs in dev: {num}")
    print(f"Unseen/all MWE ratio in dev: {rat}")

    def write_to(data_set, file_path):
        if file_path:
            print(f"# Writing to {file_path}...")
            with open(file_path, "w", encoding="utf-8") as data_file:
                data_file.write(header + "\n")
                for sent in data_set:
                    filter_relevant_meta(sent, RELEVANT_META)
                    data_file.write(sent.serialize())

    write_to(split.train, args.train_path)
    write_to(split.dev, args.dev_path)
    write_to(split.test, args.test_path)


#################################################
# MAIN
#################################################


if __name__ == '__main__':
    args = parser.parse_args()
    if args.command == 'estimate':
        do_estimate(args)
    elif args.command == 'split':
        do_split(args)

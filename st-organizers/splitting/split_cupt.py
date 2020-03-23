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
# RELEVANT_META = ['source_sent_id', 'text']

# Discard metadata with the following keys
DISCARD_META = ['metadata']


# Vaid MWEs categories
VALID_CATS = [
    'VID',
    'LVC.full', 'LVC.cause',
    'IRV',
    'VPC.full', 'VPC.semi',
    'IAV',
    'MVC'
]
NOT_MWE = 'NotMWE'
LANG_SPEC_PREF = "LS."


#################################################
# MWE TYPE
#################################################


# Lemma, or base form.
Lemma = str

# We represent MWE type as a mapping from Lemma's to their counts.  The mapping
# is represented as a set of (lemma, count) pairs (since there's no FrozenDict
# in the standard library).
MweTyp = FrozenSet[Tuple[Lemma, int]]


def lemma_or_form(tok: OrderedDict) -> str:
    """Retrieve the lemma of the given token, falling back to the form
    if the lemma is not specified.
    """
    lema = tok['lemma']
    if lema == '_':
        return tok['form']
    else:
        return lema


def type_of(sent: TokenList, mwe: cupt.MWE) -> MweTyp:
    """Convert the given MWE instance to the corresponding MWE type."""
    # Create a dictionary from token IDs to actual tokens
    tok_map = {}
    for tok in sent:
        tok_map[tok['id']] = tok
    # Retrieve the set of lemmas
    mwe_typ = [
        lemma_or_form(tok_map[tok_id])
        for tok_id in mwe.span
    ]
    return frozenset(Counter(mwe_typ).most_common())


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
                try:
                    preprocess(sent)
                    data_set.append(sent)
                except Exception as inst:
                    msg = f"ERROR: {inst}"
                    sid = sent.metadata.get('source_sent_id') or \
                        sent.metadata.get('sent_id')
                    print(
                        f"WARNING: ignoring sentence with id={sid} ({msg})",
                        file=sys.stderr)
    return data_set


# def filter_relevant_meta(sent: TokenList, keys: List[str]):
#     """Keep only the metadata entries with the relevant `keys`."""
#     meta = OrderedDict()
#     for key in keys:
#         if key in sent.metadata:
#             meta[key] = sent.metadata[key]
#     sent.metadata = meta


def valid_mwe_cat(cat) -> bool:
    """Is the given MWE category valid?"""
    return cat in VALID_CATS or \
        cat.startswith(LANG_SPEC_PREF) or \
        cat == NOT_MWE


def preprocess(sent: TokenList):
    """Perform preliminary sentence pre-processing (in-place)."""
    # filter_relevant_meta(sent, RELEVANT_META)
    discard_meta(sent, DISCARD_META)
    check_mwe_cats(sent)
    return sent


def check_mwe_cats(sent: TokenList):
    """Discard MWEs with invalid cats and NotMWEs."""
    # Retrieve MWEs, discard MWE IDs
    mwes = cupt.retrieve_mwes(sent).values()
    # Construct the new set of MWEs
    new_mwes = []
    for mwe in mwes:
        if valid_mwe_cat(mwe.cat):
            if mwe.cat != NOT_MWE:
                new_mwes.append(mwe)
        else:
            print(f"# WARNING: invalid {mwe} in {sent}")
    # Replace MWEs in place
    cupt.replace_mwes(sent, new_mwes)


def discard_meta(sent: TokenList, keys: List[str]):
    """Discard (in-place) metadata entries with the given `keys`."""
    for key in keys:
        if key in sent.metadata:
            del sent.metadata[key]


def duplicate_mwes(sent: TokenList) -> List[cupt.MWE]:
    # List of duplicates
    dups = []

    # Freeze MWE's span (so we can compare them)
    def freeze(span):
        return frozenset(span)
        # return tuple(sorted(span))

    # Retrieve MWEs, discard MWE IDs
    mwes = cupt.retrieve_mwes(sent).values()
    spans = Counter(freeze(mwe.span) for mwe in mwes)
    for mwe in mwes:
        if spans[freeze(mwe.span)] > 1:
            dups.append(mwe)
    return dups


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

    # def __radd__(self, other):
    #     if other == 0:
    #         return self
    #     else:
    #         return self.__add__(other)

    def total(self):
        """Total number of MWEs"""
        return self.seen + self.unseen

    def unseen_ratio(self):
        """Unseen/all MWE ratio"""
        return self.unseen / self.total()


def zero_stats() -> Stats:
    """0 stats"""
    return Stats(0, 0)


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


def has_mwe(sent: TokenList) -> bool:
    """Does the given sentence has any MWE?"""
    return len(types_in(sent)) > 0


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
    return sum(stats_by_sent(test_set, train_set), zero_stats())


def unseen_num_and_ratio(test: TokenList, train: TokenList) \
        -> Tuple[int, float]:
    """Return unseen and unseen/all MWE stats."""
    stats = total_stats(test, train)
    return stats.unseen, stats.unseen / stats.total()


#################################################
# OBSOLETE SPLITTING METHODS
#################################################


def split_wrt_core(
    data_set: TokenList,
    train_set: TokenList,
    unseen_num: int
) -> Tuple[TokenList, TokenList]:
    """Split the dataset into two parts (p1, p2) so that the number of
    unseen MWEs in p1 w.r.t `train_set` is closest to the target number.
    """
    p1, p2 = data_set[:], []    # note the shallow copy
    stats_list = list(stats_by_sent(p1, train_set))
    n = sum(stats_list, zero_stats()).unseen
    assert n >= unseen_num
    while n > unseen_num:
        sent, stats = p1.pop(), stats_list.pop()
        n -= stats.unseen
        p2.append(sent)
    return p1, p2


def split_wrt(
    data_set: TokenList,
    train_set: TokenList,
    unseen_num: int
) -> Tuple[TokenList, TokenList]:
    """A wrapper over split_wrt_core which considers sentences without MWEs
    separately from those with MWEs.
    """
    with_mwes = [x for x in data_set if has_mwe(x)]
    wout_mwes = [x for x in data_set if not has_mwe(x)]
    with_p1, with_p2 = split_wrt_core(with_mwes, train_set, unseen_num)
    # print("with, wout:", len(with_mwes), len(wout_mwes))
    # print("with_p1, with_p2:", len(with_p1), len(with_p2))
    # Split the part without MWEs to have similar proportions
    prop = len(with_p1) / len(with_mwes)
    k = round(prop * len(wout_mwes))
    # print("prop, k, wout_mwes:", prop, k, len(wout_mwes))
    wout_p1, wout_p2 = wout_mwes[:k], wout_mwes[k:]
    # Combine the parts with and without MWEs
    p1 = with_p1 + wout_p1
    p2 = with_p2 + wout_p2
    # print("p1:", len(p1))
    # print("p2:", len(p2))
    # Shuffle them in-place and return
    random.shuffle(p1)
    random.shuffle(p2)
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


#################################################
# 3-WAY SPLIT
#################################################


class Split(NamedTuple):
    train: List[TokenList]
    dev: List[TokenList]
    test: List[TokenList]


# def make_split(data_set, dev_test_size, uns_mwes) -> Split:
#     """Split the given dataset so the resulting test set has the given size
#     and also the given number of unseen expressions.  If there are any
#     remaining unseen MWEs, put them in the dev set."""
#     test, train = random_split(data_set, dev_test_size)
#     test, dev = split_wrt(test, train, uns_mwes)
#     return Split(train, dev, test)


class SplitSpec(NamedTuple):
    """Target specification"""
    target_test_uns: int        # Target no. of unseen MWEs in test
    target_dev_uns: int         # Target no. of unseen MWEs in dev
    target_uns_ratio: float     # Target unseen/all MWE ratio in both dev/test


def grace(split: Split, spec: SplitSpec) \
        -> float:
    """How well the given split satisfy the given specification
    (no. of unseen MWEs in test and no. of unseen MWEs in dev).
    The unseen ratio should be also roughtly the same in dev and test.

    The result is a non-negative number, with 0 representing
    the best fit.
    """
    def test_dist(test_uns):
        return abs(spec.target_test_uns - test_uns) / spec.target_test_uns

    def dev_dist(dev_uns):
        return abs(spec.target_dev_uns - dev_uns) / spec.target_dev_uns

    test = total_stats(split.test, split.train)
    dev = total_stats(split.dev, split.train)
    return test_dist(test.unseen) + dev_dist(dev.unseen) + \
        abs(test.unseen_ratio() - dev.unseen_ratio()) + \
        abs(test.unseen_ratio() - spec.target_uns_ratio)


def find_split(
        data_set, dev_test_size,
        spec: SplitSpec,
        random_num=10, random_subnum=10) -> Split:
    """Find the best split for the given specification.

    Arguments:
        test_size: target test size
        test_uns: target no. of unseen MWEs in test
        dev_uns: target no. of unseen MWEs in dev
        uns_ratio: target unseen/all MWE ratio
        random_num: how many random splits to try
        random_subnum: how many random (dev/test) subsplits to try
    """
    best_grace = float('inf')
    best_split = None
    for _ in range(random_num):
        # split = make_split(data_set, dev_test_size, test_uns)
        dev_test, train = random_split(data_set, dev_test_size)
        for _ in range(random_subnum):
            random.shuffle(dev_test)
            test, dev = split_wrt(dev_test, train, spec.target_test_uns)
            split = Split(train=train, dev=dev, test=test)
            new_grace = grace(split, spec)
            if new_grace < best_grace:
                best_grace = new_grace
                best_split = split
            if best_grace == 0:
                break
    return best_split


#################################################
# 2-WAY SPLIT
#################################################


class TwoSplitSpec(NamedTuple):
    """Target specification"""
    target_uns: int             # Target no. of unseen MWEs
    target_uns_ratio: float     # Target unseen/all MWE ratio


def grace_two(
    target: List[TokenList],
    rest: List[TokenList],
    spec: TwoSplitSpec,
) -> float:
    """How well the given 2-way split satisfies the given specification.

    The result is a non-negative number, with 0 representing
    the best fit.
    """
    stats = total_stats(target, rest)
    uns = stats.unseen
    uns_ratio = stats.unseen_ratio()
    dists = [
        abs(spec.target_uns - uns) / spec.target_uns,
        abs(uns_ratio - spec.target_uns_ratio),
    ]
    return sum(dists)


def find_two_split(
        data_set, target_size,
        spec: TwoSplitSpec,
        random_num=10) -> Tuple[List[TokenList], List[TokenList]]:
    """Find the best split for the given specification.

    Arguments:
        test_size: target test size
        test_uns: target no. of unseen MWEs in test
        dev_uns: target no. of unseen MWEs in dev
        uns_ratio: target unseen/all MWE ratio
        random_num: how many random splits to try
        random_subnum: how many random (dev/test) subsplits to try
    """
    best_grace = float('inf')
    best_split = None
    for _ in range(random_num):
        target, rest = random_split(data_set, target_size)
        new_grace = grace_two(target, rest, spec)
        if new_grace < best_grace:
            best_grace = new_grace
            best_split = rest, target
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
    "--alt",
    dest="alt",
    action="store_true",
    help="Alternative split: unseen in test are calculated w.r.t. train+dev"
)
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
    "-m", "--random-subnum",
    dest="random_subnum",
    type=int,
    default=10,
    help=("Perform each (random) subsplit into DEV/TEST "
          "the given number of times")
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

parser_check = subparsers.add_parser('check', help='check the split')
parser_check.add_argument(
    "-o",
    dest="orig_paths",
    required=True,
    nargs='+',
    help="original .cupt file(s)",
    metavar="FILE"
)
parser_check.add_argument(
    "-s",
    dest="split_paths",
    required=True,
    nargs='+',
    help="split .cupt file(s)",
    metavar="FILE"
)

parser_dupl = subparsers.add_parser(
    'dupl', help='check for duplicate annotations')
parser_dupl.add_argument(
    "-i",
    dest="input_paths",
    required=True,
    nargs='+',
    help="original .cupt file(s)",
    metavar="FILE"
)

parser_stats = subparsers.add_parser(
    'stats', help='split statistics')
parser_stats.add_argument(
    "--train-path",
    dest="train_paths",
    required=True,
    nargs='+',
    help="train .cupt file(s)",
    metavar="FILE"
)
parser_stats.add_argument(
    "--test-path",
    dest="test_paths",
    required=True,
    nargs='+',
    help="test .cupt file(s)",
    metavar="FILE"
)
parser_stats.add_argument(
    "--dev-path",
    dest="dev_paths",
    required=True,
    nargs='+',
    help="dev .cupt file(s)",
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

    # Estimate the dev+test size
    print("# Estimate the dev+test size:")
    test_dev_size, _, uns_ratio = estimate(
        data_set,
        args.test_uns + args.dev_uns,
        random_num=args.random_num,
        verbose=True,
    )

    # Split specification
    spec = SplitSpec(
        target_test_uns=args.test_uns,
        target_dev_uns=args.dev_uns,
        target_uns_ratio=uns_ratio
    )

    print("# Find the right split...")
    split = find_split(
        data_set, test_dev_size, spec,
        # args.test_uns, args.dev_uns,
        # uns_ratio,
        args.random_num, args.random_subnum
    )

    # Reports stats, and write on output
    report_stats(split)
    write_split(split, args, header)


#################################################
# DO SPLIT UTILS
#################################################


def report_stats(split: Split):
    """Report some statistics of the split."""

    print(f"# Number of sentences")
    print(f"Train size: {len(split.train)}")
    print(f"Dev size: {len(split.dev)}")
    print(f"Test size: {len(split.test)}")

    print(f"# Train")
    train_stats = total_stats(split.train, [])
    print(f"Number of MWEs in train: {train_stats.total()}")

    def uns_ratio(stats):
        """Unseen/all MWE ratio"""
        return stats.unseen / stats.total()

    print(f"# Dev")
    dev_stats = total_stats(split.dev, split.train)
    print(f"Number of MWEs in dev: {dev_stats.total()}")
    print(f"Number of unseen MWEs in dev: {dev_stats.unseen}")
    print(f"Unseen/all MWE ratio in dev: {uns_ratio(dev_stats)}")

    print(f"# Test")
    test_stats = total_stats(split.test, split.train)
    print(f"Number of MWEs in test: {test_stats.total()}")
    print(f"Number of unseen MWEs in test w.r.t train: {test_stats.unseen}")
    print(f"Unseen/all MWE ratio in test w.r.t train: {uns_ratio(test_stats)}")

    test_stats2 = total_stats(split.test, split.train+split.dev)
    print(
        f"Number of unseen MWEs in test "
        f"w.r.t train+dev: {test_stats2.unseen}"
    )
    print(
        f"Unseen/all MWE ratio in test "
        f"w.r.t train+dev: {uns_ratio(test_stats2)}"
    )


def write_split(split: Split, args, header):
    """Write the split to output files with the given header.

    TODO: refactor.
    """

    def write_to(data_set, file_path):
        if file_path:
            print(f"# Writing to {file_path}...")
            with open(file_path, "w", encoding="utf-8") as data_file:
                data_file.write(header + "\n")
                for sent in data_set:
                    data_file.write(sent.serialize())

    write_to(split.train, args.train_path)
    write_to(split.dev, args.dev_path)
    write_to(split.test, args.test_path)


#################################################
# DO ALTERNATIVE SPLIT
#################################################


def do_alt_split(args):

    # Determine the header line
    with open(args.input_paths[0], "r", encoding="utf-8") as data_file:
        header = data_file.readline().strip()

    # Collect the dataset
    print("# Read the input dataset...")
    data_set = collect_data(args.input_paths)

    # Estimate the dev+test size
    print("# Estimate the test size:")
    test_size, _, test_uns_ratio = estimate(
        data_set,
        args.test_uns,
        random_num=args.random_num,
        verbose=True,
    )

    print("# Find the right train+dev/test split...")
    spec = TwoSplitSpec(
        target_uns=args.test_uns,
        target_uns_ratio=test_uns_ratio
    )
    train_dev, test = find_two_split(
        data_set, test_size, spec,
        args.random_num
    )

    print("# Estimate the dev size:")
    dev_size, _, dev_uns_ratio = estimate(
        train_dev,
        args.dev_uns,
        random_num=args.random_num,
        verbose=True,
    )

    print("# Find the right train/dev split...")
    spec = TwoSplitSpec(
        target_uns=args.dev_uns,
        target_uns_ratio=dev_uns_ratio
    )
    train, dev = find_two_split(
        train_dev, dev_size, spec,
        args.random_num
    )

    # Create the resulting split, reports stats, and write on output
    split = Split(train=train, dev=dev, test=test)
    report_stats(split)
    write_split(split, args, header)


#################################################
# DO CHECK
#################################################


def do_check(args):
    print("# Read the original dataset...")
    orig = collect_data(args.orig_paths)
    print("# Read the split dataset...")
    split = collect_data(args.split_paths)

    def prepare(x: TokenList) -> str:
        """Prepare the sentence for comparison"""
        if 'global.columns' in x.metadata:
            del x.metadata['global.columns']
        return x.serialize()

    # Serialize the datasets, otherwise we cannot compare
    split = list(map(prepare, split))
    orig = list(map(prepare, orig))

    # Sort the two lists
    split.sort()
    orig.sort()

    # Check the length
    if len(split) != len(orig):
        print("# WARNING: the lengths of the two datasets differ")

    problem = False
    for x, y in zip(orig, split):
        if x != y:
            problem = True
            print("# WARNING: the following sentences differ:\n")
            print("@ ORIGINAL")
            print(x, end='')
            print("@ SPLIT")
            print(y, end='')
    if not problem:
        print("Datasets identical")
    else:
        print("Datasets differ")


#################################################
# DO CHECK FOR DUPLICATES
#################################################


def do_check_duplicates(args):
    # print("# Read the input dataset...")
    data_set = collect_data(args.input_paths)
    for sent in data_set:
        mwes = duplicate_mwes(sent)
        if mwes:
            sid = sent.metadata.get('source_sent_id') or \
                '"' + sent.metadata.get('text') + '"'
            print(
                f"Duplicate annotations in sentence {sid}:",
                mwes
            )


#################################################
# DO STATS
#################################################


def do_stats(args):
    train = collect_data(args.train_paths)
    dev = collect_data(args.dev_paths)
    test = collect_data(args.test_paths)
    split = Split(train=train, dev=dev, test=test)
    report_stats(split)


#################################################
# MAIN
#################################################


if __name__ == '__main__':
    args = parser.parse_args()
    if args.command == 'estimate':
        do_estimate(args)
    elif args.command == 'split':
        if args.alt:
            do_alt_split(args)
        else:
            do_split(args)
    elif args.command == 'check':
        do_check(args)
    elif args.command == 'dupl':
        do_check_duplicates(args)
    elif args.command == 'stats':
        do_stats(args)

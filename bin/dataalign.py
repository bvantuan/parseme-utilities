#! /usr/bin/env python3

r"""
This is a library for reading FoLiA XML files aligned with a CoNLL file.
The XML files may have PARSEME annotations, and this library can be helpful
in dealing with such data. In particular:

  * If you want to homogenize word lemmas, add special code to `_fix_token`
    (e.g. to re-lemmatize "me" and "te" as "se" in Romance languages).

  * If you want to re-order an expression, add special code to `_reorder_tokens`.
    (e.g. reordering the LVC "(a) bath (was) taken" as "take bath").

This library requires PyNLPl to be installed.
"""


import collections
import itertools
import os
import sys


try:
    from pynlpl.formats import folia
except ImportError:
    print("ERROR: PyNLPl not found, please install pynlpl (pip install pynlpl)", file=sys.stderr)
    sys.exit(2)


# The `empty` field in CoNLL-U and PARSEME-TSV
EMPTY = "_"

# Set of all valid languages in PARSEME'2016
LANGS = set("BG CS DE EL EN ES FA FR HE HR HU IT LT MT PL PT RO SE SL TR YI".split())

# Languages where the LVC is "VERB NOUN", and "NOUN blabla VERB" should be re-ordered
LANGS_WITH_STANDARD_LVCS = set("BG CS DE EL EN ES FA FR HE HR HU IT LT MT PL PT RO SE SL TR YI".split())  # XXX CHEKME

# Languages where the pronoun in IReflV is on the left
LANGS_WITH_REFL_PRON_ON_LEFT = set("DE FR RO".split())


############################################################

class Comment(collections.namedtuple('Comment', 'file_path lineno text')):
    r"""Represents a comment in the CoNLL-U file."""


class MWEAnnot(collections.namedtuple('MWEAnnot', 'indexes category')):
    r"""Represents an MWE annotation.
    @type indexes: tuple[int]
    @type category: str
    """


class Token(collections.namedtuple('Token', 'rank surface nsp lemma univ_pos')):
    r"""Represents a token in an input file.

    Arguments:
    @rank: str
    @surface: str
    @nsp: bool
    @lemma: Optional[str]
    @univ_pos: Optional[str]
    """
    def lemma_or_surface(self):
        return self.lemma or self.surface


class Sentence:
    r"""A sequence of tokens."""
    def __init__(self, file_path, nth_sent, lineno):
        self.file_path = file_path
        self.nth_sent = nth_sent
        self.lineno = lineno
        self.tokens = []
        self.mweannots = []  # list[MWEAnnot]
        self.mwe_id2folia = {}  # extra info per MWE from FoLiA file

    def mwe_occurs(self, lang):
        r"""Yield MWEOccur instances for all MWEs in self."""
        for mwe_id, mweannot in enumerate(self.mweannots, 1):
            annotator, confidence, datetime, comments = None, None, None, []
            if mwe_id in self.mwe_id2folia:
                F = self.mwe_id2folia[mwe_id]
                annotator, confidence, datetime = F.annotator, F.confidence, F.datetime
                comments = [c.value for c in F.select(folia.Comment)]

            yield MWEOccur(lang, self, mweannot.indexes, mweannot.category,
                    comments, annotator, confidence, datetime)

    def tokens_and_mwecodes(self):
        r"""Yield pairs (token, mwecode)."""
        tokenindex2mweindex = collections.defaultdict(list)
        for mweindex, mweannot in enumerate(self.mweannots):
            for index in mweannot.indexes:
                tokenindex2mweindex[index].append(mweindex)

        for i, token in enumerate(self.tokens):
            mwe_is = tokenindex2mweindex[i]
            yield token, [self._mwecode(i, mwe_i) for mwe_i in mwe_is]

    def _mwecode(self, token_i, mwe_i):
        r"""Return a string with mweid:category (or just mweid in some cases)."""
        mweannot = self.mweannots[mwe_i]
        if mweannot.category and mweannot.indexes[0] == token_i:
            return "{}:{}".format(mwe_i+1, mweannot.category)
        return str(mwe_i+1)

    def remove_non_vmwes(self):
        r"""Change the mwe_codes in `self.tokens` so as to remove all NonVMWE tags."""
        self.mweannots = [m for m in self.mweannots if m.category != "NonVMWE"]




class MWEOccur:
    r"""Represents an instance of a MWE in text."""
    def __init__(self, lang, sentence, indexes, category, comments, annotator, confidence, datetime):
        assert lang in LANGS
        self.lang = lang
        self.sentence = sentence
        self.indexes = indexes
        self.category = category
        self.comments = comments
        self.annotator = annotator
        self.confidence = confidence
        self.datetime = datetime

        self.raw = MWETokens(self, (sentence.tokens[i] for i in indexes))
        self.fixed = self.raw._with_fixed_tokens()
        self.reordered = self.fixed._with_reordered_tokens()

        assert all(t.rank == tf.rank for (t, tf) in zip(self.raw.tokens,
                self.fixed.tokens)), "BUG: _with_fixed_tokens must preserve order"
        assert set(self.reordered.tokens) == set(self.fixed.tokens), \
                "BUG: _with_reordered_tokens must not change word attributes"


    def __repr__(self):
        return "MWEOccur<{}>".format(" ".join(self.reordered.mwe_canonical_form))


class MWETokens:
    def __init__(self, mwe_occur, iter_tokens):
        self.mwe_occur = mwe_occur
        self.tokens = tuple(iter_tokens)
        assert all(isinstance(t, Token) for t in self.tokens), self.tokens
        self.i_head = self._i_head()        # Index of head verb
        self.i_subhead = self._i_subhead()  # Index of sub-head noun (e.g. LVCs)
        self.head = self.tokens[self.i_head]
        self.subhead = self.tokens[self.i_subhead] if (self.i_subhead is not None) else None
        self.mwe_canonical_form = self._mwe_canonical_form()

    def _i_head(self):
        r"""Index of head verb in `mwe_canonical_form`
        (First word if there is no POS info available)."""
        i_verbs = [i for (i, t) in enumerate(self.tokens) if t.univ_pos == "VERB"] or [0]
        return i_verbs[0]  # just take first verb that appears

    def _i_subhead(self):
        r"""Index of sub-head noun in `mwe_canonical form` (very useful for LVCs)."""
        i_nouns = tuple(i for (i, t) in enumerate(self.tokens) if t.univ_pos == "NOUN")
        if not i_nouns: return None
        # We look for the first noun that is not the modifier in a noun compound
        head_nouns = [i for i in i_nouns if (i==len(self.tokens)-1 or self.tokens[i+1] != "NOUN")]
        return head_nouns[0]

    def _i_reflpron(self):
        r"""Return the reflexive pronoun (for IReflV), or None."""
        return next((i for (i, t) in enumerate(self.tokens) if t.univ_pos == "PRON"), None)

    def _mwe_canonical_form(self):
        r"""Return a lemmatized form of this MWE."""
        indexes = [self.i_head, self.i_subhead, self._i_reflpron()]
        return self._lemmatized_at([i for i in indexes if i is not None])


    def _lemmatized_at(self, indexes):
        r"""Return surfaces in self.tokens, lemmatized at given indexes."""
        ret = [t.surface for t in self.tokens]
        for i in indexes:
            ret[i] = self.tokens[i].lemma_or_surface()
        return [x.casefold() for x in ret]


    def _with_fixed_tokens(self):
        r"""Return a fixed version of `self.tokens` (must keep same length & order)."""
        fixed = tuple(self._fixed_token(t) for t in self.tokens)
        return MWETokens(self.mwe_occur, fixed)

    def _fixed_token(self, token):
        r"""Return a manually fixed version of `token` (e.g. homogenize lemmas for IReflV)."""
        if token.univ_pos == "PRON" and self.mwe_occur.category == "IReflV":
            if self.mwe_occur.lang in ["PT", "ES", "FR"]:
                token = token._replace(lemma="se")
            if self.mwe_occur.lang == "IT":
                token = token._replace(lemma="si")
        return token


    def _with_reordered_tokens(self):
        r"""Return a reordered version of `tokens` (must keep same length)."""
        lang, category = self.mwe_occur.lang, self.mwe_occur.category
        T, newT, iH, iS = self.tokens, list(self.tokens), self.i_head, self.i_subhead
        if category == "LVC":
            if iS is None: iS = len(T)-1
            if iS < iH and lang in LANGS_WITH_STANDARD_LVCS:
                newT[iH], newT[iS] = T[iS], T[iH]

        if category == "IReflV":
            iPron, iVerb = ((0,-1) if (lang in LANGS_WITH_REFL_PRON_ON_LEFT) else (-1,0))
            if T[iVerb].univ_pos == "PRON" and T[iPron].univ_pos == "VERB":
                newT[iVerb], newT[iPron] = T[iPron], T[iVerb]

        return MWETokens(self.mwe_occur, newT)



############################################################

def calculate_conllu_paths(file_paths, warn=True):
    r"""Return CoNLL-U paths, or None on failure to find some of them."""
    ret = []
    for file_path in file_paths:
        if file_path.endswith(".folia.xml"):
            base = file_path.rsplit(".", 2)[0]
        elif any(file_path.endswith(x) for x in [".tsv", ".parsemetsv", ".xml"]):
            base = file_path.rsplit(".", 1)[0]
        else:
            exit("ERROR: unknown file extension for `{}`".format(file_path))

        ret_path = base + ".conllu"
        if os.path.exists(ret_path):
            print("INFO: Using CoNNL-U file `{}`".format(ret_path), file=sys.stderr)
            ret.append(ret_path)

        elif warn:
            print("WARNING: CoNLL-U file `{}` not found".format(ret_path), file=sys.stderr)
            print("WARNING: not using any CoNLL-U file", file=sys.stderr)
            return None
    return ret


def iter_aligned_files(file_paths, conllu_paths=None, keep_nvmwes=False, debug=False):
    r"""iter_aligned_files(list[str], list[str]) -> Iterable[Either[Sentence,Comment]]
    Yield Sentence's & Comment's based on file_paths and conllu_paths.
    """
    chain_iter = itertools.chain.from_iterable
    main_iterator = chain_iter(_iter_parseme_file(p) for p in file_paths)
    if conllu_paths:
        conllu_iterator = chain_iter(ConllIterator(p) for p in conllu_paths)
        main_iterator = AlignedIterator(main_iterator, conllu_iterator, debug)

    for sentence in main_iterator:
        if not keep_nvmwes:
            sentence.remove_non_vmwes()
        yield sentence


def _iter_parseme_file(file_path):
    if file_path.endswith('.xml'):
        return FoliaIterator(file_path)
    if "Platinum" in file_path:
        return ParsemePlatinumIterator(file_path)
    else:
        return ParsemeTSVIterator(file_path)


class AlignedIterator:
    r"""Yield Sentence's & Comment's based on the given iterators."""
    def __init__(self, main_iterator, conllu_iterator, debug=False):
        self.main_iterator = main_iterator
        self.conllu_iterator = conllu_iterator
        self.main = collections.deque(main_iterator)
        self.conllu = collections.deque(conllu_iterator)
        self.debug = debug

    def __iter__(self):
        while True:
            yield from self.align_sents()
            if not self.main and not self.conllu:
                break
            main_s = self.main.popleft()
            conllu_s = self.conllu.popleft()
            main_s.tokens = list(self.merge_sentences(main_s, conllu_s))
            yield main_s


    def merge_sentences(self, main_sentence, conllu_sentence):
        for (info, tokens) in TokenAligner(main_sentence, conllu_sentence):
            if info in ["EQUAL", "CONLL:EXTRA"]:
                yield from tokens

            if self.debug and info == "CONLL:EXTRA":
                print("{}:{}: DEBUG: Adding tokens from CoNLL: {!r} with rank {!r}".format(
                        conllu_sentence.file_path, conllu_sentence.lineno,
                        [t.surface for t in tokens], [t.rank for t in tokens]),
                        file=sys.stderr)


    def align_sents(self):
        while self.conllu and isinstance(self.conllu[0], Comment):
            yield self.conllu.popleft()
        if self.conllu and not self.main:
            err_badline(self.conllu[0].file_path, self.conllu[0].lineno,
                    "CoNLL-U sentence #{} found, but there is no matching PARSEME input file"
                    .format(self.conllu[0].nth_sent))
        if self.main and not self.conllu:
            err_badline(self.main[0].file_path, "??",
                    "PARSEME sentence #{} found, but there is no matching CoNLL-U input file"
                    .format(self.main[0].nth_sent))



class TokenAligner:
    def __init__(self, main_sentence, conllu_sentence):
        self.main_sentence = main_sentence
        self.conllu_sentence = conllu_sentence
        import difflib
        main_surf = [t.surface for t in main_sentence.tokens]
        conllu_surf = [t.surface for t in conllu_sentence.tokens]
        sm = difflib.SequenceMatcher(None, main_surf, conllu_surf)
        self.matches_end = sm.get_matching_blocks()
        self.matches_beg = [(0, 0, 0)] + self.matches_end


    def __iter__(self):
        r"""Yield pairs (str, list[Token])."""
        # Main: [ok ok ok ok ok...ok ok ok] gap_main [ok ok ok ok...
        #       ^position=main1                      ^position=main2
        #       ^-------------size1-------^
        for (main1,conll1,size1), (main2,conll2,_) in zip(self.matches_beg, self.matches_end):
            yield ("EQUAL", self.conllu_sentence.tokens[conll1:conll1+size1])
            gap_main = (main2 - (main1+size1))
            gap_conll = (conll2 - (conll1+size1))
            range_gap_main = range(main1+size1, main2)
            range_gap_conll = range(conll1+size1, conll2)

            if gap_main:
                affected_mweids = [i+1 for (i, m) in enumerate(self.main_sentence.mweannots) \
                        if any((gapword_index in m.indexes) for gapword_index in range_gap_main)]
                self.warn_gap_main(range_gap_main, range_gap_conll, affected_mweids)

            if gap_conll:
                # Probably a range, or a sub-word inside a range
                yield ("CONLL:EXTRA", [self.conllu_sentence.tokens[i] for i in range_gap_conll])


    def warn_gap_main(self, main_range, conllu_range, all_mwe_codes):
        r"""Warn when there are unmapped characters in main file."""
        lineno_str = " (line {})".format(self.main_sentence.lineno) \
                if self.main_sentence.lineno else ""

        if len(main_range) > 10:  # hard-coded magic to detect missing sentences
            err_badline(self.conllu_sentence.file_path, self.conllu_sentence.lineno,
                    "CoNLL-U sentence does not match sentence #{} in `{}`{}" \
                    .format(self.main_sentence.nth_sent, self.main_sentence.file_path, lineno_str))

        main_toks = [self.main_sentence.tokens[i].surface for i in main_range]
        #conllu_toks = [self.conllu_sentence.tokens[i].surface for i in conllu_range]

        mwe_codes_info = " (MWEs={})".format(";".join(all_mwe_codes)) if all_mwe_codes else ""
        print("{}{}: WARNING: Ignoring extra tokens in sentence #{}: {!r}{}"
                .format(self.main_sentence.file_path, lineno_str,
                self.main_sentence.nth_sent, main_toks, mwe_codes_info), file=sys.stderr)


############################################################

class FoliaIterator:
    r"""Yield Sentence's for file_path."""
    def __init__(self, file_path):
        self.file_path = file_path

    def __iter__(self):
        doc = folia.Document(file=self.file_path)
        for text in doc:
            for nth,folia_sentence in enumerate(text, 1):
                current_sentence = Sentence(self.file_path, nth, None)
                folia_mwe_layers = folia_sentence.layers(folia.EntitiesLayer)
                mwes = [mwe for mlayer in folia_mwe_layers for mwe in mlayer]
                current_sentence.mweannots = list(self.calc_mweannots(mwes))

                for rank, word in enumerate(folia_sentence.words(), 1):
                    token = Token(str(rank), word.text(), (not word.space), None, None)
                    current_sentence.tokens.append(token)

                current_sentence.mwe_id2folia = dict(enumerate(mwes, 1))
                yield current_sentence


    def calc_mweannots(self, mwes):
        for mwe in mwes:
            words = mwe.select(folia.Word)
            indexes = [int(w.id.rsplit(".",1)[-1]) - 1 for w in words]
            yield MWEAnnot(indexes, mwe.cls)



class AbstractFileIterator:
    def __init__(self, file_path):
        self.file_path = file_path
        self.nth_sent = 0
        self.lineno = 0
        self._new_sent()

    def _new_sent(self):
        self.curr_sent = None
        self.id2mwe_categ = {}
        self.id2mwe_indexes = collections.defaultdict(list)

    def finish_sentence(self):
        r"""Return finished `self.curr_sent`."""
        s = self.curr_sent
        s.mweannots = [MWEAnnot(tuple(self.id2mwe_indexes[id]),
            self.id2mwe_categ[id]) for id in sorted(self.id2mwe_indexes)]
        self._new_sent()
        return s

    def err(self, msg):
        err_badline(self.file_path, self.lineno, msg)

    def make_comment(self, line):
        if self.curr_sent:
            self.err("Comment in the middle of a sentence is not allowed")
        return Comment(self.file_path, self.lineno, line[1:].strip())

    def append_token(self, line):
        if not self.curr_sent:
            self.nth_sent += 1
            self.curr_sent = Sentence(self.file_path, self.nth_sent, self.lineno)
        data = [(d if d != EMPTY else None) for d in line.split("\t")]
        token, mwecodes = self.get_token_and_mwecodes(data)  # method defined in subclass

        for mwecode in mwecodes:
            index_and_categ = mwecode.split(":")
            self.id2mwe_indexes[index_and_categ[0]].append(len(self.curr_sent.tokens))
            if len(index_and_categ) == 2:
                self.id2mwe_categ[index_and_categ[0]] = index_and_categ[1]
        self.curr_sent.tokens.append(token)

    def __iter__(self):
        with open(self.file_path, 'r') as f:
            yield from self.iter_header(f)
            for self.lineno, line in enumerate(f, 1):
                line = line.strip("\n")
                if line.startswith("#"):
                    yield self.make_comment(line)
                elif not line.strip():
                    yield self.finish_sentence()
                else:
                    self.append_token(line)
            yield from self.iter_footer(f)

    def iter_header(self, f):
        return []  # Nothing to yield on header

    def iter_footer(self, f):
        if self.curr_sent:
            self.err("Missing empty line at the end of the file")
        return []  # Nothing to yield on footer


class ConllIterator(AbstractFileIterator):
    def get_token_and_mwecodes(self, data):
        if len(data) != 10:
            self.err("Line has {} columns, not 10".format(len(data)))
        rank, surface, lemma, upos = data[:4]
        return Token(rank, surface, False, lemma, upos), []


class ParsemeTSVIterator(AbstractFileIterator):
    def get_token_and_mwecodes(self, data):
        if len(data) != 4:
            self.err("Line has {} columns, not 4".format(len(data)))
        rank, surface, nsp, mwe_codes = data
        m = mwe_codes.split(";") if mwe_codes else []
        return Token(rank, surface, (nsp == "nsp"), None, None), m


class ParsemePlatinumIterator(AbstractFileIterator):
    def get_token_and_mwecodes(self, data):
        if len(data) < 6:
            self.err("Line has {} columns, not 6+".format(len(data)))
        rank, surface = data[0], data[1]
        nsp = (data[2] == 'nsp')
        # Ignore MTW in data[3]
        mwe_codes = ["{}:{}".format(data[i], data[i+1]) if data[i+1] else data[i]
                for i in range(4, len(data)-1, 2) if data[i] not in EMPTY]
        # Ignore free comments in data[-1], present if len(data)%2==1
        return Token(rank, surface, nsp, None, None), mwe_codes

    def iter_header(self, f):
        next(f); next(f)  # skip the 2-line header
        return super().iter_header(f)

    def iter_footer(self, f):
        if self.curr_sent:
            yield self.finish_sentence()



def err_badline(file_path, lineno, msg):
    r"""Warn user and quit execution due to error in file format."""
    err = "{}:{}: ERROR: {}".format(file_path, lineno or "???", msg)
    print(err, file=sys.stderr)
    exit(1)
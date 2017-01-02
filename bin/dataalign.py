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
import difflib
import itertools
import os
import sys


try:
    from pynlpl.formats import folia
except ImportError:
    exit("ERROR: PyNLPl not found, please run this code: pip3 install pynlpl")


# The `empty` field in CoNLL-U and PARSEME-TSV
EMPTY = "_"

# Set of all valid languages in PARSEME'2016
LANGS = set("BG CS DE EL EN ES FA FR HE HR HU IT LT MT PL PT RO SV SL TR YI".split())

# Languages where the pronoun in IReflV is on the left
LANGS_WITH_REFL_PRON_ON_LEFT = set("DE FR RO".split())

# Languages where the main verb is normally on the right
LANGS_WITH_DEFAULT_VERB_ON_RIGHT = set("TR".split())


############################################################

class Comment(collections.namedtuple('Comment', 'file_path lineno text')):
    r"""Represents a comment in the CoNLL-U file."""


class MWEAnnot(collections.namedtuple('MWEAnnot', 'ranks category')):
    r"""Represents an MWE annotation.
    @type ranks: tuple[str]
    @type category: str
    """
    def indexes(self, rank2index):
        r"""Return all indexes of this MWEAnnot inside a `rank2index` dict.
        Missing entries are SILENTLY IGNORED (useful for AlignedIterator).

        @type rank2index: dict[str, int]
        @rtype: tuple[int]
        """
        return tuple(rank2index[r] for r in self.ranks if (r in rank2index))


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

    def rank2index(self):
        r"""Return a dictionary mapping string ranks to indexes."""
        return {t.rank: index for (index, t) in enumerate(self.tokens)}

    def mwe_occurs(self, lang):
        r"""Yield MWEOccur instances for all MWEs in self."""
        rank2index = self.rank2index()
        for mwe_id, mweannot in enumerate(self.mweannots, 1):
            annotator, confidence, datetime, comments = None, None, None, []
            if mwe_id in self.mwe_id2folia:
                F = self.mwe_id2folia[mwe_id]
                annotator, confidence, datetime = F.annotator, F.confidence, F.datetime
                comments = [c.value for c in F.select(folia.Comment)]

            indexes = mweannot.indexes(rank2index)
            assert indexes, (mweannot, rank2index)
            yield MWEOccur(lang, self, indexes, mweannot.category,
                    comments, annotator, confidence, datetime)

    def tokens_and_mwecodes(self):
        r"""Yield pairs (token, mwecode)."""
        rank2index = self.rank2index()
        tokenindex2mweindex = collections.defaultdict(list)
        for mweindex, mweannot in enumerate(self.mweannots):
            for index in mweannot.indexes(rank2index):
                tokenindex2mweindex[index].append(mweindex)

        for i, token in enumerate(self.tokens):
            mwe_is = tokenindex2mweindex[i]
            yield token, [self._mwecode(token, mwe_i) for mwe_i in mwe_is]

    def _mwecode(self, token, mwe_i):
        r"""Return a string with mweid:category (or just mweid in some cases)."""
        mweannot = self.mweannots[mwe_i]
        if mweannot.category and mweannot.ranks[0] == token.rank:
            return "{}:{}".format(mwe_i+1, mweannot.category)
        return str(mwe_i+1)

    def remove_non_vmwes(self):
        r"""Change the mwe_codes in `self.tokens` so as to remove all NonVMWE tags."""
        self.mweannots = [m for m in self.mweannots if m.category != "NonVMWE"]


    def re_tokenize(self, new_tokens, indexmap):
        r"""Replace `self.tokens` with given tokens and fix `self.mweannot` based on `indexmap`"""
        rank2index = self.rank2index()
        self_nsps = set(i for (i, t) in enumerate(self.tokens) if t.nsp)
        self.tokens = [t._replace(nsp=t.nsp or (i in self_nsps)) for (i, t) in enumerate(new_tokens)]
        self.mweannots = [self._remap(m, rank2index, indexmap) for m in self.mweannots]

    def _remap(self, mweannot, rank2index, indexmap):
        r"""Remap `mweannot` using new `self.tokens`."""
        new_indexes = [i_new for i_old in mweannot.indexes(rank2index)
                for i_new in indexmap[i_old]]  # Python's syntax for a flatmap...
        return MWEAnnot(tuple(self.tokens[i].rank for i in new_indexes), mweannot.category)


    def id(self):
        r"""Return an ID, such as "foo.xml(s.13):78"."""
        ret = self.file_path
        ret += "(s.{})".format(self.nth_sent) if self.nth_sent else ""
        return ret + (":{}".format(self.lineno) if self.lineno else "")

    def msg_stderr(self, msg, header=True, die=False):
        r"""Print a warning message; e.g. "foo.xml:13: blablabla"."""
        final_msg = "{}: {}".format(self.id(), msg)
        if not header: final_msg = "\x1b[37m{}\x1b[m".format(final_msg)
        print(final_msg, file=sys.stderr)
        if die: exit(1)




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

    def id(self):
        r"""Return an ID that uniquely identifies the file&sentence&indexes."""
        return (self.sentence.file_path, self.sentence.nth_sent, tuple(self.indexes))

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
        i_verbs = [i for (i, t) in enumerate(self.tokens) if t.univ_pos == "VERB"] \
                or [(-1 if LANGS_WITH_DEFAULT_VERB_ON_RIGHT else 0)]
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
            nounverb = (lang in LANGS_WITH_DEFAULT_VERB_ON_RIGHT)
            if iS is None:
                iS = 0 if nounverb else len(T)-1
            if (nounverb and iH < iS) or (not nounverb and iS < iH):
                newT[iH], newT[iS] = T[iS], T[iH]

        if category == "IReflV":
            iPron, iVerb = ((0,-1) if (lang in LANGS_WITH_REFL_PRON_ON_LEFT) else (-1,0))
            if T[iVerb].univ_pos == "PRON" and T[iPron].univ_pos == "VERB":
                newT[iVerb], newT[iPron] = T[iPron], T[iVerb]
            elif lang == "PT" and (T[iVerb].univ_pos == "PART" or T[iVerb].univ_pos == "CONJ") and T[iPron].univ_pos == "VERB":
                newT[iVerb], newT[iPron] = T[iPron], T[iVerb]

        return MWETokens(self.mwe_occur, newT)



############################################################

# Leave the preferable PATH_FMT in PATH_FMTS[-1]
PATH_FMTS = ["{d}/{b}.conllu", "{d}/conllu/{b}.conllu"]


def calculate_conllu_paths(file_paths, warn=True):
    r"""Return CoNLL-U paths, or None on failure to find some of them."""
    ret = []
    for file_path in file_paths:
        dirname, basename = os.path.split(file_path)
        if not dirname: dirname = "."  # seriously, python...

        if basename.endswith(".folia.xml"):
            basename = basename.rsplit(".", 2)[0]
        elif any(basename.endswith(x) for x in [".tsv", ".parsemetsv", ".xml"]):
            basename = basename.rsplit(".", 1)[0]
        else:
            exit("ERROR: unknown file extension for `{}`".format(file_path))

        for path_fmt in ["{d}/{b}.conllu", "{d}/conllu/{b}.conllu"]:
            ret_path = path_fmt.format(d=dirname, b=basename)
            if os.path.exists(ret_path):
                if warn:
                    print("INFO: Using CoNNL-U file `{}`".format(ret_path), file=sys.stderr)
                ret.append(ret_path)
                break

        else:
            if warn:
                print("WARNING: CoNLL-U file `{}` not found".format(ret_path), file=sys.stderr)
                print("WARNING: not using any CoNLL-U file", file=sys.stderr)
                return None
    return ret


def iter_aligned_files(file_paths, conllu_paths=None, keep_nvmwes=False, debug=False):
    r"""iter_aligned_files(list[str], list[str]) -> Iterable[Either[Sentence,Comment]]
    Yield Sentence's & Comment's based on file_paths and conllu_paths.
    """
    for sentence in AlignedIterator.from_paths(file_paths, conllu_paths, debug):
        if not keep_nvmwes and isinstance(sentence, Sentence):
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
            yield from self._align_sents()
            if not self.main and not self.conllu:
                break
            main_s = self.main.popleft()
            conllu_s = self.conllu.popleft()
            tok_aligner = TokenAligner(main_s, conllu_s, debug=self.debug)
            indexmap = tok_aligner.index_mapping(main_s, conllu_s)
            main_s.re_tokenize(conllu_s.tokens, indexmap)
            yield main_s


    def merge_sentences(self, main_sentence, conllu_sentence):
        r"""Return a dict {main_i -> list[conllu_i]}"""
        tok_aligner = TokenAligner(main_sentence, conllu_sentence)
        for (info, tokens) in tok_aligner:
            if info in ["EQUAL", "CONLL:EXTRA"]:
                yield from tokens

            if self.debug and info == "CONLL:EXTRA":
                conllu_sentence.msg_stderr(
                        "DEBUG: Adding tokens from CoNLL: {!r} with rank {!r}".format(
                        [t.surface for t in tokens], [t.rank for t in tokens]))


    def _align_sents(self):
        while self.conllu and isinstance(self.conllu[0], Comment):
            yield self.conllu.popleft()
        if self.conllu or self.main:
            _check_both_exist(self.main[0] if self.main else None,
                    self.conllu[0] if self.conllu else None)

    @staticmethod
    def from_paths(main_paths, conllu_paths, debug=False):
        r"""Return an AlignedIterator for the given paths.
        (Special case: if conllu_paths is None, return a simpler kind of iterator)."""
        chain_iter = itertools.chain.from_iterable
        main_iterator = chain_iter(_iter_parseme_file(p) for p in main_paths)
        if not conllu_paths:
            return main_iterator
        conllu_iterator = chain_iter(ConllIterator(p) for p in conllu_paths)
        return AlignedIterator(main_iterator, conllu_iterator, debug)


def _check_both_exist(main_sentence, conllu_sentence):
    assert conllu_sentence or main_sentence

    if not main_sentence:
        conllu_sentence.msg_stderr("ERROR: CoNLL-U sentence #{} found, but there is " \
                "no matching PARSEME-TSV input file".format(conllu_sentence.nth_sent), die=True)
    if not conllu_sentence:
        main_sentence.msg_stderr("ERROR: PARSEME-TSV sentence #{} found, but there is " \
                "no matching CoNLL-U input file".format(main_sentence.nth_sent), die=True)


class SentenceAligner:
    def __init__(self, main_sentences, conllu_sentences, debug=False):
        self.main_sentences = _filter_sentences(main_sentences)
        self.conllu_sentences = _filter_sentences(conllu_sentences)
        self.debug = debug
        main_surfs = [tuple(t.surface for t in sent.tokens) for sent in self.main_sentences]
        conllu_surfs = [tuple(t.surface for t in sent.tokens) for sent in self.conllu_sentences]
        sm = difflib.SequenceMatcher(None, main_surfs, conllu_surfs)
        self.matches_end = sm.get_matching_blocks()
        self.matches_beg = [(0, 0, 0)] + self.matches_end

    def print_mismatches(self):
        for mismatch_main, mismatch_conllu in self.mismatches():
            if mismatch_main or mismatch_conllu:
                first_conllu_sent = self.conllu_sentences[mismatch_conllu.start] \
                    if mismatch_conllu.start < len(self.conllu_sentences) else None
                first_main_sent = self.main_sentences[mismatch_main.start] \
                    if mismatch_main.start < len(self.main_sentences) else None
                _check_both_exist(first_main_sent, first_conllu_sent)

                m, c = mismatch_main.start-1, mismatch_conllu.start-1
                for m, c in zip(mismatch_main, mismatch_conllu):
                    tokalign = TokenAligner(self.main_sentences[m], self.conllu_sentences[c])
                    if not tokalign.is_alignable():
                        tokalign.msg_unalignable(die=False)
                        self.print_context(m, c)
                        break
                else:
                    # zipped ranges are OK, the error is in the end of one of the ranges
                    end_mismatch_main = range(m+1, mismatch_main.stop)
                    end_mismatch_conllu = range(c+1, mismatch_conllu.stop)
                    assert not end_mismatch_main or not end_mismatch_conllu
                    for m in end_mismatch_main:
                        self.main_sentences[m].msg_stderr("ERROR: PARSEME sentence #{} does not match anything in CoNLL-U"
                                .format(self.main_sentences[m].nth_sent, None))
                        self.print_context(m, end_mismatch_conllu.start)
                    for c in end_mismatch_conllu:
                        self.conllu_sentences[c].msg_stderr("ERROR: CoNLL-U sentence #{} does not match anything in PARSEME"
                                .format(self.conllu_sentences[c].nth_sent, None))
                        self.print_context(end_mismatch_main.start, c)

    def print_context(self, main_index, conllu_index):
        self.print_context_sents("PARSEME", self.main_sentences[main_index-1:main_index+2])
        self.print_context_sents("CoNLL-U", self.conllu_sentences[conllu_index-1:conllu_index+2])

    def print_context_sents(self, info, sentences):
        for sent in sentences:
            sent.msg_stderr("{} sentence #{} = {} ...".format(info, sent.nth_sent,
                    " ".join(t.surface for t in sent.tokens[:7])), header=False)

    def mismatches(self):
        r"""@rtype: Iterable[(mismatch_main_range, mismatch_conllu_range)]"""
        for (main1,conll1,size1), (main2,conll2,_) in zip(self.matches_beg, self.matches_end):
            yield range(main1+size1, main2), range(conll1+size1, conll2)


def _filter_sentences(elements):
    return [e for e in elements if isinstance(e, Sentence)]



class TokenAligner:
    def __init__(self, main_sentence, conllu_sentence, debug=False):
        self.main_sentence = main_sentence
        self.conllu_sentence = conllu_sentence
        self.debug = debug
        main_surf = [t.surface for t in main_sentence.tokens]
        conllu_surf = [t.surface for t in conllu_sentence.tokens]
        sm = difflib.SequenceMatcher(None, main_surf, conllu_surf)
        self.matches_end = sm.get_matching_blocks()
        self.matches_beg = [(0, 0, 0)] + self.matches_end


    def index_mapping(self, main_sentence, conllu_sentence):
        r"""Return a dict {i_main -> list[i_conllu]}"""
        if not self.is_alignable():
            self.msg_unalignable(die=True)
        indexmap = collections.defaultdict(list)
        for info, range_main, range_conllu in self._triples():
            if info == "EQUAL":
                for iM, iC in zip(range_main, range_conllu):
                    indexmap[iM].append(iC)
            else:
                for iM in range_main:
                    indexmap[iM].extend(range_conllu)
                self.warn_mismatch(range_main, range_conllu)
        return indexmap


    def _triples(self):
        r"""Yield tuples (str, range_main, range_conll)."""
        # Main: [ok ok ok ok ok...ok ok ok] gap_main [ok ok ok ok...
        #       ^position=main1                      ^position=main2
        #       ^-------------size1-------^
        for (main1,conll1,size1), (main2,conll2,_) in zip(self.matches_beg, self.matches_end):
            yield ("EQUAL", range(main1, main1+size1), range(conll1, conll1+size1))
            yield ("MISMATCH", range(main1+size1, main2), range(conll1+size1, conll2))


    def is_alignable(self):
        r"""Return True iff the sentences are alignable."""
        for info, main_range, conllu_range in self._triples():
            if info == "MISMATCH" and len(main_range) > 10:
                return False
        return True


    def warn_mismatch(self, range_gap_main, range_gap_conllu):
        r"""Warn users when the two ranges do not match (one or both ranges may be empty)."""
        if range_gap_main:
            affected_mweids = [mwe_i+1 for (mwe_i, m) in enumerate(self.main_sentence.mweannots) \
                    if any((self.main_sentence.tokens[token_i].rank in m.ranks) for token_i in range_gap_main)]
            self.warn_gap_main(range_gap_main, range_gap_conllu, affected_mweids)

        if range_gap_conllu:
            # Probably a range, or a sub-word inside a range
            if self.debug:
                tokens = [self.conllu_sentence.tokens[i] for i in range_gap_conllu]
                self.conllu_sentence.msg_stderr(
                        "DEBUG: Adding tokens from CoNLL: {!r} with rank {!r}".format(
                        [t.surface for t in tokens], [t.rank for t in tokens]))


    def msg_unalignable(self, die=False):
        r"""Error issued if we cannot align tokens."""
        self.conllu_sentence.msg_stderr("ERROR: CoNLL-U sentence #{} does not match {} sentence #{}" \
                .format(self.conllu_sentence.nth_sent, self.main_sentence.id(),
                self.main_sentence.nth_sent), die=die)


    def warn_gap_main(self, main_range, conllu_range, all_mwe_codes):
        r"""Warn when there are unmapped characters in main file."""
        main_toks = [self.main_sentence.tokens[i].surface for i in main_range]
        #conllu_toks = [self.conllu_sentence.tokens[i].surface for i in conllu_range]

        mwe_codes_info = " (MWEs={})".format(";".join(all_mwe_codes)) if all_mwe_codes else ""
        self.main_sentence.msg_stderr(
                "WARNING: Ignoring extra tokens in sentence #{} ({}): {!r}{}"
                .format(self.main_sentence.nth_sent, self.conllu_sentence.id(),
                main_toks, mwe_codes_info))


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
                self.calc_mweannots(mwes, current_sentence)

                for rank, word in enumerate(folia_sentence.words(), 1):
                    token = Token(str(rank), word.text(), (not word.space), None, None)
                    current_sentence.tokens.append(token)

                current_sentence.mwe_id2folia = dict(enumerate(mwes, 1))
                yield current_sentence


    def calc_mweannots(self, mwes, output_sentence):
        for mwe in mwes:
            words = mwe.select(folia.Word)
            ranks = [w.id.rsplit(".",1)[-1] for w in words]
            if not ranks:  # ignore empty Entities produced by FLAT
                output_sentence.msg_stderr('Ignoring empty MWE')
            else:
                output_sentence.mweannots.append(MWEAnnot(ranks, mwe.cls))



class AbstractFileIterator:
    def __init__(self, file_path):
        self.file_path = file_path
        self.nth_sent = 0
        self.lineno = 0
        self._new_sent()

    def _new_sent(self):
        self.curr_sent = None
        self.id2mwe_categ = {}
        self.id2mwe_ranks = collections.defaultdict(list)

    def finish_sentence(self):
        r"""Return finished `self.curr_sent`."""
        if not self.curr_sent:
            self.err("File starts with empty line")
        s = self.curr_sent
        s.mweannots = [MWEAnnot(tuple(self.id2mwe_ranks[id]),
            self.id2mwe_categ[id]) for id in sorted(self.id2mwe_ranks)]
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
            self.id2mwe_ranks[index_and_categ[0]].append(token.rank)
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
        return Token(rank, surface or "_", False, lemma, upos), []


class ParsemeTSVIterator(AbstractFileIterator):
    def get_token_and_mwecodes(self, data):
        if len(data) != 4:
            self.err("Line has {} columns, not 4".format(len(data)))
        rank, surface, nsp, mwe_codes = data
        m = mwe_codes.split(";") if mwe_codes else []
        return Token(rank, surface or "_", (nsp == "nsp"), None, None), m


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
        return Token(rank, surface or "_", nsp, None, None), mwe_codes

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

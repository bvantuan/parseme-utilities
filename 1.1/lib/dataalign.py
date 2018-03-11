#! /usr/bin/env python3

r"""
This is a library for reading FoLiA XML files aligned with a CoNLL file.
The XML files may have PARSEME annotations, and this library can be helpful
in dealing with such data.

This library requires PyNLPl to be installed.

-----------------------------------------------

To adapt this library to a new language, see the LANGS
and other variables below. You may also want to add special code for
a canonical form (used e.g. when grouping MWEs during consistency check):

  * To fix word lemmas, add special code to `_with_fixed_tokens`
    (e.g. to re-lemmatize "me" and "te" as 3rd-person "se" in Romance languages).

  * To change word order, add special code to `_with_reordered_tokens`.
    (e.g. to reorder the LVC "(a) bath (was) taken" as "take bath").
"""


import collections
import difflib
import itertools
import os
import sys


# Import the Categories class
from categories import Categories


try:
    from pynlpl.formats import folia
except ImportError:
    exit("ERROR: PyNLPl not found, please run this code: pip3 install pynlpl")


# The `empty` field in CoNLL-U and PARSEME-TSV
EMPTY = "_"

# Set of all valid languages in the latest PARSEME Shared-Task
LANGS = set("AR BG CS DE EL EN ES EU FA FR HE HR HU HI IT LT MT PL PT RO SL SV TR".split())

# Languages where the pronoun in IRV is on the left
LANGS_WITH_CANONICAL_REFL_PRON_ON_LEFT = set("DE EU FR RO".split())

# Languages where the verb canonically appears to the right of the object complement (SOV/OSV/OVS)
LANGS_WITH_CANONICAL_VERB_ON_RIGHT = set("DE EU HI TR".split())



############################################################

class Comment(collections.namedtuple('Comment', 'file_path lineno text')):
    r"""Represents a comment in the CoNLL-U file."""


class MWEAnnot(collections.namedtuple('MWEAnnot', 'ranks category')):
    r"""Represents an MWE annotation.
    @type ranks: tuple[str]
    @type category: str
    """
    def __new__(cls, ranks, category):
        new_ranks = list(set(ranks))
        new_ranks.sort(key=lambda r: tuple(int(i) for i in r.split("-")))
        return super().__new__(cls, tuple(new_ranks), category)


    def indexes(self, rank2index):
        r"""Return all indexes of this MWEAnnot inside a `rank2index` dict.
        Missing entries are SILENTLY IGNORED (useful for AlignedIterator).

        @type rank2index: dict[str, int]
        @rtype: tuple[int]
        """
        return tuple(rank2index[r] for r in self.ranks if (r in rank2index))


class Dependency(collections.namedtuple('Dependency', 'label parent_rank')):
    r'''Represents a dependency link; e.g. Dependency('xcomp', '9').'''

Dependency.MISSING = Dependency('missing_dep', '0')


class Token(collections.namedtuple('Token', 'rank surface nsp lemma univ_pos dependency')):
    r"""Represents a token in an input file.

    Attributes:
    @rank: str
    @surface: str
    @nsp: bool
    @lemma: Optional[str]
    @univ_pos: Optional[str]
    @dependency: Dependency
    """
    def lemma_or_surface(self):
        return self.lemma or self.surface

    def __lt__(self, other):
        return self._lt_key() < other._lt_key()

    def cmp_key(self):
        r'''Deterministic exception-free comparison method.'''
        return (self.rank, self.surface, self.nsp, self.lemma or '', self.univ_pos or '', self.dependency)


class Sentence:
    r"""A sequence of tokens."""
    def __init__(self, file_path, nth_sent, lineno):
        self.file_path = file_path
        self.nth_sent = nth_sent
        self.lineno = lineno
        self.tokens = []
        self.mweannots = []  # list[MWEAnnot]
        self.mwe_id2folia = {}  # extra info per MWE from FoLiA file

    def __str__(self):
        r"""Return a string representation of the tokens"""
        return " ".join(map(lambda x: x.surface,self.tokens))

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
        self.mweannots = [m for m in self.mweannots if m.category not in Categories.NON_MWES]

    def remove_duplicate_mwes(self):
        r"""Uniqs self.mweannots (keeps only first occurrence)"""
        old_mweannots = self.mweannots
        self.mweannots = [m for (i, m) in enumerate(self.mweannots) if m not in self.mweannots[:i]]
        if len(self.mweannots) != len(old_mweannots):
            duplicates = [m for m in old_mweannots if old_mweannots.count(m) > 1]
            for mweannot in duplicates:
                self.msg_stderr("Removed duplicate MWE: {}".format(mweannot))


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
        r"""Return a sentence ID, such as "foo.xml(s.13):78"."""
        ret = self.file_path
        ret += "(s.{})".format(self.nth_sent) if self.nth_sent else ""
        return ret + (":{}".format(self.lineno) if self.lineno else "")

    def msg_stderr(self, msg, header=True, die=False):
        r"""Print a warning message; e.g. "foo.xml:13: blablabla"."""
        final_msg = "{}: {}".format(self.id(), msg)
        if not header: final_msg = "\x1b[37m{}\x1b[m".format(final_msg)
        print(final_msg, file=sys.stderr)
        if die: exit(1)


    def check_token_data(self):
        r"""Check token data and emit warnings if they are malformed
        (e.g. if a token contains spaces inside the surface form).
        """
        for token in self.tokens:
            nonspace_forms = ['rank', 'surface', 'nsp', 'lemma', 'univ_pos']
            for nonspace_form in nonspace_forms:
                if " " in (str(getattr(token, nonspace_form)) or ""):
                    self.msg_stderr("Token #{} contains spaces in `{}` form"
                                    .format(token.rank, nonspace_form))


    def iter_root_to_leaf_all_tokens(self):
        r'''Yield all Tokens in sentence, from root to leaves (aka topological sort).
        May NOT yield all tokens if there is missing Dependency information.
        '''
        children = collections.defaultdict(list)  # dict[str, list[Token]]
        for i, token in enumerate(self.tokens):
            if token.dependency:
                children[token.dependency.parent_rank].append(token)
        to_visit = collections.deque(children['0'])
        while to_visit:
            current = to_visit.popleft()
            to_visit.extend(children[current.rank])
            yield current


    def check_and_convert_categ(self, categ):
        r'''Return an updated version of given category. Warns on bad categories.'''
        if categ in Categories.KNOWN:
            return categ
        if categ in Categories.RENAMED:
            new_categ = Categories.RENAMED[categ]
            warn_once(self.id(), 'Category {} renamed to {}'.format(categ, new_categ))
            return new_categ
        warn_once(self.id(), 'Category {} is unknown'.format(categ))
        return categ




###########################################################

class MWEOccur:
    r"""Represents an instance of a MWE in text.
    In a type/token distinction: MWELexicalItem is a type and MWEOccur is a token.

    Parameters:
    @type  lang: str
    @param lang: one of the languages from the `LANGS` global
    @type  category: str
    @param category: one of {VID, LVC, IRV...}
    @type  sentence: Sentence
    @param sentence: the sentence in which this MWEOccur was seen
    @type  indexes: list[int]
    @param indexes: the indexes of the MWE inside `sentence`

    Attributes:
    @type  raw: MWEOccurView
    @param raw: represents tokens for raw form, as seen in text
    @type  fixed: MWEOccurView
    @param fixed: represents tokens in fixed form (e.g. homogenizing lemmas)
    @type  reordered: MWEOccurView
    @param reordered: represents tokens in reordered form (e.g. normalizing word-order for LVCs)
    """
    def __init__(self, lang, sentence, indexes, category, comments, annotator, confidence, datetime):
        assert lang in LANGS
        self.lang = lang
        self.sentence = sentence
        self.indexes = tuple(sorted(indexes))
        self.category = category
        self.comments = comments
        self.annotator = annotator
        self.confidence = confidence
        self.datetime = datetime

        self.raw = MWEOccurView(self, (sentence.tokens[i] for i in indexes))
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


class MWEOccurView:
    r'''Represents a view of the tokens inside an MWEOccur.
    The token order may be different from the literal order in the Sentence.
    
    Parameters:
    @type  mwe_occur: MWEOccur
    @param mwe_occur: The MWEOccur that this view represents
    @type  iter_tokens: Iterable[Token]
    @param iter_tokens: Tokens for MWEs in this view (may be different from literal order in Sentence)

    Attributes:
    @type  tokens: tuple[Token]
    @param tokens: Tokens for MWEs this view (may be different from literal order in Sentence)
    @type  mwe_canonical_form: list[str]
    @param mwe_canonical_form: List of lemmas (or surfaces) for MWE tokens in this MWEOccurView.
    @type  i_head: int
    @param i_head: Index of head verb.
    @type  i_subhead: Optional[int]
    @param i_subhead: Index of subhead noun (e.g. for LVCs and some VIDs). May be `None`.
    @type  i_synroots: tuple[int]
    @param i_synroots: Index of syntactic roots (requires syntax info in CoNLL-U). Empty list if unavailable.
    '''
    def __init__(self, mwe_occur, iter_tokens):
        self.mwe_occur = mwe_occur
        self.tokens = tuple(iter_tokens)
        assert all(isinstance(t, Token) for t in self.tokens), self.tokens
        self.i_head = self._i_head()
        self.i_subhead = self._i_subhead()
        self.head = self.tokens[self.i_head]
        self.subhead = self.tokens[self.i_subhead] if (self.i_subhead is not None) else None
        self.mwe_canonical_form = self._mwe_canonical_form()
        self.mwe_lemmatized_form = self._lemmatized_at(range(len(self.tokens)))    

    def _i_head(self):
        r"""Index of head verb in `mwe_canonical_form`
        (First word if there is no POS info available)."""
        i_verbs = [i for (i, t) in enumerate(self.tokens) if t.univ_pos == "VERB"] \
                or [(-1 if LANGS_WITH_CANONICAL_VERB_ON_RIGHT else 0)]
        return i_verbs[0]  # just take first verb that appears

    def _i_subhead(self):
        r"""Index of sub-head noun in `mwe_canonical form` (very useful for LVCs)."""
        i_nouns = tuple(i for (i, t) in enumerate(self.tokens) if t.univ_pos == "NOUN")
        if not i_nouns: return None
        # We look for the first noun that is not the modifier in a noun compound
        head_nouns = [i for i in i_nouns if (i==len(self.tokens)-1 or self.tokens[i+1] != "NOUN")]
        return head_nouns[0]

    def _i_synroot(self):
        r"""Yield index of the syntactic roots."""
        i_nouns = tuple(i for (i, t) in enumerate(self.tokens) if t.univ_pos == "NOUN")
        if not i_nouns: return None
        # We look for the first noun that is not the modifier in a noun compound
        head_nouns = [i for i in i_nouns if (i==len(self.tokens)-1 or self.tokens[i+1] != "NOUN")]
        return head_nouns[0]

    def _i_reflpron(self):
        r"""Return the reflexive pronoun (for IRVs), or None."""
        return next((i for (i, t) in enumerate(self.tokens) if t.univ_pos == "PRON"), None)

    def _mwe_canonical_form(self):
        r"""Return a lemmatized form of this MWE."""
        indexes = [self.i_head, self.i_subhead, self._i_reflpron()]
        return self._lemmatized_at([i for i in indexes if i is not None])


    def _lemmatized_at(self, indexes):
        r"""Return a list[str] with surfaces from self.tokens, lemmatized at given indexes."""
        ret = [t.surface for t in self.tokens]
        for i in indexes:
            ret[i] = self.tokens[i].lemma_or_surface()
        return [x.casefold() for x in ret]


    def _with_fixed_tokens(self):
        r"""Return a fixed version of `self.tokens` (must keep same length & order)."""
        fixed = tuple(self._fixed_token(t) for t in self.tokens)
        return MWEOccurView(self.mwe_occur, fixed)

    def _fixed_token(self, token):
        r"""Return a manually fixed version of `token` (e.g. homogenize lemmas for IRVs)."""
        if token.univ_pos == "PRON" and Categories.is_inherently_reflexive_verb(self.mwe_occur.category):
            # Normalize reflexive pronouns, e.g. FR "me" or "te" => "se"
            if self.mwe_occur.lang in ["PT", "ES", "FR"]:
                token = token._replace(lemma="se")
            if self.mwe_occur.lang == "IT":
                token = token._replace(lemma="si")
        return token


    def _with_reordered_tokens(self):
        r"""Return a reordered version of `tokens` (must keep same length)."""
        lang, category = self.mwe_occur.lang, self.mwe_occur.category
        T, newT, iH, iS = self.tokens, list(self.tokens), self.i_head, self.i_subhead
        if Categories.is_light_verb_construction(category):
            # Reorder e.g. EN "shower take(n)" => "take shower"
            nounverb = (lang in LANGS_WITH_CANONICAL_VERB_ON_RIGHT)
            if iS is None:
                iS = 0 if nounverb else len(T)-1
            if (nounverb and iH < iS) or (not nounverb and iS < iH):
                newT[iH], newT[iS] = T[iS], T[iH]

        if Categories.is_inherently_reflexive_verb(category):
            # Reorder e.g. PT "se suicidar" => "suicidar se"
            iPron, iVerb = ((0,-1) if (lang in LANGS_WITH_CANONICAL_REFL_PRON_ON_LEFT) else (-1,0))
            if T[iVerb].univ_pos == "PRON" and T[iPron].univ_pos == "VERB":
                newT[iVerb], newT[iPron] = T[iPron], T[iVerb]
            elif lang == "PT" and (T[iVerb].univ_pos == "PART" or T[iVerb].univ_pos == "CONJ") and T[iPron].univ_pos == "VERB":
                newT[iVerb], newT[iPron] = T[iPron], T[iVerb]

        return MWEOccurView(self.mwe_occur, newT)


    def iter_root_to_leaf_mwe_tokens(self):
        r'''Yield Tokens in MWE, from closest-to-root to leaves (aka topological sort).
        May NOT yield all tokens if there is missing Dependency information.
        '''
        # We use ranks because we sometimes replace tokens (e.g. _fixed_token above)...
        mwe_ranks = set(token.rank for token in self.tokens)
        for token in self.mwe_occur.sentence.iter_root_to_leaf_all_tokens():
            if token.rank in mwe_ranks:
                yield token

    def rerooted_tokens(self):
        r'''Return re-rooted Tokens (sorted from the closest-to-root towards the leaves).'''
        return rerooted(self.iter_root_to_leaf_mwe_tokens())


def rerooted(tokens):
    r'''Return a list of re-ranked and re-rooted tokens.
    * Tokens that referred to internal ranks new point to new ranks.
    * Tokens that referred to external ranks will now point to root:0.
    * Tokens that had parent_rank=='0' keep their old Dependency info.
    '''
    ret = []
    oldrank2new = {'0': '0'}
    for t in tokens:
        oldrank2new[t.rank] = str(len(ret)+1)
        t = t._replace(rank=oldrank2new[t.rank])

        if t.dependency.parent_rank in oldrank2new:
            t = t._replace(dependency=Dependency(
                t.dependency.label, oldrank2new[t.dependency.parent_rank]))
        else:
            t = t._replace(dependency=Dependency('root', '0'))
        ret.append(t)
    return ret



class MWELexicalItem:
    r'''Represents a group of `MWEOccur`s that share the same canonical form.
    In a type/token distinction: MWELexicalItem is a type and MWEOccur is a token.

    For example, an LVC with these MWEOccurs
      ["taking shower", "took shower", "shower taken"]
    would ideally be grouped into MWELexicalItem with canonicform "take shower".
    
    Parameters:
    @type  canonicform: tuple[str]
    @param canonicform: a tuple of canonical lemma/surface forms
    @type  mweoccurs: list[MWEOccur]
    @param mweoccurs: a list of MWEOccur instances (read-only!)

    Attributes:
    @type  i_head: int
    @param i_head: index of head verb
    @type  i_subhead: Optional[int]
    @param i_subhead: index of sub-head noun
    '''
    def __init__(self, canonicform, mweoccurs):
        self.canonicform, self.mweoccurs = canonicform, mweoccurs
        self._seen_mweoccur_ids = {m.id() for m in self.mweoccurs}  # type: set[str]

        self.i_head = most_common(m.reordered.i_head for m in mweoccurs)
        nounbased_mweos = [m.reordered.i_subhead for m in mweoccurs
                           if m.reordered.i_subhead is not None]
        self.i_subhead = most_common(nounbased_mweos, fallback=None)


    def only_non_vmwes(self):
        r'''True iff all mweoccurs are NonVMWEs.'''
        return all((o.category in Categories.NON_MWES and o.confidence is None) for o in self.mweoccurs)

    def contains_mweoccur(self, mweoccur):
        r'''True iff self.mweoccurs contains given MWEOccur.'''
        return (mweoccur.id() in self._seen_mweoccur_ids)

    def add_skipped_mweoccur(self, mweoccur):
        r'''Add MWEOccur to this MWE descriptor. If this MWEOccur already exists, does nothing.'''
        assert mweoccur.category == 'Skipped'  # we do not need to update i_head/i_subhead for Skipped
        mweoccur_id = mweoccur.id()
        if not mweoccur_id in self._seen_mweoccur_ids:
            self._seen_mweoccur_ids.add(mweoccur_id)
            self.mweoccurs.append(mweoccur)

    def head(self):
        r'''Return a `str` with the head verb.'''
        return self.canonicform[self.i_head]

    def subhead(self):
        r'''Return a `str` with the subhead noun (fails if self.i_subhead is None).'''
        return self.canonicform[self.i_subhead]


    def most_common_rooted_tokens_and_example(self):
        r'''Return the most common output from `mweoccur.rerooted_tokens()`
        for all mweoccurs in `self`, along with an example MWEOccur which has these re-rooted tokens.

        @rtype (Sequence[Token], MWEOccur).
        '''
        example_mweoccur = {}  # Dict[Tuple[Token], MWEOccur]
        counter = collections.Counter()  # Counter[Tuple[Token]]

        for mweoccur in self.mweoccurs:
            # XXX should this be `mweoccur.raw` or `mweoccur.reordered`?
            rooted_tokens = tuple(rerooted(mweoccur.raw.iter_root_to_leaf_mwe_tokens()))
            example_mweoccur.setdefault(rooted_tokens, mweoccur)
            counter[rooted_tokens] += 1

        # We just want the rooted_tokens with max-count, but we also want a
        # deterministic tie-breaker (determinism is good for experiments), so we do this hack:
        _, rooted_tokens = max(((count, tokens) for (tokens, count) in counter.items()),
                key=lambda ct: (ct[0], [t.cmp_key() for t in ct[1]]))
        return rooted_tokens, example_mweoccur[rooted_tokens]


    def lemma_or_surface_list(self):
        r'''Return a list of lemmas/surfaces for elements this MWE.'''
        try:
            return self._lemma_or_surface_list
        except AttributeError:
            lsl_possibilities = [tuple(t.lemma_or_surface() for t in m.reordered.tokens)
                                 for m in self.mweoccurs]
            self._lemma_or_surface_list = most_common(lsl_possibilities)
            return self._lemma_or_surface_list



############################################################

_FALLBACK_RAISE = object()

def most_common(iterable, *, fallback=_FALLBACK_RAISE):
    r'''Utility function: Return most common element in `iterable`.
    Return `fallback` if `iterable` is empty.
    '''
    a_list = collections.Counter(iterable).most_common(1)
    if a_list:
        return a_list[0][0]

    assert fallback is not _FALLBACK_RAISE, 'Zero elements to choose from; no fallback provided'
    return fallback


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
                    print("INFO: Using CoNLL-U file `{}`".format(ret_path), file=sys.stderr)
                ret.append(ret_path)
                break

        else:
            if warn:
                print("WARNING: CoNLL-U file `{}` not found".format(ret_path), file=sys.stderr)
                print("WARNING: not using any CoNLL-U file", file=sys.stderr)
                return None
    return ret


def iter_aligned_files(file_paths, conllu_paths=None, keep_nvmwes=False,
        keep_dup_mwes=False, keep_mwe_random_order=False, debug=False):
    r"""iter_aligned_files(list[str], list[str]) -> Iterable[Either[Sentence,Comment]]
    Yield Sentence's & Comment's based on file_paths and conllu_paths.
    """
    for entity in AlignedIterator.from_paths(file_paths, conllu_paths, debug):
        if isinstance(entity, Sentence):
            if not keep_nvmwes:
                entity.remove_non_vmwes()
            if not keep_dup_mwes:
                entity.remove_duplicate_mwes()
            if not keep_mwe_random_order:
                entity.mweannots.sort()
        yield entity


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
        while self.main and isinstance(self.main[0], Comment):
            self.main.popleft()  # Ignore all comments in TSV (do NOT yield them)
        while self.conllu and isinstance(self.conllu[0], Comment):
            yield self.conllu.popleft()  # Output comments from CoNLL-U
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

        mwe_codes_info = " (MWEs={})".format(";".join(map(str,all_mwe_codes))) if all_mwe_codes else ""
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
                mwes = list(folia_sentence.select(folia.Entity))
                self.calc_mweannots(mwes, current_sentence)

                for rank, word in enumerate(folia_sentence.words(), 1):
                    token = Token(str(rank), word.text(), (not word.space), None, None, Dependency.MISSING)
                    current_sentence.tokens.append(token)

                current_sentence.mwe_id2folia = dict(enumerate(mwes, 1))
                yield current_sentence


    def calc_mweannots(self, mwes, output_sentence):
        for mwe in mwes:
            ranks = [w.id.rsplit(".",1)[-1] for w in mwe.wrefs()]
            if not ranks:  # ignore empty Entities produced by FLAT
                output_sentence.msg_stderr('Ignoring empty MWE')
            else:
                categ = output_sentence.check_and_convert_categ(mwe.cls)
                output_sentence.mweannots.append(MWEAnnot(ranks, categ))



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
            self.err("Unexpected empty line")
        s = self.curr_sent
        try:
            s.mweannots = [MWEAnnot(tuple(self.id2mwe_ranks[id]),
                self.id2mwe_categ[id]) for id in sorted(self.id2mwe_ranks)]
        except KeyError as e:
            self.err("MWE has no category: {}".format(e.args[0]))
        self._new_sent()
        s.check_token_data()
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
            if len(index_and_categ) == 2 and index_and_categ[1]:
                categ = self.curr_sent.check_and_convert_categ(index_and_categ[1])
                self.id2mwe_categ.setdefault(index_and_categ[0], categ)
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
        dependency = Dependency(data[7], data[6]) if (data[7] and data[6]) else Dependency.MISSING
        return Token(rank, surface or "_", False, lemma, upos, dependency), []


class ParsemeTSVIterator(AbstractFileIterator):
    def get_token_and_mwecodes(self, data):
        if len(data) == 5:
            warn_once(
                "{}:{}".format(self.file_path, self.lineno),
                "Silently ignoring 5th parsemetsv column")
            data.pop()  # remove data[-1]
        elif len(data) != 4:
            self.err("Line has {} columns, not 4".format(len(data)))
        rank, surface, nsp, mwe_codes = data
        m = mwe_codes.split(";") if mwe_codes else []
        return Token(rank, surface or "_", (nsp == "nsp"), None, None, Dependency.MISSING), m


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
        return Token(rank, surface or "_", nsp, None, None, Dependency.MISSING), mwe_codes

    def iter_header(self, f):
        next(f); next(f)  # skip the 2-line header
        return super().iter_header(f)

    def iter_footer(self, f):
        if self.curr_sent:
            yield self.finish_sentence()




############################################################

_warned = set()

def warn_once(first_seen_here, msg):
    if msg not in _warned:
        warntype = 'WARNING'
        _warned.add(msg)
        print(warntype, ': ', msg, sep='', file=sys.stderr)
        print('.'*len(warntype), ': First seen here: ', first_seen_here, sep='', file=sys.stderr)
        print('.'*len(warntype), ': (Ignoring further warnings of this type)', sep='', file=sys.stderr)



def err_badline(file_path, lineno, msg):
    r"""Warn user and quit execution due to error in file format."""
    err = "{}:{}: ERROR: {}".format(file_path, lineno or "???", msg)
    print(err, file=sys.stderr)
    exit(1)



############################################################

def iter_sentences(input_paths, conllu_paths, verbose=True):
    r"""Utility function: yield all sentences in `input_paths`.
    (Output sentences are aligned, if CoNLL-U was provided or could be automatically found).
    """
    conllu_paths = conllu_paths or calculate_conllu_paths(input_paths, warn=verbose)
    for elem in iter_aligned_files(input_paths, conllu_paths, keep_nvmwes=True, debug=verbose):
        if isinstance(elem, Sentence):
            yield elem


def read_mwelexitems(lang, iter_sentences):
    r"""Return two lists: (list[MWELexicalItem], list[MWELexicalItem]).
    The first list concerns real MWEs, while the second concerns strictly NonVMWEs.
    """
    cf2mweoccurs = _canonicform2mweoccurs(lang, iter_sentences)  # type: dict[tuple[str], list[MWEOccur]]
    canonicform2mwe_mixed = collections.OrderedDict()  # type: dict[tuple[str], MWELexicalItem]
    canonicform2mwe_nvmwe = collections.OrderedDict()  # type: dict[tuple[str], MWELexicalItem]

    for canonicform, mweoccurs in cf2mweoccurs.items():
        mwe = MWELexicalItem(canonicform, mweoccurs)
        if mwe.only_non_vmwes():
            canonicform2mwe_nvmwe[canonicform] = mwe
        else:
            canonicform2mwe_mixed[canonicform] = mwe
    return (list(canonicform2mwe_mixed.values()), list(canonicform2mwe_nvmwe.values()))


def _canonicform2mweoccurs(lang, iter_sentences):
    r'''Return a dict[tuple[str], list[MWEOccur]].'''
    ret = collections.defaultdict(list)  # type: dict[tuple[str], list[MWEOccur]]
    for sentence in iter_sentences:
        for mwe_occur in sentence.mwe_occurs(lang):
            canonicform = tuple(mwe_occur.reordered.mwe_canonical_form)
            ret[canonicform].append(mwe_occur)
    return ret


############################################################

SKIPPED_FINDER_PATTERNS = '{Dependency, UnlabeledDep, BagOfDeps, WindowGapX}'


def skipped_finder(finding_method, lang, mwes, *, favor_precision):
    r'''Return an instance of a subclass of AbstractSkippedFinder.

    Parameters:
    @type  finding_method: str
    @param finding_method: A string matching one of the SKIPPED_FINDER_PATTERNS
    @type  lang: str
    @param lang: one of the languages from the `LANGS` global
    @type  mwes: list[MWELexicalItem]
    @param mwes: list of MWEs to be used for annotation (it may be ignored)
    @type  favor_precision: bool
    @param favor_precision: whether to favor precision (conservative) or recall
    '''
    if finding_method == 'Dependency':
        return DependencyBasedSkippedFinder(lang, mwes, favor_precision, 'LABELED-ARC')
    if finding_method == 'UnlabeledDep':
        return DependencyBasedSkippedFinder(lang, mwes, favor_precision, 'UNLABELED-ARC')
    if finding_method == 'BagOfDeps':
        return DependencyBasedSkippedFinder(lang, mwes, favor_precision, 'BAG')

    if finding_method.startswith('WindowGap'):
        max_gaps = int(finding_method[len('WindowGap'):])
        return WindowBasedSkippedFinder(lang, mwes, favor_precision, max_gaps)

    raise ValueError('Invalid finding-method: `{}`'.format(finding_method))



class AbstractSkippedFinder:
    r'''Superclass for algorithms to find skipped MWEs in text.

    Parameters:
    @type  lang: str
    @param lang: one of the languages from the `LANGS` global
    @type  mwes: list[MWELexicalItem]
    @param mwes: list of MWEs to be used for annotation
    @type  favor_precision: bool
    @param favor_precision: whether to favor precision (conservative) or recall
    '''
    def __init__(self, lang, mwes, favor_precision):
        self.lang = lang
        self.mwes = list(mwes)
        self.favor_precision = favor_precision

    def find_skipped_in(self, sentences):
        r"""Yield pairs (MWELexicalItem, MWEOccur) for Skipped MWEs in all sentences."""
        raise NotImplementedError

    def _mweinfo_pair(self, mwelexitem, sentence, indexes):
        r"""Return a pair (MWELexicalItem, MWEOccur) with
        a new MWEOccur for "Skipped" MWE in sentence (at given indexes).
        """
        indexes = tuple(sorted(indexes))
        new_occur = MWEOccur(self.lang, sentence, indexes,
                "Skipped", [], "autodetect", None, None)
        return (mwelexitem, new_occur)




class WindowBasedSkippedFinder(AbstractSkippedFinder):
    r'''Algorithm to find skipped MWEs based on a window
    (allows gaps of up to `max_gaps` words).
    See documentation in AbstractSkippedFinder.
    
    Extra Parameters:
    @type  max_gaps: int
    @param max_gaps: max number of gaps between words in match
    '''
    def __init__(self, lang, mwes, favor_precision, max_gaps):
        super().__init__(lang, mwes, favor_precision)
        self.max_gaps = max_gaps

        self.mweelement2mwes = collections.defaultdict(list)  # type: dict[str, list[MWELexicalItem]]
        for mwe in self.mwes:
            for lemmasurface in set(mwe.lemma_or_surface_list()):
                self.mweelement2mwes[lemmasurface.lower()].append(mwe)

    def find_skipped_in(self, sentences):
        r"""Yield pairs (MWELexicalItem, MWEOccur) for Skipped MWEs in all sentences."""
        for sentence in sentences:
            for i, token in enumerate(sentence.tokens):
                for wordform in [token.lemma_or_surface().lower(), token.surface.lower()]:
                    for mwe in self.mweelement2mwes.get(wordform, []):
                        yield from self._find_skipped_mwe_at(sentence, mwe, i)

    def _find_skipped_mwe_at(self, sentence, mwe, i_head):
        r"""Yield a Skipped MWE or nothing at all."""
        unmatched_words = collections.Counter(mwe.lemma_or_surface_list())
        matched_indexes = []

        def matched(wordform, i):
            unmatched_words.pop(wordform)
            matched_indexes.append(i)

        gaps = 0
        for i in range(i_head, len(sentence.tokens)):
            word = sentence.tokens[i]
            if not unmatched_words:
                break  # matched_indexes is complete
            if gaps > self.max_gaps:
                break  # failed to match under max_gaps
            if word.surface.lower() in unmatched_words:
                matched(word.surface.lower(), i)
            elif word.lemma_or_surface().lower() in unmatched_words:
                matched(word.lemma.lower(), i)
            else:
                gaps += 1

        if not unmatched_words:
            yield self._mweinfo_pair(mwe, sentence, matched_indexes)



#------------------------------------------------------------

class Bag:
    r'''Bag[A, B] is similar to a Dict[A, set[B]], with insertions adding to the set of values.'''
    def __init__(self, key_value_pairs=()):
        self.dict = {}
        for k, value in key_value_pairs:
            try:
                subset = self.dict[k]
            except KeyError:
                subset = self.dict[k] = set()
            subset.add(value)

    def is_empty(self):
        return (not self.dict)

    def __contains__(self, key):
        return (key in self.dict)

    def __getitem__(self, key):
        return self.dict.get(key, frozenset())

    def excluding(self, key, value_in_bag):
        r'''Return new Bag excluding (key, value_in_bag).'''
        return Bag((k, v) for (k, values) in self.dict.items() for v in values if (k, v) != (key, value_in_bag))


class MWEBagFrame(collections.namedtuple('MWEBagFrame', 'mwe n_roots lemmabag')):
    r'''Attributes:
    @type  mwe: MWELexicalItem
    @type  n_roots: int
    @type  n_roots: Number of tokens with parent '0'
    @type  lemmabag: Bag[str, Token]
    @param lemmabag: Mapping from lemma to set of rooted tokens
    '''

class DependencyBasedSkippedFinder(AbstractSkippedFinder):
    r'''Algorithm to find skipped MWEs based
    on bags of unlabeled syntactic dependencies.
    See documentation in AbstractSkippedFinder.

    Extra parameters:
    @type  matchability: str
    @param matchability: One of {labeled-arc, unlabeled-arc, bag}
    '''
    def __init__(self, lang, mwes, favor_precision, matchability):
        super().__init__(lang, mwes, favor_precision)
        self.matchability = matchability
        self.rootmostlemma2mwebagframe = collections.defaultdict(list)  # type: dict[str, list[MWEBagFrame]]

        for mwe in self.mwes:
            # CAREFUL: re-rooting changes the parent_rank of dependencies
            rooted_tokens, example_mweoccur = mwe.most_common_rooted_tokens_and_example()
            n_roots = sum(1 for t in rooted_tokens if t.dependency.parent_rank == '0')

            if any(t.dependency == Dependency.MISSING for t in rooted_tokens):
                example_mweoccur.sentence.msg_stderr(
                    'WARNING: skipping MWE with partial dependency info: {}'.format("_".join(mwe.canonicform)))
                continue

            if favor_precision and n_roots > 1:
                example_mweoccur.sentence.msg_stderr(
                    'WARNING: skipping MWE with disconnected syntax tree: {}'.format('_'.join(mwe.canonicform)))
                continue

            x = MWEBagFrame(mwe, n_roots, Bag((t.lemma_or_surface().lower(), t) for t in rooted_tokens))
            self.rootmostlemma2mwebagframe[mwe.head().lower()].append(x)


    def find_skipped_in(self, sentences):
        r"""Yield pairs (MWELexicalItem, MWEOccur) for Skipped MWEs in all sentences."""
        for sentence in sentences:
            reordered_sentence_tokens = tuple(sentence.iter_root_to_leaf_all_tokens())

            # For every rootmost lemma in sentence, find all MWEOccurs involving this lemma
            for rootmost_lemma in sorted(set(t.lemma_or_surface().lower() for t in reordered_sentence_tokens)):
                for mwebagframe in self.rootmostlemma2mwebagframe.get(rootmost_lemma, []):
                    sub_finder = _SingleMWEFinder(
                            self.lang, self.favor_precision, self.matchability, sentence,
                            reordered_sentence_tokens, mwebagframe.mwe, mwebagframe.n_roots, mwebagframe.lemmabag)

                    for matched_indexes in sub_finder.find_indexes():
                        yield self._mweinfo_pair(mwebagframe.mwe, sentence, matched_indexes)


class _SingleMWEFinder(collections.namedtuple(
        '_SingleMWEFinder',
        'lang favor_precision matchability sentence reordered_sentence_tokens mwe max_roots lemmabag')):
    r'''Finder of all occurrences of `mwe` in `reordered_sentence_tokens`.'''

    def find_indexes(self):
        r"""Yield Skipped MWE occurrence indexes in sentence (may yield 2+ MWEs in rare cases)."""
        rank2index = self.sentence.rank2index()

        already_matched = MWEBagAlreadyMatched.EMPTY
        for matched_ranks in self._recursive_find_ranks(0, already_matched, self.lemmabag):
            assert len(matched_ranks) == len(self.mwe.canonicform), self.mwe.canonicform
            yield tuple(rank2index[rank] for rank in matched_ranks)


    def _recursive_find_ranks(self, i_start, already_matched, unmatched_lemmabag):
        r'''Yield sets of ranks fully matching current MWE.'''
        if unmatched_lemmabag.is_empty():
            yield already_matched.rank2rootedrank.keys()
            return

        for i, sentence_token, rooted_token in self._find_matched_tokens(
                 i_start, already_matched, unmatched_lemmabag):
            new_already_matched = already_matched.including(sentence_token, rooted_token)
            new_unmatched_lemmabag = unmatched_lemmabag.excluding(rooted_token.lemma_or_surface(), rooted_token)
            yield from self._recursive_find_ranks(i+1, new_already_matched, new_unmatched_lemmabag)


    def _find_matched_tokens(self, i_start, already_matched, unmatched_lemmabag):
        r'''Yield all (i, sentence_token, rooted_token) for matches at reordered_sentence_tokens[i].'''
        for i, sentence_token in enumerate(self.reordered_sentence_tokens[i_start:], i_start):
            if sentence_token.dependency == Dependency.MISSING:
                continue  # If we have no dependency info, avoid false positives

            for wordform in [sentence_token.lemma_or_surface().lower(), sentence_token.surface.lower()]:
                for rooted_token in unmatched_lemmabag[wordform]:
                    match_triple = (i, sentence_token, rooted_token)

                    if sentence_token.dependency.parent_rank in already_matched.rank2rootedrank:
                        # Non-rootmost token, connected to someone in `already_matched`
                        expected_rooted_parent_rank = already_matched.rank2rootedrank[sentence_token.dependency.parent_rank]
                        if self._matches_in_tree(i, sentence_token, rooted_token, already_matched, expected_rooted_parent_rank):
                            yield match_triple

                    elif already_matched.n_roots < self.max_roots:
                        # Rootmost token, does not have a parent inside `already_matched`
                        if self._matches_rootmost(i, sentence_token, rooted_token, already_matched):
                            yield match_triple


    def _matches_rootmost(self, i, sentence_token, rooted_token, already_matched):
        r'''Return True iff `sentence_token` matches a rootmost element of self.mwe'''
        if self.matchability == 'BAG':
            return True
        if self.matchability in ('LABELED-ARC', 'UNLABELED-ARC'):
            # Only allow if it was expected to attach to root
            return rooted_token.dependency == Dependency('root', '0')
        assert False, self.matchability


    def _matches_in_tree(self, i, sentence_token, rooted_token, already_matched, expected_rooted_parent_rank):
        r'''Return True iff `sentence_token` matches non-rootmost element of self.mwe'''
        if self.matchability == 'BAG':
            return True
        if self.matchability == 'UNLABELED-ARC':
            return expected_rooted_parent_rank == rooted_token.dependency.parent_rank
        if self.matchability == 'LABELED-ARC':
            return (expected_rooted_parent_rank == rooted_token.dependency.parent_rank
                    and sentence_token.dependency.label == rooted_token.dependency.label)
        assert False, self.matchability


class MWEBagAlreadyMatched(collections.namedtuple('MWEBagAlreadyMatched', 'rank2rootedrank n_roots')):
    r'''Attributes:
    @type  rank2rootedrank: dict[str,str]
    @param rank2rootedrank: Mapping from rank in sentence to rank in rooted_tokens
    @type  n_roots: int
    @param n_roots: Number of roots already matched (greater than 1 for disconnected trees)
    '''
    def including(self, sentence_token, rooted_token):
        assert sentence_token.rank not in self.rank2rootedrank, \
                ('Already matched!', sentence_token, self.rank2rootedrank)
        new_rank2rootedrank = dict(self.rank2rootedrank)
        new_rank2rootedrank[sentence_token.rank] = rooted_token.rank
        new_n_roots = self.n_roots + int(sentence_token.dependency.parent_rank not in self.rank2rootedrank)
        return MWEBagAlreadyMatched(new_rank2rootedrank, new_n_roots)

MWEBagAlreadyMatched.EMPTY = MWEBagAlreadyMatched({}, 0)

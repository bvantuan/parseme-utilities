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
import json
import os
import re
import sys


# Import the Categories class
from categories import Categories


try:
    from pynlpl.formats import folia
except ImportError:
    exit("ERROR: PyNLPl not found, please run this code: pip3 install pynlpl")


# The `empty` field in CoNLL-U and PARSEME-TSV
EMPTY = "_"

# Languages where the canonical form should have the lemmas for all tokens
# Reason: HI = has many MVCs; HU = has bad POS tags
# (XXX this is a workaround, we should rethink this for ST 2.0)
LANGS_WITH_ALL_CANONICAL_TOKENS_LEMATIZED = set("HI HU".split())


############################################################

# Set of all valid languages in the latest PARSEME Shared-Task
LANGS = set("AR BG CS DE EL EN ES EU FA FR HE HR HU HI IT LT MT PL PT RO SL SV TR".split())

# Languages where the pronoun in IRV is canonically on the left
LANGS_WITH_CANONICAL_REFL_PRON_ON_LEFT = set("DE EU FR RO".split())

# Languages where the verb canonically appears to the right of the object complement (SOV/OSV/OVS)
LANGS_WITH_CANONICAL_VERB_ON_RIGHT = set("DE EU HI TR".split())

# Languages where the verb occurrences usually appear to the right of the object complement (SOV/OSV/OVS)
LANGS_WITH_VERB_OCCURRENCES_ON_RIGHT = LANGS_WITH_CANONICAL_VERB_ON_RIGHT - set(["DE"])


############################################################

# Flag indicating whether we want to use colors when writing to stderr
COLOR_STDERR = (sys.stderr.isatty() and 'DISABLE_ANSI_COLOR' not in os.environ)


############################################################

class ToplevelComment:
    r"""Represents a bare comment in a conllup file. May represent metadata."""
    GLOBAL_COLUMNS_REGEX = re.compile(rb'^# *global\.columns *= *(.*)$', re.MULTILINE)

    def __init__(self, file_path, lineno, text):
        self.file_path, self.lineno, self.text = file_path, lineno, text

    def to_tsv(self) -> str:
        r"""Return comment line in TSV syntax."""
        return '# {}'.format(self.text)


class UserInfoComment:
    r"""Represents a annotator comment in one of the files.
    In TSV files, this does NOT appear as top-level comment line
    (it appears inside a userinfo line instead).
    """
    def __init__(self, file_path, lineno, text, userinfo):
        self.file_path, self.lineno = file_path, lineno
        self.text, self.userinfo = text, userinfo

    @staticmethod
    def from_folia(folia_comment: folia.Comment):
        r"""Return a Comment instance for given FoLiA comment object."""
        fpath, lineno = folia_comment.doc.filename, None
        text = folia_comment.value
        ui = UserInfo.from_folia('comment', folia_comment)
        return UserInfoComment(fpath, lineno, text, ui)


class UserInfo:
    r"""Represents common meta-information.
    (This is basically the set of key-value properties
    that are always acceptable in all FoLiA nodes).

    Attributes:
    * annotator: Name or ID of the system/human annotator (or None).
    * annotatortype: Either "manual" or "auto" (or None).
    * confidence: Floating point value between zero and one (or None).
    * datetime: Date in format "YYYY-MM-DDThh:mm:ss" (or None).
    * int_id: Some 1-based integer identifier (or None). Corresponds to FoLiA "n".
    * ui_comments: A list of UserInfoComment instances.
    """
    # TODO XXX check if we actually need int_id...

    TSV_REGEX = re.compile(r'^# *userinfo.(\S*) *= *(.*)$')

    def __init__(self, scope: str, *,
                 annotator: str = None, annotatortype: str = None,
                 datetime: str = None, confidence: float = None,
                 int_id: int = None, ui_comments: list = None):
        self.scope = scope
        self.annotator = annotator
        self.annotatortype = annotatortype
        self.datetime = datetime
        self.confidence = confidence
        self.int_id = int_id
        self.ui_comments = ui_comments or []

    @staticmethod
    def from_folia(scope: str, f: folia.AbstractElement):
        r"""Return UserInfo for given FoLiA element `f`."""
        ui_comments = [UserInfoComment.from_folia(c) for c in f.select(folia.Comment)]
        return UserInfo(
            scope, annotator=f.annotator, annotatortype=f.annotatortype,
            datetime=f.datetime, confidence=f.confidence,
            int_id=f.n, ui_comments=ui_comments)

    def empty(self):
        r'''True iff all of the properties of this UserInfo are empty.'''
        return all(v is None for (k, v) in self._generic_properties()) and not self.ui_comments

    def _generic_properties(self):
        return [('int_id', self.int_id),
                ('annotator', self.annotator),
                ('annotatortype', self.annotatortype),
                ('datetime', self.datetime),
                ('confidence', self.confidence)]

    def to_dict(self):
        r"""Return an OrderedDict object that represents
        this userinfo (e.g. to be converted to JSON).
        """
        ret = collections.OrderedDict((k, v) \
            for k, v in self._generic_properties() if v is not None)
        if self.ui_comments:
            ret['ui_comments'] = []
            for ui_comment in self.ui_comments:
                ret['ui_comments'].append(ui_comment.userinfo.to_dict())
                ret['ui_comments'][-1]['text'] = ui_comment.text
        return ret

    @staticmethod
    def from_dict(scope, data_dict):
        r"""Return a UserInfo for given dict."""
        ret = UserInfo(scope)
        ret.int_id = data_dict.pop('int_id')
        ret.annotator = data_dict.pop('annotator')
        ret.annotatortype = data_dict.pop('annotatortype')
        ret.datetime = data_dict.pop('datetime')
        ret.confidence = data_dict.pop('confidence')
        ret.ui_comments = data_dict.pop('ui_comments', [])
        assert not data_dict, data_dict
        return ret

    def to_tsv(self) -> str:
        r"""Return comment line in TSV syntax."""
        import json
        d = collections.OrderedDict(("text", self.text))
        d['userinfo'] = self.userinfo.to_dict()
        j = json.dumps(self.userinfo.to_dict(update_with={"text": self.text}))
        return "# userinfo.{} = {}".format(scope, j)



############################################################

class MWEAnnot(collections.namedtuple('MWEAnnot', 'ranks category')):
    r"""Represents an MWE annotation.
    @type ranks: tuple[str]
    @type category: str
    """
    def __new__(cls, ranks, category):
        assert ranks
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



class Token(collections.Mapping):
    r"""Represents a token in an input file.

    Instances behave like a frozen dict, so you can do
    e.g. token["LEMMA"] to obtain the lemma.
    """
    def __init__(self, *args, **kwargs):
        data = dict(*args, **kwargs)
        # (Note we allow FORM=="_", because it can mean underspecified OR "_" itself
        self._data = {str(k): str(v) for (k, v) in data.items()
                      if v and (v != '_' or k == 'FORM')}
        self._data.setdefault('FORM', '_')

    def with_update(self, *args, **kwargs):
        r'''Return a copy Token with updated key-value pairs.'''
        ret = Token(self._data)
        ret._data.update(*args, **kwargs)
        return ret

    def with_nospace(self, no_space: bool):
        r'''Return a copy Token with updated MISC (only if no_space is True).'''
        if no_space and 'SpaceAfter=No' not in self.get('MISC', ''):
            new_misc = 'SpaceAfter=No'
            if self.get('MISC'):
                new_misc = "{}|{}".format(self['MISC'], new_misc)
            return self.with_update(MISC=new_misc)
        return self

    def lemma_or_surface(self):
        r'''Return the lemma, if known, or the surface form otherwise'''
        return self.get('LEMMA', self['FORM'])

    def __iter__(self):
        return iter(self._data)
    def __len__(self):
        return len(self._data)
    def __getitem__(self, key):
        return self._data[key]
    def __hash__(self):
        return hash(frozenset(self.items()))
    def __repr__(self):
        return 'Token({})'.format(self._data)

    def cmp_key(self):
        r'''Deterministic exception-free comparison method.'''
        return (self.rank, self.surface, self.nsp, self.get('LEMMA', ''),
                self.univ_pos, self.get('HEAD'), self.get('DEPREL'))

    @property
    def rank(self):
        return self['ID']
    @property
    def surface(self):
        return self['FORM']
    @property
    def nsp(self):
        return 'SpaceAfter=No' in self.get('MISC', '')
    @property
    def lemma(self):
        return self['LEMMA']
    @property
    def univ_pos(self):
        return self.get('UPOS')

    def has_dependency_info(self):
        return 'DEPREL' in self and 'HEAD' in self


class Sentence:
    r"""A sequence of tokens."""
    def __init__(self, file_path, nth_sent, lineno):
        self.file_path = file_path
        self.nth_sent = nth_sent
        self.lineno = lineno
        self.toplevel_comments = []  # type: list[ToplevelComment]
        self.tokens = []
        self.mweannots = []  # type: list[MWEAnnot]
        self.mweannots_folia = []  # type: list[folia.Entity]

    def __str__(self):
        r"""Return a string representation of the tokens"""
        return " ".join(map(lambda x: x.surface,self.tokens))

    def rank2index(self):
        r"""Return a dictionary mapping string ranks to indexes."""
        return {t.rank: index for (index, t) in enumerate(self.tokens)}

    def mwe_occurs(self, lang):
        r"""Yield MWEOccur instances for all MWEs in self."""
        rank2index = self.rank2index()
        for mwe_index, mweannot in enumerate(self.mweannots):
            userinfo = UserInfo("mwe")
            if self.mweannots_folia:
                userinfo = UserInfo.from_folia("mwe", self.mweannots_folia[mwe_index])
            userinfo.int_id = mwe_index
            indexes = mweannot.indexes(rank2index)
            assert indexes, (mweannot, rank2index)
            yield MWEOccur(lang, self, indexes, mweannot.category, userinfo)

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
                self.warn("Removed duplicate MWE: {}".format(mweannot))


    def re_tokenize(self, new_tokens, indexmap):
        r"""Replace `self.tokens` with given tokens and fix `self.mweannot` based on `indexmap`"""
        rank2index = self.rank2index()
        self_nsps = set(i for (i, t) in enumerate(self.tokens) if t.nsp)
        self.tokens = [t.with_nospace(i in self_nsps) for (i, t) in enumerate(new_tokens)]
        self.mweannots = [self._remap(m, rank2index, indexmap) for m in self.mweannots]

    def _remap(self, mweannot, rank2index, indexmap):
        r"""Remap `mweannot` using new `self.tokens`."""
        new_indexes = [i_new for i_old in mweannot.indexes(rank2index)
                for i_new in indexmap[i_old]]  # Python's syntax for a flatmap...
        return MWEAnnot(tuple(self.tokens[i].rank for i in new_indexes), mweannot.category)


    def id(self, *, short=False):
        r"""Return a sentence ID, such as "foo.xml(s.13):78"."""
        ret = self.file_path if not short else os.path.basename(self.file_path)
        ret += "(s.{})".format(self.nth_sent) if self.nth_sent else ""
        return ret + (":{}".format(self.lineno) if self.lineno else "")

    def warn(self, msg_fmt, **kwargs):
        r"""Print a warning message; e.g. "foo.xml:13: blablabla"."""
        do_warn(msg_fmt, prefix=self.id(short=True), **kwargs)


    def check_token_data(self):
        r"""Check token data and emit warnings if they are malformed
        (e.g. if a token contains spaces inside the surface form).
        """
        for token in self.tokens:
            for fieldname in ['FORM', 'LEMMA']:
                if " " in token.get(fieldname, ""):
                    self.warn("Token #{} contains spaces in field `{}`"
                              .format(token.rank, fieldname))


    def iter_root_to_leaf_all_tokens(self):
        r'''Yield all Tokens in sentence, from root to leaves (aka topological sort).
        May NOT yield all tokens if there is missing dependency information.
        '''
        children = collections.defaultdict(list)  # dict[str, list[Token]]
        for token in self.tokens:
            if token.has_dependency_info():
                children[token['HEAD']].append(token)
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
            warn_once(self.id(), 'Category {categ} renamed to {new_categ}',
                      categ=categ, new_categ=new_categ)
            return new_categ
        warn_once(self.id(), 'Category {categ} is unknown', categ=categ)
        return categ


    def print_tsv_comments(self, lang: str):
        r"""Print comments in TSV format."""
        for toplevel_comment in self.toplevel_comments:
            print(toplevel_comment.to_tsv())
        for mweoccur in self.mwe_occurs(lang):
            print(mweoccur.userinfo.to_tsv())


class MWEOccur:
    r"""Represents an instance of a MWE in text.
    In a type/token distinction: MWELexicalItem is a type and MWEOccur is a token.

    Parameters:
    @type  lang: str
    @param lang: one of the languages from the `LANGS` global
    @type  sentence: Sentence
    @param sentence: the sentence in which this MWEOccur was seen
    @type  indexes: list[int]
    @param indexes: the indexes of the MWE inside `sentence`
    @type  category: str
    @param category: one of {VID, LVC, IRV...}

    Attributes:
    @type  raw: MWEOccurView
    @param raw: represents tokens for raw form, as seen in text
    @type  fixed: MWEOccurView
    @param fixed: represents tokens in fixed form (e.g. homogenizing lemmas)
    @type  reordered: MWEOccurView
    @param reordered: represents tokens in reordered form (e.g. normalizing word-order for LVCs)
    """
    def __init__(self, lang: str, sentence: Sentence,
                 indexes: list, category: str, userinfo: UserInfo):
        assert lang in LANGS
        self.lang = lang
        self.sentence = sentence
        self.indexes = tuple(sorted(indexes))
        self.category = category
        self.userinfo = userinfo

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
        return "MWEOccur<{}>".format(" ".join(self.reordered.likely_canonicform))

    def suspiciously_similar(self, other: 'MWEOccur'):
        r'''Return True iff self and other are likely to be the same MWE
        (used e.g. to avoid predicting spurious Skipped occurrences).
        '''
        return self.sentence.file_path == other.sentence.file_path \
            and self.sentence.nth_sent == other.sentence.nth_sent \
            and (set(self.indexes) & set(other.indexes))


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
    @type  likely_canonicform: list[str]
    @param likely_canonicform: List of lemmas (or surfaces) for MWE tokens in this MWEOccurView.
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
        self.likely_lemmatizedform = self._lemmatized_at(range(len(self.tokens)))    
        self.likely_canonicform = self._likely_canonicform()

    def _i_head(self):
        r"""Index of head verb in `likely_canonicform`
        (First word if there is no POS info available)."""
        i_verbs = [i for (i, t) in enumerate(self.tokens) if t.univ_pos == "VERB"] \
                or [(-1 if self.mwe_occur.lang in LANGS_WITH_VERB_OCCURRENCES_ON_RIGHT else 0)]
        return i_verbs[0]  # just take first verb that appears

    def _i_subhead(self):
        r"""Index of sub-head noun in `likely_canonicform` (very useful for LVCs)."""
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

    def _likely_canonicform(self):
        r"""Return a lemmatized form of this MWE."""
        if self.mwe_occur.lang in LANGS_WITH_ALL_CANONICAL_TOKENS_LEMATIZED:
            return self.likely_lemmatizedform
        indexes = [self.i_head, self.i_subhead, self._i_reflpron()]
        return self._lemmatized_at([i for i in indexes if i is not None])


    def _lemmatized_at(self, indexes):
        r"""Return a tuple[str] with surfaces from self.tokens, lemmatized at given indexes."""
        ret = [t.surface for t in self.tokens]
        for i in indexes:
            ret[i] = self.tokens[i].lemma_or_surface()
        return tuple(x.casefold() for x in ret)


    def _with_fixed_tokens(self):
        r"""Return a fixed version of `self.tokens` (must keep same length & order)."""
        fixed = tuple(self._fixed_token(t) for t in self.tokens)
        return MWEOccurView(self.mwe_occur, fixed)

    def _fixed_token(self, token):
        r"""Return a manually fixed version of `token` (e.g. homogenize lemmas for IRVs)."""
        if token.univ_pos == "PRON" and Categories.is_inherently_reflexive_verb(self.mwe_occur.category):
            # Normalize reflexive pronouns, e.g. FR "me" or "te" => "se"
            if self.mwe_occur.lang in ["PT", "ES", "FR"]:
                token = token.with_update(LEMMA="se")
            if self.mwe_occur.lang == "IT":
                token = token.with_update(LEMMA="si")
            if self.mwe_occur.lang == "EN":
                token = token.with_update(LEMMA="oneself")
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
        May NOT yield all tokens if there is missing dependency information.
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
    * Tokens that had parent_rank=='0' keep their old dependency info.
    '''
    ret = []
    oldrank2new = {'0': '0'}
    for t in tokens:
        oldrank2new[t.rank] = str(len(ret)+1)
        t = t.with_update(ID=oldrank2new[t.rank])

        if t['HEAD'] in oldrank2new:
            t = t.with_update(HEAD=oldrank2new[t['HEAD']])
        else:
            t = t.with_update(DEPREL='root', HEAD='0')
        ret.append(t)
    return ret



class RootedMWEOccur(collections.namedtuple('RootedMWEOccur', 'mweoccur rooted_tokens')):
    r"""Represents an MWEOccur along with its tokens in root-to-leaf order"""
    def n_attachments_to_root(self):
        r"""Return the number of syntactic attachments where HEAD=='0'."""
        return sum(1 for t in self.rooted_tokens if t.get('HEAD') == '0')

    def cmp_key(self):
        r'''Deterministic exception-free comparison method.'''
        return [t.cmp_key() for t in self.rooted_tokens]


class RootedMWEOccurList(list):
    r"""List of RootedMWEOccur objects sharing the same lemma+syntax)."""
    def __gt__(self, other):
        r"""A RootedMWEOccurList is greater than another one if (in this order):
        * It has the fewest attachments to root (we don't like disconnected subtrees).
        * It has the most number of examples in rooted_tokens (we want the most common lemma+syntax).
        * It has smaller RootedMWEOccur.cmp_key() value (tie-breaker, for determinism).
        """
        if self[0].n_attachments_to_root() < other[0].n_attachments_to_root():
            return True  # (all elements in a RootedMWEOccurList should have the same `n` attachments)
        if len(self) > len(other):
            return True
        return [t.cmp_key() for t in self] < [t.cmp_key() for t in other]



class MWELexicalItem:
    r'''Represents a group of `MWEOccur`s that share the same canonical form.
    In a type/token distinction: MWELexicalItem is a type and MWEOccur is a token.

    For example, an LVC with these MWEOccurs
      ["taking shower", "took shower", "shower taken"]
    would ideally be grouped into MWELexicalItem with canonicform "take shower".
    
    Parameters:
    @type  mweoccurs: list[MWEOccur]
    @param mweoccurs: a list of MWEOccur instances (read-only!)

    Attributes:
    @type  i_head: int
    @param i_head: index of head verb
    @type  i_subhead: Optional[int]
    @param i_subhead: index of sub-head noun
    '''
    def __init__(self, mweoccurs: list):
        self.mweoccurs = mweoccurs
        self.canonicform = most_common(m.reordered.likely_canonicform for m in mweoccurs)
        self._seen_mweoccur_ids = {m.id() for m in self.mweoccurs}  # type: set[str]

        self.i_head = most_common(m.reordered.i_head for m in mweoccurs)
        nounbased_mweos = [m.reordered.i_subhead for m in mweoccurs
                           if m.reordered.i_subhead is not None]
        self.i_subhead = most_common(nounbased_mweos, fallback=None)


    def only_non_vmwes(self):
        r'''True iff all mweoccurs are NonVMWEs.'''
        return all((o.category in Categories.NON_MWES and o.userinfo.confidence is None) for o in self.mweoccurs)

    def contains_mweoccur(self, mweoccur):
        r'''True iff self.mweoccurs contains given MWEOccur.'''
        return (mweoccur.id() in self._seen_mweoccur_ids)

    def add_skipped_mweoccur(self, mweoccur):
        r'''Add MWEOccur to this MWE descriptor. If this MWEOccur already exists, does nothing.'''
        assert mweoccur.category == 'Skipped'  # we do not need to update i_head/i_subhead for Skipped
        mweoccur_id = mweoccur.id()
        if not any(mweoccur.suspiciously_similar(m) for m in self.mweoccurs):
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

        @rtype RootedMWEOccur.
        '''
        lemmasyntax2rootedmweoccur = collections.defaultdict(RootedMWEOccurList)

        for mweoccur in self.mweoccurs:
            rooted_tokens = tuple(rerooted(mweoccur.raw.iter_root_to_leaf_mwe_tokens()))
            lemmasyntax = tuple((t.lemma_or_surface(), t.get('HEAD'), t.get('DEPREL')) for t in rooted_tokens)
            lemmasyntax2rootedmweoccur[lemmasyntax].append(
                RootedMWEOccur(mweoccur, rooted_tokens))

        majority_mweoccurs = max(lemmasyntax2rootedmweoccur.values())
        return max(majority_mweoccurs, key=RootedMWEOccur.cmp_key)


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


class FrozenCounter(collections.Counter):
    r'''Instance of Counter that can be hashed. Should not be modified.'''
    def __hash__(self):
        return hash(frozenset(self.items()))



############################################################

# Leave the preferable PATH_FMT in PATH_FMTS[-1]
PATH_FMTS = ["{d}/{b}.conllu", "{d}/conllu/{b}.conllu"]


def calculate_conllu_paths(file_paths, warn=True):
    r"""Return CoNLL-U paths, or None on failure to find some of them."""
    ret = []
    for file_path in file_paths:
        dirname, basename = os.path.split(file_path)
        if not dirname: dirname = "."  # seriously, python...

        basename = basename_without_ext(basename)
        for path_fmt in ["{d}/{b}.conllu", "{d}/conllu/{b}.conllu"]:
            ret_path = path_fmt.format(d=dirname, b=basename)
            if os.path.exists(ret_path):
                if warn:
                    do_warn("Using CoNLL-U file `{p}`", p=ret_path, warntype="INFO")
                ret.append(ret_path)
                break

        else:
            if warn:
                do_warn("CoNLL-U file `{p}` not found", p=ret_path)
                do_warn("Not using any CoNLL-U file")
                return None
    return ret


RE_BASENAME_NOEXT = re.compile(
    r'^(?:.*/)*(.*?)(\.(folia|xml|conllu|conllup|parsemetsv|tsv|tar|gz|bz2|zip))*$')

def basename_without_ext(filepath):
    r"""Return the basename of `filepath` without any known extensions."""
    return RE_BASENAME_NOEXT.match(filepath).group(1)


#####################################################################

def iter_aligned_files(file_paths, conllu_paths=None,
        *, keep_nvmwes=False, default_mwe_category=None,
        keep_dup_mwes=False, keep_mwe_random_order=False, debug=False):
    r"""iter_aligned_files(list[str], list[str]) -> Iterable[Sentence]
    Yield Sentence instances based on file_paths and conllu_paths.
    """
    for entity in AlignedIterator.from_paths(
            file_paths, conllu_paths, default_mwe_category=default_mwe_category, debug=debug):
        if not keep_nvmwes:
            entity.remove_non_vmwes()
        if not keep_dup_mwes:
            entity.remove_duplicate_mwes()
        if not keep_mwe_random_order:
            entity.mweannots.sort()
        yield entity


def _iter_parseme_file(file_path, default_mwe_category):
    fileobj = open(file_path, 'r')
    if b'FoLiA' in fileobj.buffer.peek(1024):
        return FoliaIterator(file_path, fileobj)
    if b'global.columns' in fileobj.buffer.peek(1024):
        return ConllpIterator(file_path, fileobj, default_mwe_category)
    return ParsemeTSVIterator(file_path, fileobj, default_mwe_category)


class AlignedIterator:
    r"""Yield Sentence instances based on the given iterators."""
    def __init__(self, main_iterator, conllu_iterator, debug=False):
        self.main_iterator = main_iterator
        self.conllu_iterator = conllu_iterator
        self.main = collections.deque(main_iterator)
        self.conllu = collections.deque(conllu_iterator)
        self.debug = debug

    def __iter__(self):
        while self.main or self.conllu:
            _warn_if_none(
                self.main[0] if self.main else None,
                self.conllu[0] if self.conllu else None)
            main_s = self.main.popleft()
            conllu_s = self.conllu.popleft()

            if self.conllu:
                # Ignore all ToplevelComments in TSV (do NOT yield them)
                # Yield ToplevelComments in from CoNLL-U instead
                main_s.toplevel_comments = conllu_s.toplevel_comments

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
                conllu_sentence.warn(
                    "Adding tokens from CoNLL: {surf!r} with rank {rank!r}",
                    surf=[t.surface for t in tokens], rank=[t.rank for t in tokens], warntype='DEBUG')


    @staticmethod
    def from_paths(main_paths, conllu_paths, *, default_mwe_category=None, debug=False):
        r"""Return an AlignedIterator for the given paths.
        (Special case: if conllu_paths is None, return a simpler kind of iterator)."""
        chain_iter = itertools.chain.from_iterable
        main_iterator = chain_iter(_iter_parseme_file(p, default_mwe_category) for p in main_paths)
        if not conllu_paths:
            return main_iterator
        conllu_iterator = chain_iter(ConllIterator(p, open(p, 'r'), default_mwe_category) for p in conllu_paths)
        return AlignedIterator(main_iterator, conllu_iterator, debug)


def _warn_if_none(main_sentence, conllu_sentence):
    assert conllu_sentence or main_sentence

    if not main_sentence:
        conllu_sentence.warn("CoNLL-U sentence #{n} found, but there is " \
                "no matching PARSEME-TSV input file", n=conllu_sentence.nth_sent, error=True)
    if not conllu_sentence:
        main_sentence.warn("PARSEME-TSV sentence #{n} found, but there is " \
                "no matching CoNLL-U input file", n=main_sentence.nth_sent, error=True)


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
                _warn_if_none(first_main_sent, first_conllu_sent)

                m, c = mismatch_main.start-1, mismatch_conllu.start-1
                for m, c in zip(mismatch_main, mismatch_conllu):
                    tokalign = TokenAligner(self.main_sentences[m], self.conllu_sentences[c])
                    if not tokalign.is_alignable():
                        tokalign.msg_unalignable(error=False)
                        self.print_context(m, c)
                        do_error("Mismatched sentences")
                else:
                    # zipped ranges are OK, the error is in the end of one of the ranges
                    end_mismatch_main = range(m+1, mismatch_main.stop)
                    end_mismatch_conllu = range(c+1, mismatch_conllu.stop)
                    assert not end_mismatch_main or not end_mismatch_conllu
                    for m in end_mismatch_main:
                        self.main_sentences[m].warn(
                            "PARSEME sentence #{n} does not match anything in CoNLL-U",
                            n=self.main_sentences[m].nth_sent, error=True)
                        self.print_context(m, end_mismatch_conllu.start)
                    for c in end_mismatch_conllu:
                        self.conllu_sentences[c].warn(
                            "CoNLL-U sentence #{n} does not match anything in PARSEME",
                            n=self.conllu_sentences[c].nth_sent, error=True)
                        self.print_context(end_mismatch_main.start, c)

    def print_context(self, main_index, conllu_index):
        self.print_context_sents("PARSEME", self.main_sentences[max(0,main_index-1):main_index+2])
        self.print_context_sents("CoNLL-U", self.conllu_sentences[max(0,conllu_index-1):conllu_index+2])

    def print_context_sents(self, info, sentences):
        for sent in sentences:
            sent.warn(
                "{} sentence #{} = {} ...".format(info, sent.nth_sent,
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
            self.msg_unalignable(error=True)
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
                self.conllu_sentence.warn(
                        "Adding tokens from CoNLL: {surf!r} with rank {rank!r}",
                        surf=[t.surface for t in tokens], rank=[t.rank for t in tokens], warntype="DEBUG")


    def msg_unalignable(self, error=False):
        r"""Error issued if we cannot align tokens."""
        self.conllu_sentence.warn(
            "CoNLL-U sentence #{n} does not match {id} sentence #{n2}",
            n=self.conllu_sentence.nth_sent, id=self.main_sentence.id(),
            n2=self.main_sentence.nth_sent, error=error)


    def warn_gap_main(self, main_range, conllu_range, all_mwe_codes):
        r"""Warn when there are unmapped characters in main file."""
        main_toks = [self.main_sentence.tokens[i].surface for i in main_range]
        #conllu_toks = [self.conllu_sentence.tokens[i].surface for i in conllu_range]

        mwe_codes_info = " (MWEs={})".format(";".join(map(str,all_mwe_codes))) if all_mwe_codes else ""
        self.main_sentence.warn(
            "Ignoring extra tokens in sentence #{n} ({id}): {toks!r}{mwe}",
            n=self.main_sentence.nth_sent, id=self.conllu_sentence.id(),
            toks=main_toks, mwe=mwe_codes_info)


############################################################

class FoliaIterator:
    r"""Yield Sentence's for file_path."""
    def __init__(self, file_path, fileobj):
        self.file_path = file_path
        self.fileobj = fileobj

    def __iter__(self):
        doc = folia.Document(string=self.fileobj.read())
        doc.filename = self.fileobj
        for folia_nonembedded_entitieslayer in doc.select(folia.EntitiesLayer, recursive=False):
            for folia_nonembedded_entity in folia_nonembedded_entitieslayer.select(folia.Entity):
                do_warn('Ignoring MWE outside the scope of a single sentence: {id!r}',
                        prefix=os.path.basename(self.file_path), id=folia_nonembedded_entity.id)

        for nth, folia_sentence in enumerate(doc.select(folia.Sentence), 1):
            current_sentence = Sentence(self.file_path, nth, None)
            mwes = list(folia_sentence.select(folia.Entity))
            self.calc_mweannots(mwes, folia_sentence, current_sentence)

            for rank, word in enumerate(folia_sentence.words(), 1):
                # ID FORM LEMMA UPOS XPOS FEATS HEAD DEPREL DEPS MISC
                conllu = {
                    'ID': str(rank),
                    'FORM': word.text() or '_',
                    'MISC': ('' if word.space else 'SpaceAfter=No'),
                }
                current_sentence.tokens.append(Token(conllu))

            yield current_sentence


    def calc_mweannots(self, mwes, folia_sentence, output_sentence):
        sent_word_ids = [w.id for w in folia_sentence.select(folia.Word)]
        for mwe in mwes:
            mwe_word_ids = [w.id for w in mwe.wrefs()]
            if not mwe_word_ids:  # ignore empty Entities produced by FLAT
                output_sentence.warn('Ignoring empty MWE: {id!r}', id=mwe.id)
            elif any(w.id not in sent_word_ids for w in mwe.wrefs()):
                output_sentence.warn('Ignoring misplaced MWE: {id!r}', id=mwe.id)
            else:
                ranks = [w.id.rsplit(".",1)[-1] for w in mwe.wrefs()]
                categ = output_sentence.check_and_convert_categ(mwe.cls)
                output_sentence.mweannots.append(MWEAnnot(ranks, categ))
                output_sentence.mweannots_folia.append(mwe)



class AbstractFileIterator:
    r'''Parameters:
    @param file_path: path to file that we will iterate (str)
    @param default_mwe_category: category to use when one is missing (str);
                                 if not specified, raises an error instead
    '''
    def __init__(self, file_path, fileobj, default_mwe_category):
        self.file_path = file_path
        self.fileobj = fileobj
        self.default_mwe_category = default_mwe_category
        self.nth_sent = 0
        self.lineno = 0
        self._new_sent()

    def _new_sent(self):
        self.nth_sent += 1
        self.curr_sent = Sentence(self.file_path, self.nth_sent, self.lineno+1)
        self.pending_userinfo = []
        self.id2mwe_categ = {}
        self.id2mwe_ranks = collections.defaultdict(list)

    def get_token_and_mwecodes(self, fields: list) -> (Token, list):
        r"""Return a Token and a list of mwecodes (str)
        for the list of fields in current line.
        """
        return NotImplementedError('Abstract method')

    def finish_sentence(self):
        r"""Return finished `self.curr_sent`."""
        if not self.curr_sent:
            self.warn("Unexpected empty line")
        s = self.curr_sent
        if self.default_mwe_category:
            for key in self.id2mwe_ranks:
                self.id2mwe_categ.setdefault(key, self.default_mwe_category)
        try:
            s.mweannots = [MWEAnnot(tuple(self.id2mwe_ranks[id]),
                self.id2mwe_categ[id]) for id in sorted(self.id2mwe_ranks)]
        except KeyError as e:
            self.warn("MWE has no category: {categ}", categ=e.args[0])
        self._new_sent()
        s.check_token_data()
        return s

    def warn(self, msg_fmt, **kwargs):
        do_warn(msg_fmt, prefix="{}:{}".format(self.file_path, self.lineno), **kwargs)

    def make_comment(self, line):
        if self.curr_sent.tokens:
            self.warn("Comment in the middle of a sentence is not allowed")
        match = UserInfo.TSV_REGEX.match(line)
        if match:
            scope, json_str = match.groups()
            self.pending_userinfo.append(UserInfo.from_dict(
                scope, json.loads(json_str)))
        else:
            self.curr_sent.toplevel_comments.append(ToplevelComment(
                self.file_path, self.lineno, line[1:].strip()))

    def append_token(self, line):
        token, mwecodes = self.get_token_and_mwecodes(line.split("\t"))  # method defined in subclass

        for mwecode in mwecodes:
            index_and_categ = mwecode.split(":")
            self.id2mwe_ranks[index_and_categ[0]].append(token.rank)
            if len(index_and_categ) == 2 and index_and_categ[1]:
                categ = self.curr_sent.check_and_convert_categ(index_and_categ[1])
                self.id2mwe_categ.setdefault(index_and_categ[0], categ)
        self.curr_sent.tokens.append(token)

    def __iter__(self):
        with self.fileobj:
            yield from self.iter_header(self.fileobj)
            for self.lineno, line in enumerate(self.fileobj, 1):
                try:
                    line = line.strip("\n")
                    if line.startswith("#"):
                        self.make_comment(line)
                    elif not line.strip():
                        yield self.finish_sentence()
                    else:
                        self.append_token(line)
                except:
                    self.warn("Error when reading token", warntype="FATAL")
                    raise
            yield from self.iter_footer(self.fileobj)

    def iter_header(self, f):
        return []  # Nothing to yield on header

    def iter_footer(self, f):
        return []  # Nothing to yield on footer


class ConllIterator(AbstractFileIterator):
    UD_KEYS = 'ID FORM LEMMA UPOS XPOS FEATS HEAD DEPREL DEPS MISC'.split()

    def get_token_and_mwecodes(self, data):
        if len(data) != 10:
            self.warn("Line has {n} columns, not 10", n=len(data))
        return Token(zip(self.UD_KEYS, data)), []


class ConllpIterator(AbstractFileIterator):
    def __init__(self, file_path, fileobj, default_mwe_category):
        super().__init__(file_path, fileobj, default_mwe_category)
        first_lines = fileobj.buffer.peek(1024*10)
        colnames = ToplevelComment.GLOBAL_COLUMNS_REGEX.search(first_lines).group(1)
        self.colnames = tuple(colnames.decode('utf8').split())

    def get_token_and_mwecodes(self, data):
        if len(data) != len(self.colnames):
            self.warn("Line has {n} columns, not {n_exp}", n=len(data), n_exp=len(self.colnames))
        tokendict = dict(zip(self.colnames, data))
        mwe_codes = tokendict.pop('PARSEME:MWE') or "_"
        m = mwe_codes.split(";") if mwe_codes not in "_*" else []
        return Token(tokendict), m


class ParsemeTSVIterator(AbstractFileIterator):
    def get_token_and_mwecodes(self, data):
        if len(data) == 5:
            warn_once(
                "{}:{}".format(self.file_path, self.lineno),
                "Silently ignoring 5th parsemetsv column")
            data.pop()  # remove data[-1]
        elif len(data) != 4:
            self.warn("Line has {n} columns, not 4", n=len(data))
        # ID FORM LEMMA UPOS XPOS FEATS HEAD DEPREL DEPS MISC
        conllu = {
            'ID': data[0],
            'FORM': data[1] or '_',
            'MISC': ('SpaceAfter=No' if data[2]=='nsp' else ''),
        }
        mwe_codes = data[3]
        m = mwe_codes.split(";") if mwe_codes not in "_*" else []
        return Token(conllu), m



############################################################

_WARNED = set()

def warn_once(first_seen_here, msg_fmt, **kwargs):
    r"""Same as do_warn, but only called once per msg_fmt."""
    actual_msg = msg_fmt.format(**kwargs)
    if actual_msg not in _WARNED:
        _WARNED.add(actual_msg)
        do_warn(msg_fmt, **kwargs)
        do_warn('First seen here: {here}', here=first_seen_here, header=False)
        do_warn('(Ignoring further warnings of this type)', header=False)


def do_info(msg_fmt, **kwargs):
    r"""Same as do_warn, but using warntype=="INFO"."""
    do_warn(msg_fmt, **kwargs, warntype="INFO")

def do_error(msg_fmt, **kwargs):
    r"""Same as do_warn, but using warntype=="ERROR" (calls exit)."""
    do_warn(msg_fmt, **kwargs, warntype="ERROR")


def do_warn(msg_fmt, *, prefix=None, warntype=None, error=False, header=True, **kwargs):
    r"""Print a warning message "prefix: msg"; e.g. "foo.xml:13: blablabla"."""
    warntype = ("ERROR" if error else warntype) or "WARNING"
    dot_warntype = warntype if header else '.'*len(warntype)

    msg = msg_fmt.format(**kwargs)
    prefix = "{}: {}".format(prefix, dot_warntype) if prefix else dot_warntype
    final_msg = "{}: {}".format(prefix, msg)

    if COLOR_STDERR:
        if not header:
            color = '38;5;245'  # ANSI color: grey
        elif warntype == "ERROR":
            color = 31          # ANSI color: red
        elif warntype == "INFO":
            color = 34          # ANSI color: blue
        elif warntype == "FATAL":
            color = '7;31'      # ANSI color: red+invert
        else:
            color = 33  # ANSI color: yellow
        final_msg = "\x1b[{}m{}\x1b[m".format(color, final_msg)

    print(final_msg, file=sys.stderr)
    if warntype == "ERROR":
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
    lf2mweoccurs = _lemmatizedform2mweoccurs(lang, iter_sentences)  # type: dict[tuple[str], list[MWEOccur]]
    lemmatizedform2mwe_mixed = collections.OrderedDict()  # type: dict[tuple[str], MWELexicalItem]
    lemmatizedform2mwe_nvmwe = collections.OrderedDict()  # type: dict[tuple[str], MWELexicalItem]

    for lemmatizedform, mweoccurs in lf2mweoccurs.items():
        mwe = MWELexicalItem(mweoccurs)
        if mwe.only_non_vmwes():
            lemmatizedform2mwe_nvmwe[lemmatizedform] = mwe
        else:
            lemmatizedform2mwe_mixed[lemmatizedform] = mwe
    return (list(lemmatizedform2mwe_mixed.values()), list(lemmatizedform2mwe_nvmwe.values()))


def _lemmatizedform2mweoccurs(lang, iter_sentences):
    r'''Return a dict[tuple[str], list[MWEOccur]].'''
    ret = collections.defaultdict(list)  # type: dict[tuple[str], list[MWEOccur]]
    for sentence in iter_sentences:
        for mwe_occur in sentence.mwe_occurs(lang):
            lemmatizedform = FrozenCounter(mwe_occur.reordered.likely_lemmatizedform)
            ret[lemmatizedform].append(mwe_occur)
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
        userinfo = UserInfo("mwe", annotator='autodetect', annotatortype='auto')
        new_occur = MWEOccur(self.lang, sentence, indexes, "Skipped", userinfo)
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
            unmatched_words[wordform] -= 1
            if unmatched_words[wordform] == 0:
                unmatched_words.pop(wordform)  # so verbose...
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
            rootedmweoccur = mwe.most_common_rooted_tokens_and_example()
            example_mweoccur, rooted_tokens = rootedmweoccur
            n_roots = rootedmweoccur.n_attachments_to_root()

            if not all(t.has_dependency_info() for t in rooted_tokens):
                example_mweoccur.sentence.warn(
                    'Skipping MWE with partial dependency info: {}'.format("_".join(mwe.canonicform)))
                continue

            if favor_precision and n_roots > 1:
                example_mweoccur.sentence.warn(
                    'Skipping MWE with disconnected syntax tree: {}'.format('_'.join(mwe.canonicform)))
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
            if not sentence_token.has_dependency_info():
                continue  # If we have no dependency info, avoid false positives

            for wordform in [sentence_token.lemma_or_surface().lower(), sentence_token.surface.lower()]:
                for rooted_token in unmatched_lemmabag[wordform]:
                    match_triple = (i, sentence_token, rooted_token)

                    if sentence_token['HEAD'] in already_matched.rank2rootedrank:
                        # Non-rootmost token, connected to someone in `already_matched`
                        expected_rooted_parent_rank = already_matched.rank2rootedrank[sentence_token['HEAD']]
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
            return rooted_token['HEAD'] == '0'
        assert False, self.matchability


    def _matches_in_tree(self, i, sentence_token, rooted_token, already_matched, expected_rooted_parent_rank):
        r'''Return True iff `sentence_token` matches non-rootmost element of self.mwe'''
        if self.matchability == 'BAG':
            return True
        if self.matchability == 'UNLABELED-ARC':
            return expected_rooted_parent_rank == rooted_token['HEAD']
        if self.matchability == 'LABELED-ARC':
            return (expected_rooted_parent_rank == rooted_token['HEAD']
                    and sentence_token['DEPREL'] == rooted_token['DEPREL'])
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
        new_n_roots = self.n_roots + int(sentence_token.get('HEAD', '0') not in self.rank2rootedrank)
        return MWEBagAlreadyMatched(new_rank2rootedrank, new_n_roots)

MWEBagAlreadyMatched.EMPTY = MWEBagAlreadyMatched({}, 0)

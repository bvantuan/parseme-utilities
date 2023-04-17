#! /usr/bin/env python3
# Original code (2015) by Filip Ginter and Sampo Pyysalo.
# DZ 2018-11-04: Porting the validator to Python 3.
# DZ: Many subsequent changes. See the git history.

# Modified on 13/04/2023 for PARSEME corpora validation
# Level 1 and level 2 from UD are used
# Add tests on PARSEME:MWE column
import fileinput
import sys
import io
import os.path
import argparse
import logging
import traceback
# According to https://stackoverflow.com/questions/1832893/python-regex-matching-unicode-properties,
# the regex module has the same API as re but it can check Unicode character properties using \p{}
# as in Perl.
#import re
import regex as re
import unicodedata
import json


THISDIR=os.path.dirname(os.path.realpath(os.path.abspath(__file__))) # The folder where this script resides.

# Constants for the column indices
COLCOUNT=11
ID,FORM,LEMMA,UPOS,XPOS,FEATS,HEAD,DEPREL,DEPS,MISC,MWE=range(COLCOUNT)
COLNAMES='ID,FORM,LEMMA,UPOS,XPOS,FEATS,HEAD,DEPREL,DEPS,MISC,PARSEME:MWE'.split(',')
TOKENSWSPACE=MISC+1 # one extra constant
AUX=MISC+2 # another extra constant
COP=MISC+3 # another extra constant
# default MWE annotation
DEFAULT_MWE='*'

# Global variables:
curr_line = 0 # Current line in the input file
comment_start_line = 0 # The line in the input file on which the current sentence starts, including sentence-level comments.
sentence_line = 0 # The line in the input file on which the current sentence starts (the first node/token line, skipping comments)
sentence_id = None # The most recently read sentence id
line_of_first_morpho_feature = None # features are optional, but if the treebank has features, then some become required
delayed_feature_errors = {}
line_of_first_enhanced_graph = None
line_of_first_tree_without_enhanced_graph = None
error_counter = {} # key: error type value: error count
mwt_typo_span_end = None # if Typo=Yes at multiword token, what is the end of the multiword span?
depreldata = {} # key: language code (deprel data loaded from deprels.json)


###### Support functions

def is_whitespace(line):
    # checks if the entire line consists of only whitespace characters. 
    return re.match(r"^\s+$", line)

def is_word(cols):
    return re.match(r"^[1-9][0-9]*$", cols[ID])

def is_multiword_token(cols):
    return re.match(r"^[1-9][0-9]*-[1-9][0-9]*$", cols[ID])

def is_empty_node(cols):
    return re.match(r"^[0-9]+\.[1-9][0-9]*$", cols[ID])

def parse_empty_node_id(cols):
    m = re.match(r"^([0-9]+)\.([0-9]+)$", cols[ID])
    assert m, 'parse_empty_node_id with non-empty node'
    return m.groups()

def lspec2ud(deprel):
    return deprel.split(':', 1)[0]

def load_file(filename):
    res = set()
    with io.open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            line=line.strip()
            if not line or line.startswith('#'):
                continue
            res.add(line)
    return res

def load_upos_set(filename):
    """
    Loads the list of permitted UPOS tags and returns it as a set.
    """
    res = load_file(os.path.join(THISDIR, 'data', filename))
    return res

def get_depreldata_for_language(lcode):
    """
    Searches the previously loaded database of dependency relation labels.
    Returns the lists for a given language code. For most CoNLL-U files,
    this function is called only once at the beginning. However, some files
    contain code-switched data and we may temporarily need to validate
    another language.
    """
    global depreldata
    deprelset = set()
    # If lcode is 'ud', we should permit all universal dependency relations,
    # regardless of language-specific documentation.
    ###!!! We should be able to take them from the documentation JSON files instead of listing them here.
    if lcode == 'ud':
        deprelset = set(['nsubj', 'obj', 'iobj', 'csubj', 'ccomp', 'xcomp', 'obl', 'vocative', 'expl', 'dislocated', 'advcl', 'advmod', 'discourse', 'aux', 'cop', 'mark', 'nmod', 'appos', 'nummod', 'acl', 'amod', 'det', 'clf', 'case', 'conj', 'cc', 'fixed', 'flat', 'compound', 'list', 'parataxis', 'orphan', 'goeswith', 'reparandum', 'punct', 'root', 'dep'])
    elif lcode in depreldata:
        for r in depreldata[lcode]:
            if depreldata[lcode][r]['permitted'] > 0:
                deprelset.add(r)
    return deprelset

def load_deprel_set(filename_langspec, lcode):
    """
    Loads the list of permitted relation types and returns it as a set.
    """
    global depreldata
    global warn_on_undoc_deps
    with open(os.path.join(THISDIR, 'data', filename_langspec), 'r', encoding='utf-8') as f:
        all_deprels_0 = json.load(f)
    depreldata = all_deprels_0['deprels']
    deprelset = get_depreldata_for_language(lcode)
    # Prepare a global message about permitted relation labels. We will add
    # it to the first error message about an unknown relation. Note that this
    # global information pertains to the default validation language and it
    # should not be used with code-switched segments in alternative languages.
    msg = ''
    if len(deprelset) == 0:
        msg += "No dependency relation types have been permitted for language [%s].\n" % (lcode)
        msg += "They can be permitted at the address below (if the language has an ISO code and is registered with UD):\n"
        msg += "https://quest.ms.mff.cuni.cz/udvalidator/cgi-bin/unidep/langspec/specify_deprel.pl\n"
    else:
        # Identify dependency relations that are permitted in the current language.
        # If there are errors in documentation, identify the erroneous doc file.
        # Note that depreldata[lcode] may not exist even though we have a non-empty
        # set of relations, if lcode is 'ud'.
        if lcode in depreldata:
            for r in depreldata[lcode]:
                file = re.sub(r':', r'-', r)
                if file == 'aux':
                    file = 'aux_'
                for e in depreldata[lcode][r]['errors']:
                    msg += "ERROR in _%s/dep/%s.md: %s\n" % (lcode, file, e)
        sorted_documented_relations = sorted(deprelset)
        msg += "The following %d relations are currently permitted in language [%s]:\n" % (len(sorted_documented_relations), lcode)
        msg += ', '.join(sorted_documented_relations) + "\n"
        msg += "If a language needs a relation subtype that is not documented in the universal guidelines, the relation\n"
        msg += "must have a language-specific documentation page in a prescribed format.\n"
        msg += "See https://universaldependencies.org/contributing_language_specific.html for further guidelines.\n"
        msg += "Documented dependency relations can be specifically turned on/off for each language in which they are used.\n"
        msg += "See https://quest.ms.mff.cuni.cz/udvalidator/cgi-bin/unidep/langspec/specify_deprel.pl for details.\n"
        # Save the message in a global variable.
        # We will add it to the first error message about an unknown feature in the data.
    warn_on_undoc_deps = msg
    return deprelset

def load_mwe_set(filename):
    """
    Loads the list of permitted MWE tags and returns it as a set.
    """
    res = load_file(os.path.join(THISDIR, 'data', filename))
    return res

def get_alt_language(misc):
    """
    Takes the value of the MISC column for a token and checks it for the
    attribute Lang=xxx. If present, it is interpreted as the code of the
    language in which the current token is. This is uselful for code switching,
    if a phrase is in a language different from the main language of the
    document. The validator can then temporarily switch to a different set
    of language-specific tests.
    """
    misclist = misc.split('|')
    p = re.compile(r'Lang=(.+)')
    for attr in misclist:
        m = p.match(attr)
        if m:
            return m.group(1)
    return None

def warn(msg, error_type, testlevel=0, testid='some-test', lineno=True, nodelineno=0, nodeid=0):
    """
    Print the warning.
    If lineno is True, print the number of the line last read from input. Note
    that once we have read a sentence, this is the number of the empty line
    after the sentence, hence we probably do not want to print it.
    If we still have an error that pertains to an individual node, and we know
    the number of the line where the node appears, we can supply it via
    nodelineno. Nonzero nodelineno means that lineno value is ignored.
    If lineno is False, print the number and starting line of the current tree.
    """
    global curr_fname, curr_line, sentence_line, sentence_id, error_counter, tree_counter, args
    error_counter[error_type] = error_counter.get(error_type, 0)+1
    if not args.quiet:
        if args.max_err > 0 and error_counter[error_type] == args.max_err:
            print(('...suppressing further errors regarding ' + error_type), file=sys.stderr)
        elif args.max_err > 0 and error_counter[error_type] > args.max_err:
            pass # suppressed
        else:
            if len(args.input) > 1: # several files, should report which one
                if curr_fname=='-':
                    fn = '(in STDIN) '
                else:
                    fn = '(in '+os.path.basename(curr_fname)+') '
            else:
                fn = ''
            sent = ''
            node = ''
            # Global variable (last read sentence id): sentence_id
            # Originally we used a parameter sid but we probably do not need to override the global value.
            if sentence_id:
                sent = ' Sent ' + sentence_id
            if nodeid:
                node = ' Node ' + str(nodeid)
            if nodelineno:
                print("[%sLine %d%s%s]: [L%d %s %s] %s" % (fn, nodelineno, sent, node, testlevel, error_type, testid, msg), file=sys.stderr)
            elif lineno:
                print("[%sLine %d%s%s]: [L%d %s %s] %s" % (fn, curr_line, sent, node, testlevel, error_type, testid, msg), file=sys.stderr)
            else:
                print("[%sTree number %d on line %d%s%s]: [L%d %s %s] %s" % (fn, tree_counter, sentence_line, sent, node, testlevel, error_type, testid, msg), file=sys.stderr)


###### Tests applicable to a single row indpendently of the others

def validate_unicode_normalization(text):
    """
    Tests that letters composed of multiple Unicode characters (such as a base
    letter plus combining diacritics) conform to NFC normalization (canonical
    decomposition followed by canonical composition).
    """
    normalized_text = unicodedata.normalize('NFC', text)
    if text != normalized_text:
        # Find the first unmatched character and include it in the report.
        firsti = -1
        firstj = -1
        inpfirst = ''
        nfcfirst = ''
        tcols = text.split("\t")
        ncols = normalized_text.split("\t")
        for i in range(len(tcols)):
            for j in range(len(tcols[i])):
                if tcols[i][j] != ncols[i][j]:
                    firsti = i
                    firstj = j
                    inpfirst = unicodedata.name(tcols[i][j])
                    nfcfirst = unicodedata.name(ncols[i][j])
                    break
            if firsti >= 0:
                break
        testlevel = 1
        testclass = 'Unicode'
        testid = 'unicode-normalization'
        testmessage = "Unicode not normalized: %s.character[%d] is %s, should be %s." % (COLNAMES[firsti], firstj, inpfirst, nfcfirst)
        warn(testmessage, testclass, testlevel=testlevel, testid=testid)


##### Tests applicable to the whole sentence

def deps_list(cols):
    if DEPS >= len(cols):
        return # this has been already reported in trees()
    if cols[DEPS] == '_':
        deps = []
    else:
        deps = [hd.split(':',1) for hd in cols[DEPS].split('|')]
    if any(hd for hd in deps if len(hd) != 2):
        raise ValueError('malformed DEPS: %s' % cols[DEPS])
    return deps

def subset_to_words_and_empty_nodes(tree):
    """
    Only picks word and empty node lines, skips multiword token lines.
    """
    return [cols for cols in tree if is_word(cols) or is_empty_node(cols)]


# Ll ... lowercase Unicode letters
# Lm ... modifier Unicode letters (e.g., superscript h)
# Lo ... other Unicode letters (all caseless scripts, e.g., Arabic)
# M .... combining diacritical marks
# Underscore is allowed between letters but not at beginning, end, or next to another underscore.
edeprelpart_resrc = '[\p{Ll}\p{Lm}\p{Lo}\p{M}]+(_[\p{Ll}\p{Lm}\p{Lo}\p{M}]+)*';
# There must be always the universal part, consisting only of ASCII letters.
# There can be up to three additional, colon-separated parts: subtype, preposition and case.
# One of them, the preposition, may contain Unicode letters. We do not know which one it is
# (only if there are all four parts, we know it is the third one).
# ^[a-z]+(:[a-z]+)?(:[\p{Ll}\p{Lm}\p{Lo}\p{M}]+(_[\p{Ll}\p{Lm}\p{Lo}\p{M}]+)*)?(:[a-z]+)?$
edeprel_resrc = '^[a-z]+(:[a-z]+)?(:' + edeprelpart_resrc + ')?(:[a-z]+)?$'
edeprel_re = re.compile(edeprel_resrc, re.U)
mwecode_re = re.compile(r'^(\d+)(?::([a-zA-Z]+(?:\.[a-zA-Z]+)?))?$')
def validate_character_constraints(cols):
    """
    Checks general constraints on valid characters, e.g. that UPOS
    only contains [A-Z].
    """
    testlevel = 2
    if is_multiword_token(cols):
        return
    if UPOS >= len(cols):
        return # this has been already reported in trees()
    if not (re.match(r"^[A-Z]+$", cols[UPOS]) or (is_empty_node(cols) and cols[UPOS] == '_')):
        testclass = 'Morpho'
        testid = 'invalid-upos'
        testmessage = "Invalid UPOS value '%s'." % cols[UPOS]
        warn(testmessage, testclass, testlevel=testlevel, testid=testid)
    # MWE codes
    # If it is a MWE
    if cols[MWE] not in "*_":
        for mwe_code in cols[MWE].split(";"):
            if not mwecode_re.match(mwe_code):
                testclass = 'MWE'
                testid = 'invalid-mwe'
                testmessage = "Invalid MWE code '%s'." % mwe_code
                warn(testmessage, testclass, testlevel=testlevel, testid=testid)

    if not (re.match(r"^[a-z]+(:[a-z]+)?$", cols[DEPREL]) or (is_empty_node(cols) and cols[DEPREL] == '_')):
        testclass = 'Syntax'
        testid = 'invalid-deprel'
        testmessage = "Invalid DEPREL value '%s'." % cols[DEPREL]
        warn(testmessage, testclass, testlevel=testlevel, testid=testid)
    try:
        deps = deps_list(cols)
    except ValueError:
        testclass = 'Enhanced'
        testid = 'invalid-deps'
        testmessage = "Failed to parse DEPS: '%s'." % cols[DEPS]
        warn(testmessage, testclass, testlevel=testlevel, testid=testid)
        return
    if any(deprel for head, deprel in deps_list(cols)
        if not edeprel_re.match(deprel)):
            testclass = 'Enhanced'
            testid = 'invalid-edeprel'
            testmessage = "Invalid enhanced relation type: '%s'." % cols[DEPS]
            warn(testmessage, testclass, testlevel=testlevel, testid=testid)


def validate_upos(cols, tag_sets):
    if UPOS >= len(cols):
        return # this has been already reported in trees()
    if is_empty_node(cols) and cols[UPOS] == '_':
        return
    if tag_sets[UPOS] is not None and cols[UPOS] not in tag_sets[UPOS]:
        testlevel = 2
        testclass = 'Morpho'
        testid = 'unknown-upos'
        testmessage = "Unknown UPOS tag: '%s'." % cols[UPOS]
        warn(testmessage, testclass, testlevel=testlevel, testid=testid)


def validate_deprels(cols, tag_sets, args):
    global warn_on_undoc_deps
    global warn_on_undoc_edeps
    if DEPREL >= len(cols):
        return # this has been already reported in trees()
    # List of permited relations is language-specific.
    # The current token may be in a different language due to code switching.
    deprelset = tag_sets[DEPREL]
    ###!!! Unlike with features and auxiliaries, with deprels it is less clear
    ###!!! whether we actually want to switch the set of labels when the token
    ###!!! belongs to another language. If the set is changed at all, then it
    ###!!! should be a union of the main language and the token language.
    ###!!! Otherwise we risk that, e.g., we have allowed 'flat:name' for our
    ###!!! language, the maintainers of the other language have not allowed it,
    ###!!! and then we could not use it when the foreign language is active.
    ###!!! (This has actually happened in French GSD.)
    altlang = None
    #altlang = get_alt_language(cols[MISC])
    #if altlang:
    #    deprelset = get_depreldata_for_language(altlang)
    # Test only the universal part if testing at universal level.
    deprel = cols[DEPREL]
    deprel = lspec2ud(deprel)
    testlevel = 2
    if deprelset is not None and deprel not in deprelset:
        testclass = 'Syntax'
        testid = 'unknown-deprel'
        # If some relations were excluded because they are not documented,
        # tell the user when the first unknown relation is encountered in the data.
        # Then erase this (long) introductory message and do not repeat it with
        # other instances of unknown relations.
        testmessage = "Unknown DEPREL label: '%s'" % cols[DEPREL]
        if not altlang and len(warn_on_undoc_deps) > 0:
            testmessage += "\n\n" + warn_on_undoc_deps
            warn_on_undoc_deps = ''
        warn(testmessage, testclass, testlevel=testlevel, testid=testid)
    if DEPS >= len(cols):
        return # this has been already reported in trees()
    if tag_sets[DEPS] is not None and cols[DEPS] != '_':
        for head_deprel in cols[DEPS].split('|'):
            try:
                head,deprel=head_deprel.split(':', 1)
            except ValueError:
                testclass = 'Enhanced'
                testid = 'invalid-head-deprel' # but it would have probably triggered another error above
                testmessage = "Malformed head:deprel pair '%s'." % head_deprel
                warn(testmessage, testclass, testlevel=testlevel, testid=testid)
                continue
            
            deprel = lspec2ud(deprel)
            if deprel not in tag_sets[DEPS]:
                testclass = 'Enhanced'
                testid = 'unknown-edeprel'
                testmessage = "Unknown enhanced relation type '%s' in '%s'" % (deprel, head_deprel)
                if not altlang and len(warn_on_undoc_edeps) > 0:
                    testmessage += "\n\n" + warn_on_undoc_edeps
                    warn_on_undoc_edeps = ''
                warn(testmessage, testclass, testlevel=testlevel, testid=testid)


def validate_mwe(cols, tag_sets):
    if MWE >= len(cols):
        return # this has been already reported in trees()
    if cols[MWE] == DEFAULT_MWE:
        return
    else:
        if args.underspecified_mwes and cols[MWE] != DEFAULT_MWE:
            testlevel = 2
            testclass = 'MWE'
            testid = 'unknown-mwe'
            testmessage = "Unknown MWE tag, only _ (for blind version): '%s'." % cols[MWE]
            warn(testmessage, testclass, testlevel=testlevel, testid=testid)
    
    # Remove digit elements using a list comprehension
    mwe_tags = set([tag for tag in re.split(r"[:;]", cols[MWE]) if not tag.isdigit()])

    testlevel = 2
    # Level 3, remove NotMWE tag
    if args.level > 2:
        testlevel = 3
        tag_sets[MWE].discard("NotMWE")

    if mwe_tags and not mwe_tags <= tag_sets[MWE]:
            testclass = 'MWE'
            testid = 'unknown-mwe'
            testmessage = "Unknown MWE tag: '%s'." % cols[MWE]
            warn(testmessage, testclass, testlevel=testlevel, testid=testid)


def features_present():
    """
    In general, the annotation of morphological features is optional, although
    highly encouraged. However, if the treebank does have features, then certain
    features become required. This function is called when the first morphological
    feature is encountered. It remembers that from now on, missing features can
    be reported as errors. In addition, if any such errors have already been
    encountered, they will be reported now.
    """
    global curr_line
    global line_of_first_morpho_feature
    global delayed_feature_errors
    if not line_of_first_morpho_feature:
        line_of_first_morpho_feature = curr_line
        for testid in delayed_feature_errors:
            for occurrence in delayed_feature_errors[testid]['occurrences']:
                warn(delayed_feature_errors[testid]['message'], delayed_feature_errors[testid]['class'], testlevel=delayed_feature_errors[testid]['level'], testid=testid, nodeid=occurrence['nodeid'], nodelineno=occurrence['nodelineno'])


attr_val_re=re.compile('^([A-Z][A-Za-z0-9]*(?:\[[a-z0-9]+\])?)=(([A-Z0-9][A-Z0-9a-z]*)(,([A-Z0-9][A-Z0-9a-z]*))*)$',re.U)
val_re=re.compile('^[A-Z0-9][A-Za-z0-9]*',re.U)
def validate_features(cols, tag_sets, args):
    """
    Checks general constraints on feature-value format. On level 4 and higher,
    also checks that a feature-value pair is listed as approved. (Every pair
    must be allowed on level 2 because it could be defined as language-specific.
    To disallow non-universal features, test on level 4 with language 'ud'.)
    """
    global warn_on_undoc_feats
    global mwt_typo_span_end
    testclass = 'Morpho'
    if FEATS >= len(cols):
        return # this has been already reported in trees()
    feats = cols[FEATS]
    if feats == '_':
        return True
    features_present()
    # List of permited features is language-specific.
    # The current token may be in a different language due to code switching.
    lang = args.lang
    featset = tag_sets[FEATS]
    altlang = get_alt_language(cols[MISC])
    if altlang:
        lang = altlang
        featset = get_featdata_for_language(altlang)
    feat_list=feats.split('|')
    if [f.lower() for f in feat_list] != sorted(f.lower() for f in feat_list):
        testlevel = 2
        testid = 'unsorted-features'
        testmessage = "Morphological features must be sorted: '%s'." % feats
        warn(testmessage, testclass, testlevel=testlevel, testid=testid)
    attr_set = set() # I'll gather the set of features here to check later that none is repeated.
    for f in feat_list:
        match = attr_val_re.match(f)
        if match is None:
            testlevel = 2
            testid = 'invalid-feature'
            testmessage = "Spurious morphological feature: '%s'. Should be of the form Feature=Value and must start with [A-Z] and only contain [A-Za-z0-9]." % f
            warn(testmessage, testclass, testlevel=testlevel, testid=testid)
            attr_set.add(f) # to prevent misleading error "Repeated features are disallowed"
        else:
            # Check that the values are sorted as well
            attr = match.group(1)
            attr_set.add(attr)
            values = match.group(2).split(',')
            if len(values) != len(set(values)):
                testlevel = 2
                testid = 'repeated-feature-value'
                testmessage = "Repeated feature values are disallowed: '%s'" % feats
                warn(testmessage, testclass, testlevel=testlevel, testid=testid)
            if [v.lower() for v in values] != sorted(v.lower() for v in values):
                testlevel = 2
                testid = 'unsorted-feature-values'
                testmessage = "If a feature has multiple values, these must be sorted: '%s'" % f
                warn(testmessage, testclass, testlevel=testlevel, testid=testid)
            for v in values:
                if not val_re.match(v):
                    testlevel = 2
                    testid = 'invalid-feature-value'
                    testmessage = "Spurious value '%s' in '%s'. Must start with [A-Z0-9] and only contain [A-Za-z0-9]." % (v, f)
                    warn(testmessage, testclass, testlevel=testlevel, testid=testid)
                # Level 2 tests character properties and canonical order but not that the f-v pair is known.
                
    if len(attr_set) != len(feat_list):
        testlevel = 2
        testid = 'repeated-feature'
        testmessage = "Repeated features are disallowed: '%s'." % feats
        warn(testmessage, testclass, testlevel=testlevel, testid=testid)
    if mwt_typo_span_end and int(mwt_typo_span_end) <= int(cols[ID]):
        mwt_typo_span_end = None


def validate_token_empty_vals(cols):
    """
    Checks that a multi-word token has _ empty values in all fields except MISC and MWE.
    This is required by UD guidelines although it is not a problem in general,
    therefore a level 2 test.
    """
    global mwt_typo_span_end
    assert is_multiword_token(cols), 'internal error'
    for col_idx in range(LEMMA, MISC): # all columns except the first two (ID, FORM) and the two last ones (MISC, MWE)
        # Exception: The feature Typo=Yes may occur in FEATS of a multi-word token.
        if col_idx == FEATS and cols[col_idx] == 'Typo=Yes':
            # If a multi-word token has Typo=Yes, its component words must not have it.
            # We must remember the span of the MWT and check it in validate_features().
            m = interval_re.match(cols[ID])
            mwt_typo_span_end = m.group(2)
        elif cols[col_idx] != '_':
            testlevel = 2
            testclass = 'Format'
            testid = 'mwt-nonempty-field'
            testmessage = "A multi-word token line must have '_' in the column %s. Now: '%s'." % (COLNAMES[col_idx], cols[col_idx])
            warn(testmessage, testclass, testlevel=testlevel, testid=testid)
    
    if col_idx == MWE and cols[col_idx] != DEFAULT_MWE:
        testlevel = 2
        testclass = 'Format'
        testid = 'mwt-nonempty-field'
        testmessage = "A multi-word token line must have '%s' in the column %s. Now: '%s'." % (DEFAULT_MWE, COLNAMES[col_idx], cols[col_idx])
        warn(testmessage, testclass, testlevel=testlevel, testid=testid)


def validate_empty_node_empty_vals(cols):
    """
    Checks that an empty node has _ empty values in HEAD and DEPREL. This is
    required by UD guidelines but not necessarily by CoNLL-U, therefore
    a level 2 test.
    """
    assert is_empty_node(cols), 'internal error'
    for col_idx in (HEAD, DEPREL):
        if cols[col_idx]!= '_':
            testlevel = 2
            testclass = 'Format'
            testid = 'mwt-nonempty-field'
            testmessage = "An empty node must have '_' in the column %s. Now: '%s'." % (COLNAMES[col_idx], cols[col_idx])
            warn(testmessage, testclass, testlevel=testlevel, testid=testid)


def validate_cols(cols, tag_sets, args):
    """
    All tests that can run on a single line. Done as soon as the line is read,
    called from trees() if level>1.
    """
    if is_word(cols) or is_empty_node(cols):
        validate_character_constraints(cols) # level 2
        validate_upos(cols, tag_sets) # level 2
        validate_mwe(cols, tag_sets)  # level 2 et up
        validate_features(cols, tag_sets, args) # level 2 
    elif is_multiword_token(cols):
        validate_token_empty_vals(cols)
    # else do nothing; we have already reported wrong ID format at level 1
    if is_word(cols):
        validate_deprels(cols, tag_sets, args) # level 2 
    elif is_empty_node(cols):
        validate_empty_node_empty_vals(cols) # level 2
    # if args.level > 3:
    #     validate_whitespace(cols, tag_sets) # level 4 (it is language-specific; to disallow everywhere, use --lang ud)


whitespace_re = re.compile('.*\s', re.U)
whitespace2_re = re.compile('.*\s\s', re.U)
def validate_cols_level1(cols):
    """
    Tests that can run on a single line and pertain only to the CUPT file
    format, not to predefined sets of UD tags.
    """
    testlevel = 1
    testclass = 'Format'
    # Some whitespace may be permitted in FORM, LEMMA and MISC but not elsewhere.
    for col_idx in range(MWE+1):
        if col_idx >= len(cols):
            break # this has been already reported in trees()
        # Must never be empty
        if not cols[col_idx]:
            testid = 'empty-column'
            testmessage = 'Empty value in column %s.' % (COLNAMES[col_idx])
            warn(testmessage, testclass, testlevel=testlevel, testid=testid)
        else:
            # Must never have leading/trailing whitespace
            if cols[col_idx][0].isspace():
                testid = 'leading-whitespace'
                testmessage = 'Leading whitespace not allowed in column %s.' % (COLNAMES[col_idx])
                warn(testmessage, testclass, testlevel=testlevel, testid=testid)
            if cols[col_idx][-1].isspace():
                testid = 'trailing-whitespace'
                testmessage = 'Trailing whitespace not allowed in column %s.' % (COLNAMES[col_idx])
                warn(testmessage, testclass, testlevel=testlevel, testid=testid)
            # Must never contain two consecutive whitespace characters
            if whitespace2_re.match(cols[col_idx]):
                testid = 'repeated-whitespace'
                testmessage = 'Two or more consecutive whitespace characters not allowed in column %s.' % (COLNAMES[col_idx])
                warn(testmessage, testclass, testlevel=testlevel, testid=testid)
    # Multi-word tokens may have whitespaces in MISC but not in FORM or LEMMA.
    # If it contains a space, it does not make sense to treat it as a MWT.
    if is_multiword_token(cols):
        for col_idx in (FORM, LEMMA):
            if col_idx >= len(cols):
                break # this has been already reported in trees()
            if whitespace_re.match(cols[col_idx]):
                testid = 'invalid-whitespace-mwt'
                testmessage = "White space not allowed in multi-word token '%s'. If it contains a space, it is not one surface token." % (cols[col_idx])
                warn(testmessage, testclass, testlevel=testlevel, testid=testid)
    # These columns must not have whitespace.
    for col_idx in (ID, UPOS, XPOS, FEATS, HEAD, DEPREL, DEPS, MWE):
        if col_idx >= len(cols):
            break # this has been already reported in trees()
        if whitespace_re.match(cols[col_idx]):
            testid = 'invalid-whitespace'
            testmessage = "White space not allowed in column %s: '%s'." % (COLNAMES[col_idx], cols[col_idx])
            warn(testmessage, testclass, testlevel=testlevel, testid=testid)
    # Check for the format of the ID value. (ID must not be empty.)
    if not (is_word(cols) or is_empty_node(cols) or is_multiword_token(cols)):
        testid = 'invalid-word-id'
        testmessage = "Unexpected ID format '%s'." % cols[ID]
        warn(testmessage, testclass, testlevel=testlevel, testid=testid)


##### Tests applicable to the whole tree

interval_re = re.compile('^([0-9]+)-([0-9]+)$', re.U)
def validate_ID_sequence(tree):
    """
    Validates that the ID sequence is correctly formed.
    Besides issuing a warning if an error is found, it also returns False to
    the caller so it can avoid building a tree from corrupt ids.
    """
    ok = True
    testlevel = 1
    testclass = 'Format'
    words=[]
    tokens=[]
    current_word_id, next_empty_id = 0, 1
    for cols in tree:
        if not is_empty_node(cols):
            next_empty_id = 1    # reset sequence
        if is_word(cols):
            t_id = int(cols[ID])
            current_word_id = t_id
            words.append(t_id)
            # Not covered by the previous interval?
            if not (tokens and tokens[-1][0] <= t_id and tokens[-1][1] >= t_id):
                tokens.append((t_id, t_id)) # nope - let's make a default interval for it
        elif is_multiword_token(cols):
            match = interval_re.match(cols[ID]) # Check the interval against the regex
            if not match: # This should not happen. The function is_multiword_token() would then not return True.
                testid = 'invalid-word-interval'
                testmessage = "Spurious word interval definition: '%s'." % cols[ID]
                warn(testmessage, testclass, testlevel=testlevel, testid=testid)
                ok = False
                continue
            beg, end = int(match.group(1)), int(match.group(2))
            if not ((not words and beg >= 1) or (words and beg >= words[-1] + 1)):
                testid = 'misplaced-word-interval'
                testmessage = 'Multiword range not before its first word.'
                warn(testmessage, testclass, testlevel=testlevel, testid=testid)
                ok = False
                continue
            tokens.append((beg, end))
        elif is_empty_node(cols):
            word_id, empty_id = (int(i) for i in parse_empty_node_id(cols))
            if word_id != current_word_id or empty_id != next_empty_id:
                testid = 'misplaced-empty-node'
                testmessage = 'Empty node id %s, expected %d.%d' % (cols[ID], current_word_id, next_empty_id)
                warn(testmessage, testclass, testlevel=testlevel, testid=testid)
                ok = False
            next_empty_id += 1
            # Interaction of multiword tokens and empty nodes if there is an empty
            # node between the first word of a multiword token and the previous word:
            # This sequence is correct: 4 4.1 5-6 5 6
            # This sequence is wrong:   4 5-6 4.1 5 6
            if word_id == current_word_id and tokens and word_id < tokens[-1][0]:
                testid = 'misplaced-empty-node'
                testmessage = "Empty node id %s must occur before multiword token %s-%s." % (cols[ID], tokens[-1][0], tokens[-1][1])
                warn(testmessage, testclass, testlevel=testlevel, testid=testid)
                ok = False
    # Now let's do some basic sanity checks on the sequences.
    # Expected sequence of word IDs is 1, 2, ...
    expstrseq = ','.join(str(x) for x in range(1, len(words) + 1))
    wrdstrseq = ','.join(str(x) for x in words)
    if wrdstrseq != expstrseq:
        testid = 'word-id-sequence'
        testmessage = "Words do not form a sequence. Got '%s'. Expected '%s'." % (wrdstrseq, expstrseq)
        warn(testmessage, testclass, testlevel=testlevel, testid=testid, lineno=False)
        ok = False
    # Check elementary sanity of word intervals.
    # Remember that these are not just multi-word tokens. Here we have intervals even for single-word tokens (b=e)!
    for (b, e) in tokens:
        if e<b: # end before beginning
            testid = 'reversed-word-interval'
            testmessage = 'Spurious token interval %d-%d' % (b,e)
            warn(testmessage, testclass, testlevel=testlevel, testid=testid)
            ok = False
            continue
        if b<1 or e>len(words): # out of range
            testid = 'word-interval-out'
            testmessage = 'Spurious token interval %d-%d (out of range)' % (b,e)
            warn(testmessage, testclass, testlevel=testlevel, testid=testid)
            ok = False
            continue
    return ok


def validate_token_ranges(tree):
    """
    Checks that the word ranges for multiword tokens are valid.
    """
    testlevel = 1
    testclass = 'Format'
    covered = set()
    for cols in tree:
        if not is_multiword_token(cols):
            continue
        m = interval_re.match(cols[ID])
        if not m: # This should not happen. The function is_multiword_token() would then not return True.
            testid = 'invalid-word-interval'
            testmessage = "Spurious word interval definition: '%s'." % cols[ID]
            warn(testmessage, testclass, testlevel=testlevel, testid=testid)
            continue
        start, end = m.groups()
        try:
            start, end = int(start), int(end)
        except ValueError:
            assert False, 'internal error' # RE should assure that this works
        if not start < end: ###!!! This was already tested above in validate_ID_sequence()! Should we remove it from there?
            testid = 'reversed-word-interval'
            testmessage = 'Spurious token interval %d-%d' % (start, end)
            warn(testmessage, testclass, testlevel=testlevel, testid=testid)
            continue
        if covered & set(range(start, end+1)):
            testid = 'overlapping-word-intervals'
            testmessage = 'Range overlaps with others: %s' % cols[ID]
            warn(testmessage, testclass, testlevel=testlevel, testid=testid)
        covered |= set(range(start, end+1))


def validate_newlines(inp):
    if inp.newlines and inp.newlines != '\n':
        testlevel = 1
        testclass = 'Format'
        testid = 'non-unix-newline'
        testmessage = 'Only the unix-style LF line terminator is allowed.'
        warn(testmessage, testclass, testlevel=testlevel, testid=testid)


#==============================================================================
# Level 1 tests. Only CUPT backbone. Values can be empty or non-UD.
#==============================================================================
# regular expression of source_sent_id metadata
sentid_re=re.compile('^# source_sent_id\s*=\s*(\S+)\s+(\S+)\s+(\S+)$')
def trees(inp, tag_sets, args):
    """
    `inp` a file-like object yielding lines as unicode
    `tag_sets` and `args` are needed for choosing the tests

    This function does elementary checking of the input and yields one
    sentence at a time from the input stream.

    This function is a generator. The caller can call it in a 'for x in ...'
    loop. In each iteration of the caller's loop, the generator will generate
    the next sentence, that is, it will read the next sentence from the input
    stream. (Technically, the function returns an object, and the object will
    then read the sentences within the caller's loop.)
    """
    global curr_line, comment_start_line, sentence_line, sentence_id
    comments = [] # List of comment lines to go with the current sentence
    lines = [] # List of token/word lines of the current sentence
    corrupted = False # In case of wrong number of columns check the remaining lines of the sentence but do not yield the sentence for further processing.
    comment_start_line = None
    testlevel = 1
    testclass = 'Format'
    # Loop over all lines in the files
    for line_counter, line in enumerate(inp):
        # current line number
        curr_line = line_counter+1
        
        if not comment_start_line:
            comment_start_line = curr_line
        # remove the Unicode newline character (\n) from the end of the string. 
        line = line.rstrip(u"\n")

        # First line
        if curr_line == 1:
            colnames = line.split("=")[-1].strip().split()
            if not "global.columns =" in line:
                testid = 'invalid-first-line'
                testmessage = "Spurious first line: '%s'. First line must specify global.columns" % (line)
                warn(testmessage, testclass, testlevel=testlevel, testid=testid)
            
            try:
                parseme_colname = colnames.index("PARSEME:MWE")
            except ValueError:
                testid = 'missing-mwe-column'
                testmessage = "Spurious first line: '%s'. First line must specify column PARSEME:MWE" % (line)
                warn(testmessage, testclass, testlevel=testlevel, testid=testid)

        # If the entire line consists of only whitespace characters. 
        if is_whitespace(line):
            testid = 'pseudo-empty-line'
            testmessage = 'Spurious line that appears empty but is not; there are whitespace characters.'
            warn(testmessage, testclass, testlevel=testlevel, testid=testid)
            # We will pretend that the line terminates a sentence in order to avoid subsequent misleading error messages.
            if lines:
                if not corrupted:
                    yield comments, lines
                comments = []
                lines = []
                corrupted = False
                comment_start_line = None
        # empty line
        elif not line: 
            if lines: # sentence done
                if not corrupted:
                    yield comments, lines
                comments=[]
                lines=[]
                corrupted = False
                comment_start_line = None
            else:
                testid = 'extra-empty-line'
                testmessage = 'Spurious empty line. Only one empty line is expected after every sentence.'
                warn(testmessage, testclass, testlevel=testlevel, testid=testid)
        # comment lines
        elif line[0]=='#':
            # We will really validate sentence ids later. But now we want to remember
            # everything that looks like a sentence id and use it in the error messages.
            # Line numbers themselves may not be sufficient if we are reading multiple
            # files from a pipe.
            match = sentid_re.match(line)
            if match:
                sentence_id = match.group(3)
            if not lines: # before sentence
                comments.append(line)
            else:
                testid = 'misplaced-comment'
                testmessage = 'Spurious comment line. Comments are only allowed before a sentence.'
                warn(testmessage, testclass, testlevel=testlevel, testid=testid)
        # Tokenization lines
        elif line[0].isdigit():
            validate_unicode_normalization(line)
            if not lines: # new sentence
                sentence_line=curr_line
            cols=line.split(u"\t")
            # print("cols: ", cols)
            # exit(0)
            if len(cols)!=COLCOUNT:
                testid = 'number-of-columns'
                testmessage = 'The line has %d columns but %d are expected. The contents of the columns will not be checked.' % (len(cols), COLCOUNT)
                warn(testmessage, testclass, testlevel=testlevel, testid=testid)
                corrupted = True
            # If there is an unexpected number of columns, do not test their contents.
            # Maybe the contents belongs to a different column. And we could see
            # an exception if a column value is missing.
            else:
                lines.append(cols)
                # pertain to the CoNLL-U file format
                validate_cols_level1(cols)
                if args.level > 1:
                    validate_cols(cols, tag_sets, args)
        else: # A line which is neither a comment nor a token/word, nor empty. That's bad!
            testid = 'invalid-line'
            testmessage = "Spurious line: '%s'. All non-empty lines should start with a digit or the # character." % (line)
            warn(testmessage, testclass, testlevel=testlevel, testid=testid)
    else: # end of file
        if comments or lines: # These should have been yielded on an empty line!
            testid = 'missing-empty-line'
            testmessage = 'Missing empty line after the last sentence.'
            warn(testmessage, testclass, testlevel=testlevel, testid=testid)
            if not corrupted:
                yield comments, lines


#==============================================================================
# Level 2 tests. Tree structure, universal tags and deprels. Note that any
# well-formed Feature=Valid pair is allowed (because it could be language-
# specific) and any word form or lemma can contain spaces (because language-
# specific guidelines may permit it).
#==============================================================================

###### Metadata tests #########

def validate_source_sent_id(comments, known_ids, lcode):
    testlevel = 2
    testclass = 'Metadata'
    matched=[]
    for c in comments:
        match=sentid_re.match(c)
        if match:
            matched.append(match)
        else:
            if c.startswith('# source_sent_id') or c.startswith('#source_sent_id'):
                testid = 'invalid-source-sent-id'
                testmessage = "Spurious source_sent_id line: '%s' Should look like '# source_sent_id = uri path id'. Forward slash reserved for special purposes." % c
                warn(testmessage, testclass, testlevel=testlevel, testid=testid)
    if not matched:
        testid = 'missing-source-sent-id'
        testmessage = 'Missing the source_sent_id attribute.'
        warn(testmessage, testclass, testlevel=testlevel, testid=testid)
    elif len(matched)>1:
        testid = 'multiple-source-sent-id'
        testmessage = 'Multiple source_sent_id attributes.'
        warn(testmessage, testclass, testlevel=testlevel, testid=testid)
    else:
        # Uniqueness of sentence ids should be tested treebank-wide, not just file-wide.
        # For that to happen, all three files should be tested at once.
        sid=matched[0].group(3)
        if sid in known_ids:
            testid = 'non-unique-sent-id'
            testmessage = "Non-unique id attribute '%s'." % sid
            warn(testmessage, testclass, testlevel=testlevel, testid=testid)

        if sid.count(u"/")>1 or (sid.count(u"/")==1 and lcode!=u"ud" and lcode!=u"shopen"):
            testid = 'slash-in-sent-id'
            testmessage = "The forward slash is reserved for special use in parallel treebanks: '%s'" % sid
            warn(testmessage, testclass, testlevel=testlevel, testid=testid)
        known_ids.add(sid)


newdoc_re = re.compile('^#\s*newdoc(\s|$)')
newpar_re = re.compile('^#\s*newpar(\s|$)')
text_re = re.compile('^#\s*text\s*=\s*(.+)$')
metadata_re = re.compile('^#\s*metadata\s*=\s*')
def validate_text_meta(comments, tree):
    # In trees(), sentence_line was already moved to the first token/node line
    # after the sentence comment lines. While this is useful in most validation
    # functions, it complicates things here where we also work with the comments.
    global sentence_line
    testlevel = 2
    testclass = 'Metadata'
    newdoc_matched = []
    newpar_matched = []
    text_matched = []
    for c in comments:
        newdoc_match = newdoc_re.match(c)
        if newdoc_match:
            newdoc_matched.append(newdoc_match)
        newpar_match = newpar_re.match(c)
        if newpar_match:
            newpar_matched.append(newpar_match)
        text_match = text_re.match(c)
        if text_match:
            text_matched.append(text_match)
        
        if args.level > 2:
            testlevel = 3
            if metadata_re.match(c):
                testid = 'forbidden-metadata'
                testmessage = "The metadata field is forbidden in metadata comments: %s" % c
                warn(testmessage, testclass, testlevel=testlevel, testid=testid)

    if len(newdoc_matched) > 1:
        testid = 'multiple-newdoc'
        testmessage = 'Multiple newdoc attributes.'
        warn(testmessage, testclass, testlevel=testlevel, testid=testid)
    if len(newpar_matched) > 1:
        testid = 'multiple-newpar'
        testmessage = 'Multiple newpar attributes.'
        warn(testmessage, testclass, testlevel=testlevel, testid=testid)
    if not text_matched:
        testid = 'missing-text'
        testmessage = 'Missing the text attribute.'
        warn(testmessage, testclass, testlevel=testlevel, testid=testid)
    elif len(text_matched) > 1:
        testid = 'multiple-text'
        testmessage = 'Multiple text attributes.'
        warn(testmessage, testclass, testlevel=testlevel, testid=testid)
    else:
        stext = text_matched[0].group(1)
        if stext[-1].isspace():
            testid = 'text-trailing-whitespace'
            testmessage = 'The text attribute must not end with whitespace.'
            warn(testmessage, testclass, testlevel=testlevel, testid=testid)


def validate_root(tree):
    """
    Checks that DEPREL is "root" iff HEAD is 0.
    """
    testlevel = 2
    for cols in tree:
        if is_word(cols):
            if HEAD >= len(cols):
                continue # this has been already reported in trees()
            if cols[HEAD] == '0' and lspec2ud(cols[DEPREL]) != 'root':
                testclass = 'Syntax'
                testid = '0-is-not-root'
                testmessage = "DEPREL must be 'root' if HEAD is 0."
                warn(testmessage, testclass, testlevel=testlevel, testid=testid)
            if cols[HEAD] != '0' and lspec2ud(cols[DEPREL]) == 'root':
                testclass = 'Syntax'
                testid = 'root-is-not-0'
                testmessage = "DEPREL cannot be 'root' if HEAD is not 0."
                warn(testmessage, testclass, testlevel=testlevel, testid=testid)
        if is_word(cols) or is_empty_node(cols):
            if DEPS >= len(cols):
                continue # this has been already reported in trees()
            try:
                deps = deps_list(cols)
            except ValueError:
                # Similar errors have probably been reported earlier.
                testclass = 'Format'
                testid = 'invalid-deps'
                testmessage = "Failed to parse DEPS: '%s'." % cols[DEPS]
                warn(testmessage, testclass, testlevel=testlevel, testid=testid)
                continue
            for head, deprel in deps:
                if head == '0' and lspec2ud(deprel) != 'root':
                    testclass = 'Enhanced'
                    testid = 'enhanced-0-is-not-root'
                    testmessage = "Enhanced relation type must be 'root' if head is 0."
                    warn(testmessage, testclass, testlevel=testlevel, testid=testid)
                if head != '0' and lspec2ud(deprel) == 'root':
                    testclass = 'Enhanced'
                    testid = 'enhanced-root-is-not-0'
                    testmessage = "Enhanced relation type cannot be 'root' if head is not 0."
                    warn(testmessage, testclass, testlevel=testlevel, testid=testid)


basic_head_re = re.compile('^(0|[1-9][0-9]*)$', re.U)
enhanced_head_re = re.compile('^(0|[1-9][0-9]*)(\.[1-9][0-9]*)?$', re.U)
def validate_ID_references(tree):
    """
    Validates that HEAD and DEPS reference existing IDs.
    """
    testlevel = 2
    word_tree = subset_to_words_and_empty_nodes(tree)
    ids = set([cols[ID] for cols in word_tree])
    for cols in word_tree:
        if HEAD >= len(cols):
            return # this has been already reported in trees()
        # Test the basic HEAD only for non-empty nodes.
        # We have checked elsewhere that it is empty for empty nodes.
        if not is_empty_node(cols):
            match = basic_head_re.match(cols[HEAD])
            if match is None:
                testclass = 'Format'
                testid = 'invalid-head'
                testmessage = "Invalid HEAD: '%s'." % cols[HEAD]
                warn(testmessage, testclass, testlevel=testlevel, testid=testid)
            if not (cols[HEAD] in ids or cols[HEAD] == '0'):
                testclass = 'Syntax'
                testid = 'unknown-head'
                testmessage = "Undefined HEAD (no such ID): '%s'." % cols[HEAD]
                warn(testmessage, testclass, testlevel=testlevel, testid=testid)
        if DEPS >= len(cols):
            return # this has been already reported in trees()
        try:
            deps = deps_list(cols)
        except ValueError:
            # Similar errors have probably been reported earlier.
            testclass = 'Format'
            testid = 'invalid-deps'
            testmessage = "Failed to parse DEPS: '%s'." % cols[DEPS]
            warn(testmessage, testclass, testlevel=testlevel, testid=testid)
            continue
        for head, deprel in deps:
            match = enhanced_head_re.match(head)
            if match is None:
                testclass = 'Format'
                testid = 'invalid-ehead'
                testmessage = "Invalid enhanced head reference: '%s'." % head
                warn(testmessage, testclass, testlevel=testlevel, testid=testid)
            if not (head in ids or head == '0'):
                testclass = 'Enhanced'
                testid = 'unknown-ehead'
                testmessage = "Undefined enhanced head reference (no such ID): '%s'." % head
                warn(testmessage, testclass, testlevel=testlevel, testid=testid)


def validate_deps(tree):
    """
    Validates that DEPS is correctly formatted and that there are no
    self-loops in DEPS.
    """
    global line_of_first_enhancement
    testlevel = 2
    node_line = sentence_line - 1
    for cols in tree:
        node_line += 1
        if not (is_word(cols) or is_empty_node(cols)):
            continue
        if DEPS >= len(cols):
            continue # this has been already reported in trees()
        # Remember whether there is at least one difference between the basic
        # tree and the enhanced graph in the entire dataset.
        if cols[DEPS] != '_' and cols[DEPS] != cols[HEAD]+':'+cols[DEPREL]:
            line_of_first_enhancement = node_line
        try:
            deps = deps_list(cols)
            heads = [float(h) for h, d in deps]
        except ValueError:
            # Similar errors have probably been reported earlier.
            testclass = 'Format'
            testid = 'invalid-deps'
            testmessage = "Failed to parse DEPS: '%s'." % cols[DEPS]
            warn(testmessage, testclass, testlevel=testlevel, testid=testid, nodelineno=node_line)
            return
        if heads != sorted(heads):
            testclass = 'Format'
            testid = 'unsorted-deps'
            testmessage = "DEPS not sorted by head index: '%s'" % cols[DEPS]
            warn(testmessage, testclass, testlevel=testlevel, testid=testid, nodelineno=node_line)
        else:
            lasth = None
            lastd = None
            for h, d in deps:
                if h == lasth:
                    if d < lastd:
                        testclass = 'Format'
                        testid = 'unsorted-deps-2'
                        testmessage = "DEPS pointing to head '%s' not sorted by relation type: '%s'" % (h, cols[DEPS])
                        warn(testmessage, testclass, testlevel=testlevel, testid=testid, nodelineno=node_line)
                    elif d == lastd:
                        testclass = 'Format'
                        testid = 'repeated-deps'
                        testmessage = "DEPS contain multiple instances of the same relation '%s:%s'" % (h, d)
                        warn(testmessage, testclass, testlevel=testlevel, testid=testid, nodelineno=node_line)
                lasth = h
                lastd = d
                ###!!! This is now also tested above in validate_root(). We must reorganize testing of the enhanced structure so that the same thing is not tested multiple times.
                # Like in the basic representation, head 0 implies relation root and vice versa.
                # Note that the enhanced graph may have multiple roots (coordination of predicates).
                #ud = lspec2ud(d)
                #if h == '0' and ud != 'root':
                #    warn("Illegal relation '%s:%s' in DEPS: must be 'root' if head is 0" % (h, d), 'Format', nodelineno=node_line)
                #if ud == 'root' and h != '0':
                #    warn("Illegal relation '%s:%s' in DEPS: cannot be 'root' if head is not 0" % (h, d), 'Format', nodelineno=node_line)
        try:
            id_ = float(cols[ID])
        except ValueError:
            # This error has been reported previously.
            return
        if id_ in heads:
            testclass = 'Enhanced'
            testid = 'deps-self-loop'
            testmessage = "Self-loop in DEPS for '%s'" % cols[ID]
            warn(testmessage, testclass, testlevel=testlevel, testid=testid, nodelineno=node_line)


def validate_misc(tree):
    """
    In general, the MISC column can contain almost anything. However, if there
    is a vertical bar character, it is interpreted as the separator of two
    MISC attributes, which may or may not have the form of attribute=value pair.
    In general it is not forbidden that the same attribute appears several times
    with different values, but this should not happen for selected attributes
    that are described in the UD documentation.
    """
    testlevel = 2
    node_line = sentence_line - 1
    for cols in tree:
        node_line += 1
        if not (is_word(cols) or is_empty_node(cols)):
            continue
        if MISC >= len(cols):
            continue # this has been already reported in trees()
        if cols[MISC] == '_':
            continue
        misc = [ma.split('=', 1) for ma in cols[MISC].split('|')]
        mamap = {}
        for ma in misc:
            if len(ma) == 1 and ma[0] == '':
                testclass = 'Warning' # warning only
                testid = 'empty-misc'
                testmessage = "Empty attribute in MISC; possible misinterpreted vertical bar?"
                warn(testmessage, testclass, testlevel=testlevel, testid=testid, nodelineno=node_line)
            elif ma[0] == '':
                testclass = 'Warning' # warning only
                testid = 'empty-misc-key'
                testmessage = "Empty MISC attribute name in '%s=%s'." % (ma[0], ma[1])
                warn(testmessage, testclass, testlevel=testlevel, testid=testid, nodelineno=node_line)
            elif re.match(r'^\s', ma[0]):
                testclass = 'Warning' # warning only
                testid = 'misc-extra-space'
                testmessage = "MISC attribute name starts with space in '%s=%s'." % (ma[0], ma[1])
                warn(testmessage, testclass, testlevel=testlevel, testid=testid, nodelineno=node_line)
            elif re.search(r'\s$', ma[0]):
                testclass = 'Warning' # warning only
                testid = 'misc-extra-space'
                testmessage = "MISC attribute name ends with space in '%s=%s'." % (ma[0], ma[1])
                warn(testmessage, testclass, testlevel=testlevel, testid=testid, nodelineno=node_line)
            elif len(ma) > 1 and re.match(r'^\s', ma[1]):
                testclass = 'Warning' # warning only
                testid = 'misc-extra-space'
                testmessage = "MISC attribute value starts with space in '%s=%s'." % (ma[0], ma[1])
                warn(testmessage, testclass, testlevel=testlevel, testid=testid, nodelineno=node_line)
            elif len(ma) > 1 and re.search(r'\s$', ma[1]):
                testclass = 'Warning' # warning only
                testid = 'misc-extra-space'
                testmessage = "MISC attribute value ends with space in '%s=%s'." % (ma[0], ma[1])
                warn(testmessage, testclass, testlevel=testlevel, testid=testid, nodelineno=node_line)
            if re.match(r'^(SpaceAfter|Lang|Translit|LTranslit|Gloss|LId|LDeriv)$', ma[0]):
                mamap.setdefault(ma[0], 0)
                mamap[ma[0]] = mamap[ma[0]] + 1
            elif re.match(r'^\s*(spaceafter|lang|translit|ltranslit|gloss|lid|lderiv)\s*$', ma[0], re.IGNORECASE):
                testclass = 'Warning' # warning only
                testid = 'misc-attr-typo'
                testmessage = "Possible typo (case or spaces) in MISC attribute '%s=%s'." % (ma[0], ma[1])
                warn(testmessage, testclass, testlevel=testlevel, testid=testid, nodelineno=node_line)
        for a in list(mamap):
            if mamap[a] > 1:
                testclass = 'Format' # this one is real error
                testid = 'repeated-misc'
                testmessage = "MISC attribute '%s' not supposed to occur twice" % a
                warn(testmessage, testclass, testlevel=testlevel, testid=testid, nodelineno=node_line)


def validate_mwe_sequence(tree: list):
    """Validates that the MWE sequence is correctly formed.

    Args:
        tree (list): Tokenization of a sentence

    Returns:
        None
    """
    testlevel = 2
    testclass = 'MWE'
    mweid2categ = {}
    node_line = sentence_line - 1
    number_tokens = 0

    # Loop over all lines in the tokenization of a sentence
    for cols in tree:
        node_line += 1
        if is_word(cols) or is_empty_node(cols) or is_multiword_token(cols):
            number_tokens += 1
            # If it is a MWE
            if cols[MWE] not in "*_":
                for word_mwe in cols[MWE].split(";"):
                    try:
                        mweid = int(word_mwe)
                    except ValueError:
                        try:
                            mweid, mwecateg = word_mwe.split(':')
                            mweid = int(mweid)
                        except ValueError:
                            testid = 'invalid-mwe-code'
                            testmessage = 'Invalid MWE code %s (expecting an integer like \'3\' a pair like \'3:LVC.full\')' % (cols[MWE])
                            warn(testmessage, testclass, testlevel=testlevel, testid=testid, nodelineno=node_line)
                        else:
                            if mweid in mweid2categ:
                                testid = 'redefined-mwe-code'
                                testmessage = 'MWE code was redefined (\'%d:%s\' => \'%d:%s\')' % (mweid, mweid2categ[mweid], mweid, mwecateg)
                                warn(testmessage, testclass, testlevel=testlevel, testid=testid, nodelineno=node_line)

                            mweid2categ[mweid] = mwecateg
                    else:
                        if mweid not in mweid2categ:
                            testid = 'mwe-code-without-category'
                            testmessage = 'MWE code %d without giving it a category right away' % (mweid)
                            warn(testmessage, testclass, testlevel=testlevel, testid=testid, nodelineno=node_line)

    # If the sentence has a MWE
    if len(mweid2categ) > 0:
        expstrseq = ','.join(str(x) for x in range(1, len(mweid2categ) + 1))
        wrdstrseq = ','.join(str(x) for x in sorted(mweid2categ.keys()))
        if wrdstrseq != expstrseq:
            testid = 'mwe-sequence'
            testmessage = "MWE keys do not form a sequence. Got '%s'. Expected '%s'." % (wrdstrseq, expstrseq)
            warn(testmessage, testclass, testlevel=testlevel, testid=testid, lineno=False)     

        if max(mweid2categ.keys()) > number_tokens: # out of range
            testid = 'mwe-interval-out'
            testmessage = 'Spurious mwe interval 1-%d (out of range)' % (max(mweid2categ.keys()))
            warn(testmessage, testclass, testlevel=testlevel, testid=testid)
        

def get_projection(id, tree, projection):
    """
    Like proj() above, but works with the tree data structure. Collects node ids
    in the set called projection.
    """
    nodes = list((id,))
    while nodes:
        id = nodes.pop()
        for child in tree['children'][id]:
            if child in projection:
                continue; # skip cycles
            projection.add(child)
            nodes.append(child)
    return projection


def build_tree(sentence):
    """
    Takes the list of non-comment lines (line = list of columns) describing
    a sentence. Returns a dictionary with items providing easier access to the
    tree structure. In case of fatal problems (missing HEAD etc.) returns None
    but does not report the error (presumably it has already been reported).

    tree ... dictionary:
      nodes ... array of word lines, i.e., lists of columns;
          mwt and empty nodes are skipped, indices equal to ids (nodes[0] is empty)
      children ... array of sets of children indices (numbers, not strings);
          indices to this array equal to ids (children[0] are the children of the root)
      linenos ... array of line numbers in the file, corresponding to nodes
          (needed in error messages)
    """
    testlevel = 2
    testclass = 'Syntax'
    global sentence_line # the line of the first token/word of the current tree (skipping comments!)
    node_line = sentence_line - 1
    children = {} # node -> set of children
    tree = {
        'nodes':    [['0', '_', '_', '_', '_', '_', '_', '_', '_', '_']], # add artificial node 0
        'children': [],
        'linenos':  [sentence_line] # for node 0
    }
    for cols in sentence:
        node_line += 1
        if not is_word(cols):
            continue
        # Even MISC may be needed when checking the annotation guidelines
        # (for instance, SpaceAfter=No must not occur inside a goeswith span).
        if MISC >= len(cols):
            # This error has been reported on lower levels, do not report it here.
            # Do not continue to check annotation if there are elementary flaws.
            return None
        try:
            id_ = int(cols[ID])
        except ValueError:
            # This error has been reported on lower levels, do not report it here.
            # Do not continue to check annotation if there are elementary flaws.
            return None
        try:
            head = int(cols[HEAD])
        except ValueError:
            # This error has been reported on lower levels, do not report it here.
            # Do not continue to check annotation if there are elementary flaws.
            return None
        if head == id_:
            testid = 'head-self-loop'
            testmessage = 'HEAD == ID for %s' % cols[ID]
            warn(testmessage, testclass, testlevel=testlevel, testid=testid, nodelineno=node_line)
            return None
        tree['nodes'].append(cols)
        tree['linenos'].append(node_line)
        # Incrementally build the set of children of every node.
        children.setdefault(cols[HEAD], set()).add(id_)
    for cols in tree['nodes']:
        tree['children'].append(sorted(children.get(cols[ID], [])))
    # Check that there is just one node with the root relation.
    if len(tree['children'][0]) > 1:
        testid = 'multiple-roots'
        testmessage = "Multiple root words: %s" % tree['children'][0]
        warn(testmessage, testclass, testlevel=testlevel, testid=testid, lineno=False)
        return None
    # Return None if there are any cycles. Avoid surprises when working with the graph.
    # Presence of cycles is equivalent to presence of unreachable nodes.
    projection = set()
    get_projection(0, tree, projection)
    unreachable = set(range(1, len(tree['nodes']) - 1)) - projection
    if unreachable:
        testid = 'non-tree'
        testmessage = 'Non-tree structure. Words %s are not reachable from the root 0.' % (','.join(str(w) for w in sorted(unreachable)))
        warn(testmessage, testclass, testlevel=testlevel, testid=testid, lineno=False)
        return None
    return tree


def get_graph_projection(id, graph, projection):
    """
    Like get_projection() above, but works with the enhanced graph data structure.
    Collects node ids in the set called projection.
    """
    nodes = list((id,))
    while nodes:
        id = nodes.pop()
        for child in graph[id]['children']:
            if child in projection:
                continue; # skip cycles
            projection.add(child)
            nodes.append(child)
    return projection


#==============================================================================
# Main part.
#==============================================================================

def validate(inp, out, args, tag_sets, known_sent_ids):
    global tree_counter
    for comments, sentence in trees(inp, tag_sets, args):
        tree_counter += 1
        # The individual lines were validated already in trees().
        # What follows is tests that need to see the whole tree.
        idseqok = validate_ID_sequence(sentence) # level 1
        validate_token_ranges(sentence) # level 1
        if args.level > 1:
            validate_source_sent_id(comments, known_sent_ids, args.lang) # level 2
            validate_text_meta(comments, sentence) # level 2
            validate_root(sentence) # level 2
            validate_ID_references(sentence) # level 2
            validate_deps(sentence) # level 2 
            validate_misc(sentence) # level 2 
            validate_mwe_sequence(sentence) # level 2 
        
            # Avoid building tree structure if the sequence of node ids is corrupted.
            if idseqok:
                tree = build_tree(sentence) # level 2 test: tree is single-rooted, connected, cycle-free
            else:
                tree = None
        
            if not tree:
                testlevel = 2
                testclass = 'Format'
                testid = 'skipped-corrupt-tree'
                testmessage = "Skipping annotation tests because of corrupt tree structure."
                warn(testmessage, testclass, testlevel=testlevel, testid=testid, lineno=False)
    validate_newlines(inp) # level 1


if __name__=="__main__":
    opt_parser = argparse.ArgumentParser(description="CUPT validation script. Python 3 is needed to run it!")

    io_group = opt_parser.add_argument_group("Input / output options")
    io_group.add_argument('--quiet', dest="quiet", action="store_true", default=False, help='Do not print any error messages. Exit with 0 on pass, non-zero on fail.')
    io_group.add_argument('--max-err', action="store", type=int, default=20, help='How many errors to output before exiting? 0 for all. Default: %(default)d.')
    io_group.add_argument("--underspecified_mwes", action='store_true', default=False, help='If set, check that all MWEs are underspecified as "_" (for blind).')
    io_group.add_argument('input', nargs='*', help='Input file name(s), or "-" or nothing for standard input.')

    list_group = opt_parser.add_argument_group("Tag sets", "Options relevant to checking tag sets.")
    list_group.add_argument("--level", action="store", type=int, default=3, dest="level", help="Level 1: Test only CUPT backbone. Level 2: PARSEME and UD format. Level 3: PARSEME releases.")

    args = opt_parser.parse_args() #Parsed command-line arguments
    error_counter={} # Incremented by warn()  {key: error type value: its count}
    tree_counter=0

    if args.underspecified_mwes:
        DEFAULT_MWE='_'

    # Level of validation
    if args.level < 1:
        print('Option --level must not be less than 1; changing from %d to 1' % args.level, file=sys.stderr)
        args.level = 1
    # No language-specific tests for levels 1-3
    # Anyways, any Feature=Value pair should be allowed at level 3 (because it may be language-specific),
    # and any word form or lemma can contain spaces (because language-specific guidelines may allow it).
    # We can also test language 'ud' on level 4; then it will require that no language-specific features are present.
    if args.level < 4:
        args.lang = 'ud'

    # Sets of tags for every column that needs to be checked, plus (in v2) other sets, like the allowed tokens with space
    tagsets = {XPOS:None, UPOS:None, FEATS:None, DEPREL:None, DEPS:None, TOKENSWSPACE:None, AUX:None, MWE:None}
    tagsets[UPOS] = load_upos_set('cpos.ud')
    tagsets[DEPREL] = load_deprel_set('deprels.json', args.lang)
    tagsets[MWE] = load_mwe_set('mwe.parseme')

    out = sys.stdout # hard-coding - does this ever need to be anything else?

    try:
        known_sent_ids=set()
        open_files=[]
        if args.input==[]:
            args.input.append('-')
        for fname in args.input:
            if fname=='-':
                # Set PYTHONIOENCODING=utf-8 before starting Python. See https://docs.python.org/3/using/cmdline.html#envvar-PYTHONIOENCODING
                # Otherwise ANSI will be read in Windows and locale-dependent encoding will be used elsewhere.
                open_files.append(sys.stdin)
            else:
                open_files.append(io.open(fname, 'r', encoding='utf-8'))
        for curr_fname, inp in zip(args.input, open_files):
            validate(inp, out, args, tagsets, known_sent_ids)
    except:
        warn('Exception caught!', 'Format')
        # If the output is used in an HTML page, it must be properly escaped
        # because the traceback can contain e.g. "<module>". However, escaping
        # is beyond the goal of validation, which can be also run in a console.
        traceback.print_exc()
    # Summarize the warnings and errors.
    passed = True
    nerror = 0
    if error_counter:
        for k, v in sorted(error_counter.items()):
            if k == 'Warning':
                errors = 'Warnings'
            else:
                errors = k+' errors'
                nerror += v
                passed = False
            if not args.quiet:
                print('%s: %d' % (errors, v), file=sys.stderr)
    # Print the final verdict and exit.
    if passed:
        if not args.quiet:
            print('*** PASSED ***', file=sys.stderr)
        sys.exit(0)
    else:
        if not args.quiet:
            print('*** FAILED *** with %d errors' % nerror, file=sys.stderr)
        sys.exit(1)
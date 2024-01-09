#! /usr/bin/env python3
# Original code (2015) by Filip Ginter and Sampo Pyysalo.
# DZ 2018-11-04: Porting the validator to Python 3.
# DZ: Many subsequent changes. See the git history.

# Modified on 13/04/2023 for PARSEME corpora validation
# Level 1 and level 2 from UD are used
# Add tests on PARSEME:MWE column
import sys
import io
import subprocess
import os.path
import argparse
import traceback
import json
# According to https://stackoverflow.com/questions/1832893/python-regex-matching-unicode-properties,
# the regex module has the same API as re but it can check Unicode character properties using \p{}
# as in Perl.
#import re
import regex as re


THISDIR=os.path.dirname(os.path.realpath(os.path.abspath(__file__))) # The folder where this script resides.
# UD Validation release 2.13
# https://github.com/UniversalDependencies/tools/tree/r2.13
UD_VALIDATE = f"{THISDIR}/UD_Validation/validate.py"

# Constants for the column indices
COLCOUNT=11
ID,FORM,LEMMA,UPOS,XPOS,FEATS,HEAD,DEPREL,DEPS,MISC,MWE=range(COLCOUNT)
MWE_COLNAME = 'PARSEME:MWE'
ID_COLNAME = 'ID'
COLNAMES = ''

# default values for columns
DEFAULT_ID = 1
DEFAULT_FORM = "xxx"
DEFAULT_LEMMA = "_"
DEFAULT_UPOS = "X"
DEFAULT_XPOS = "_"
DEFAULT_FEATS = "_"
DEFAULT_HEAD = 1
DEFAULT_DEPREL = "dep"
DEFAULT_DEPS = "_"
DEFAULT_MISC = "_"
DEFAULT_MWE = '*'

# Global variables:
curr_line = 0 # Current line in the input file
comment_start_line = 0 # The line in the input file on which the current sentence starts, including sentence-level comments.
sentence_line = 0 # The line in the input file on which the current sentence starts (the first node/token line, skipping comments)
sentence_id = None # The most recently read sentence id
error_counter = {} # Incremented by warn()  {key: error type value: its count}
tree_counter = 0  # number of trees


###### Support functions

def is_whitespace(line):
    """
    Checks if the entire line consists of only whitespace characters. 
    """
    return re.match(r"^\s+$", line)

def is_word(cols):
    """
    Checks if words are indexed with integers 
    """
    return re.match(r"^[1-9][0-9]*$", cols[ID])

def load_file(filename):
    """
    Loads lines that aren't starting # into a set
    """
    res = set()
    with io.open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            line=line.strip()
            if not line or line.startswith('#'):
                continue
            res.add(line)
    return res

def load_languages_set(filename):
    """
    Loads the list of permitted languages and returns it as a set.
    """
    res = load_file(os.path.join(THISDIR, 'data', filename))
    return res

def load_mwe_set(filename, lcode):
    """
    Loads the list of permitted MWE tags and returns it as a set.
    """
    res = load_file(os.path.join(THISDIR, 'data', filename))
    with open(os.path.join(THISDIR, 'data', filename), 'r', encoding='utf-8') as f:
        all_mwe_categories = json.load(f)
    # Universal mwe tag set
    mwe_set = set(all_mwe_categories['all'])

    # defined language-specific mwe tag set
    if lcode.lower() in all_mwe_categories:
        mwe_set.update(all_mwe_categories[lcode.lower()])
    return mwe_set

def warn(msg, error_type, testlevel=0, testid='some-test', lineno=True, noterr=False, nodelineno=0, nodeid=0):
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
    if not noterr:
        error_counter[error_type] = error_counter.get(error_type, 0)+1
    # else:
    #     error_counter[error_type] = 0
        
    if not args.quiet:
        if args.max_err > 0 and not noterr and error_counter[error_type] == args.max_err:
            print(('...suppressing further errors regarding ' + error_type), file=sys.stderr)
        elif args.max_err > 0 and not noterr and error_counter[error_type] > args.max_err:
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


def validate_first_line(line: str):
    """
    Ensures that the first line correctly indicates global.columns and includes the ID and PARSEME:MWE columns.
    """
    global COLNAMES, MWE, ID
    
    testlevel = 1
    testclass = 'Format'
    ok = True
    
    COLNAMES = line.split("=")[-1].strip().split()
    
    if not "global.columns =" in line:
        testid = 'invalid-first-line'
        testmessage = "Spurious first line: '%s'. First line must specify global.columns" % (line)
        warn(testmessage, testclass, testlevel=testlevel, testid=testid)
        ok = False
    
    try:
        COLNAMES.index(ID_COLNAME)
    except ValueError:
        testid = 'missing-id-column'
        testmessage = "Spurious first line: '%s'. First line must specify column %s" % (line, ID_COLNAME)
        warn(testmessage, testclass, testlevel=testlevel, testid=testid)
        ok = False
    
    try:
        COLNAMES.index(MWE_COLNAME)
    except ValueError:
        testid = 'missing-mwe-column'
        testmessage = "Spurious first line: '%s'. First line must specify column %s" % (line, MWE_COLNAME)
        warn(testmessage, testclass, testlevel=testlevel, testid=testid)
        ok = False
    
    MWE = COLNAMES.index(MWE_COLNAME)
    ID = COLNAMES.index(ID_COLNAME)
    
    return ok
    
    
    
##### Tests applicable to the whole sentence

def validate_mwe_codes(cols: list, tag_sets: dict):
    """
    Checks general constraints on valid MWE codes
    """
    testlevel = 2
    testclass = 'MWE'
    
    # MWE codes
    for mwe_code in cols[MWE].split(";"):
        try:
            mwe_id = int(mwe_code)
        except ValueError:
            try:
                mwe_id, mwe_categ = mwe_code.split(':')
                mwe_id = int(mwe_id)
            except ValueError:
                testid = 'invalid-mwe-code'
                testmessage = 'Invalid MWE code %s in the MWE content %s (expecting an integer like \'3\' a pair like \'3:LVC.full\')' % (mwe_code, cols[MWE])
                warn(testmessage, testclass, testlevel=testlevel, testid=testid)
                return 1
            else:
                # Level 3, remove NotMWE tag
                if args.level > 2:
                    testlevel = 3
                    tag_sets[MWE].discard("NotMWE")

                if mwe_categ not in tag_sets[MWE]:
                        testid = 'unknown-mwe-category'
                        testmessage = "Unknown MWE category '%s' in the MWE code '%s'." % (mwe_categ, mwe_code)
                        warn(testmessage, testclass, testlevel=testlevel, testid=testid)
                        return 1
    return 0


def validate_mwe_cols(cols: list, tag_sets: dict, underspecified_mwes: bool = False):
    """
    All tests that can run on a single line (content of the column MWE). Done as soon as the line is read,
    called from trees() if level>1.
    """
    testlevel = 2
    testclass = 'MWE'

    if MWE >= len(cols):
        return 0 # this has been already reported in trees()
    
    # If the words are indexed with integers 
    if is_word(cols):
        if cols[MWE] == DEFAULT_MWE:
            return 0
        else:
            if underspecified_mwes and cols[MWE] != DEFAULT_MWE:
                testid = 'unknown-mwe-content'
                testmessage = "Unknown MWE content, only _ (for blind version): '%s'." % cols[MWE]
                warn(testmessage, testclass, testlevel=testlevel, testid=testid)
                return 1
        # Checks general constraints on valid MWE codes
        validate_mwe_codes(cols, tag_sets) # level 2 et up
    # multiword tokens or empty nodes 
    else:
        if cols[MWE] != DEFAULT_MWE:
            testid = 'invalid-mwe'
            testmessage = "Invalid mwe annotation, only _ (for blind version) or *: '%s'." % cols[MWE]
            warn(testmessage, testclass, testlevel=testlevel, testid=testid)
            return 1


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
    col_idx = MWE
    
    # Number of columns is not match to global.columns
    if len(COLNAMES) != len(cols):
        testid = 'number-columns'
        testmessage = 'Number of columns does not match global.columns (Got %d. Expected %d)' % (len(cols), len(COLNAMES))
        warn(testmessage, testclass, testlevel=testlevel, testid=testid)
    else:
        # Must never be empty
        if not cols[col_idx]:
            testid = 'empty-column'
            testmessage = 'Empty value in column %s.' % (MWE_COLNAME)
            warn(testmessage, testclass, testlevel=testlevel, testid=testid)
        else:
            # Must never have leading/trailing whitespace
            if cols[col_idx][0].isspace():
                testid = 'leading-whitespace'
                testmessage = 'Leading whitespace not allowed in column %s.' % (MWE_COLNAME)
                warn(testmessage, testclass, testlevel=testlevel, testid=testid)
            if cols[col_idx][-1].isspace():
                testid = 'trailing-whitespace'
                testmessage = 'Trailing whitespace not allowed in column %s.' % (MWE_COLNAME)
                warn(testmessage, testclass, testlevel=testlevel, testid=testid)
            # Must never contain two consecutive whitespace characters
            if whitespace2_re.match(cols[col_idx]):
                testid = 'repeated-whitespace'
                testmessage = 'Two or more consecutive whitespace characters not allowed in column %s.' % (MWE_COLNAME)
                warn(testmessage, testclass, testlevel=testlevel, testid=testid)
    
        if whitespace_re.match(cols[col_idx]):
            testid = 'invalid-whitespace'
            testmessage = "White space not allowed in column %s: '%s'." % (MWE_COLNAME, cols[col_idx])
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
    global curr_line, comment_start_line, sentence_line
    comments = [] # List of comment lines to go with the current sentence
    lines = [] # List of token/word lines of the current sentence
    corrupted = False # In case of wrong number of columns check the remaining lines of the sentence but do not yield the sentence for further processing.
    comment_start_line = None
    # Loop over all lines in the files
    for line_counter, line in enumerate(inp):
        # current line number
        curr_line += 1
        
        if line_counter == 0:
            # Ensures that the first line correctly indicates global.columns and includes the ID and PARSEME:MWE columns.
            corrupted = not validate_first_line(line)
        
        if not comment_start_line:
            comment_start_line = curr_line
        # remove the Unicode newline character (\n) from the end of the string. 
        line = line.rstrip(u"\n")

        # If the entire line consists of only whitespace characters. 
        if is_whitespace(line):
            # We will pretend that the line terminates a sentence in order to avoid subsequent misleading error messages.
            if lines:
                if not corrupted:
                    yield comments, lines
                comments = []
                lines = []
                comment_start_line = None
        # empty line
        elif not line: 
            if lines: # sentence done
                if not corrupted:
                    yield comments, lines
                comments=[]
                lines=[]
                comment_start_line = None
            
        # comment lines
        elif line[0]=='#':
            # We will really validate sentence ids later. But now we want to remember
            # everything that looks like a sentence id and use it in the error messages.
            # Line numbers themselves may not be sufficient if we are reading multiple
            # files from a pipe.
            if not lines: # before sentence
                comments.append(line)
            
        # Tokenization lines
        elif line[0].isdigit():
            # validate_unicode_normalization(line)
            if not lines: # new sentence
                sentence_line=curr_line
            cols=line.split(u"\t")
            
            lines.append(cols)
            # pertain to the CUPT file format
            validate_cols_level1(cols)
            if args.level > 1:
                validate_mwe_cols(cols, tag_sets, args.underspecified_mwes)
    else: # end of file
        if comments or lines: # These should have been yielded on an empty line!
            if not corrupted:
                yield comments, lines


#==============================================================================
# Level 2 tests. Tree structure, universal tags and deprels. Note that any
# well-formed Feature=Valid pair is allowed (because it could be language-
# specific) and any word form or lemma can contain spaces (because language-
# specific guidelines may permit it).
#==============================================================================

###### Metadata tests #########

def validate_source_sent_id(comments: list) -> None:
    """Validate the comment line source_sent_id

    Args:
        comments (list): Comment lines

    Returns:
        None
    """
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


metadata_re = re.compile('^#\s*metadata\s*=\s*')
def validate_text_meta(comments: list) -> None:
    """Validate the comment line metadata

    Args:
        comments (list): Comment lines

    Returns:
        None
    """

    testlevel = 3
    testclass = 'Metadata'
    for c in comments:
        if metadata_re.match(c):
            testid = 'forbidden-metadata'
            testmessage = "The metadata field is forbidden in metadata comments: %s" % c
            warn(testmessage, testclass, testlevel=testlevel, testid=testid)


def validate_mwe_sequence(tree: list) -> None:
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
                        # Already reported in validate_mwe_cols()
                        pass
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
            warn(testmessage, testclass, testlevel=testlevel, testid=testid, lineno=False, noterr=True)     

        if max(mweid2categ.keys()) > number_tokens: # out of range
            testid = 'mwe-interval-out'
            testmessage = 'Spurious mwe interval 1-%d (out of range)' % (max(mweid2categ.keys()))
            warn(testmessage, testclass, testlevel=testlevel, testid=testid)


#==============================================================================
# Main part.
#==============================================================================

def validate(inp, args, tag_sets):
    global tree_counter
    for comments, sentence in trees(inp, tag_sets, args):
        tree_counter += 1
        # The individual lines were validated already in trees().
        # What follows is tests that need to see the whole tree.
        if args.level > 1:
            validate_source_sent_id(comments) # level 2
            validate_mwe_sequence(sentence) # level 2 
            if args.level > 2:
                validate_text_meta(comments) # level 3


def get_ud_columns(colnames: list, line: str, token_id: int) -> list:
    """Get a UD line from PARSEME line

    Args:
        colnames (list): PARSEME column names
        line (str): A PARSEME line
        token_id (int): a tokenization id

    Returns:
        A UD line (list)
    """
    # initialize the UD line
    ud_columns = ['_' for _ in range(COLCOUNT-1)]

    # Split the line into columns
    columns = line.strip().split("\t")

    # Write ID column into the .conllu file
    if "ID" in colnames:
        ud_columns[ID] = columns[colnames.index("ID")]
    else:
        ud_columns[ID] = token_id
    
    # Write FORM column into the .conllu file
    if "FORM" in colnames:
        ud_columns[FORM] = columns[colnames.index("FORM")]
    else:
        ud_columns[FORM] = DEFAULT_FORM
    
    # Write LEMMA column into the .conllu file
    if "LEMMA" in colnames:
        ud_columns[LEMMA] = columns[colnames.index("LEMMA")]
    else:
        ud_columns[LEMMA] = DEFAULT_LEMMA
    
    # Write UPOS column into the .conllu file
    if "UPOS" in colnames:
        ud_columns[UPOS] = columns[colnames.index("UPOS")]
    else:
        ud_columns[UPOS] = DEFAULT_UPOS
    
    # Write XPOS column into the .conllu file
    if "XPOS" in colnames:
        ud_columns[XPOS] = columns[colnames.index("XPOS")]
    else:
        ud_columns[XPOS] = DEFAULT_XPOS
    
    # Write FEATS column into the .conllu file
    if "FEATS" in colnames:
        ud_columns[FEATS] = columns[colnames.index("FEATS")]
    else:
        ud_columns[FEATS] = DEFAULT_FEATS
    
    # Write HEAD column into the .conllu file
    if "HEAD" in colnames:
        ud_columns[HEAD] = columns[colnames.index("HEAD")]
    else:
        if token_id == 1:
            ud_columns[HEAD] = 0
        else:
            ud_columns[HEAD] = DEFAULT_HEAD
    
    # Write DEPREL column into the .conllu file
    if "DEPREL" in colnames:
        ud_columns[DEPREL] = columns[colnames.index("DEPREL")]
    else:
        if token_id == 1:
            ud_columns[DEPREL] = "root"
        else:
            ud_columns[DEPREL] = DEFAULT_DEPREL
    
    # Write DEPS column into the .conllu file
    if "DEPS" in colnames:
        ud_columns[DEPS] = columns[colnames.index("DEPS")]
    else:
        ud_columns[DEPS] = DEFAULT_DEPS
    
    # Write MISC column into the .conllu file
    if "MISC" in colnames:
        ud_columns[MISC] = columns[colnames.index("MISC")]
    else:
        ud_columns[MISC] = DEFAULT_MISC
    
    return ud_columns


sentid_re=re.compile('^# source_sent_id\s*=\s*(\S+)\s+(\S+)\s+(\S+)$')
def cupt2conllu(cupt_input_file: str, conllu_output_file: str) -> None:
    """Convert a .cupt file to a .conllu file

    Args:
        cupt_input_file (str): A .cupt file
        conllu_output_file (str): A .conllu file

    Returns:
        None
    """
    testlevel = 1
    testclass = 'Format'
    ok = True

    # Open files
    with open(cupt_input_file, "r", encoding="utf-8") as infile, open(conllu_output_file, "w", encoding="utf-8") as outfile:
        # First line
        line = next(infile)

        colnames = line.split("=")[-1].strip().split()
        outfile.write(line)

        # First tokenization line
        token_id = 1

        # Loop over all lines in the .cupt file
        for line in infile:
            # Ignore empty lines and comment lines
            if line.strip() == "":
                outfile.write(line)
                # reset for the new sentence
                token_id = 1
                continue
            
            match = sentid_re.match(line)
            if match:
                prefix_uri = match.group(1)
                file_path_under_root = match.group(2)
                sentence_id = match.group(3)
                # concatenate all three parts to form an id
                ud_sent_id = prefix_uri + file_path_under_root + sentence_id
                # remove all the forward slash
                ud_sent_id = ud_sent_id.replace("/", "")
                outfile.write(f"# sent_id = {ud_sent_id}" + "\n")
                # reset for the new sentence
                token_id = 1
                continue

            if line.startswith("#"):
                outfile.write(line)
                # reset for the new sentence
                token_id = 1
                continue
            
            # Get a UD line from PARSEME line
            ud_columns = get_ud_columns(colnames, line, token_id)
            
            # next tokenization line
            token_id += 1

            # Join the columns and write them to the output file
            outfile.write("\t".join([str(x) for x in ud_columns]) + "\n")
        
        # Close files
        infile.close()
        outfile.close()
    
    # Errors
    if not ok:
        # Remove conllu files
        if os.path.exists(conllu_output_file):
            os.remove(conllu_output_file)

    return ok


def run_ud_validation() -> int:
    """Run UD validation tests

    Args:
        None

    Returns:
        0 for passed
        1 for failed
    """
    # Transform CUPT to CONLLU
    conllu_files = [filename + ".conllu" for filename in args.input]
    for index in range(len(conllu_files)):
        if not cupt2conllu(args.input[index], conllu_files[index]):
            return 1
    
    # Messages
    if not args.quiet:
        print("========================================================================================")
        print("============================***UD Validation***=========================================")
        print("========================================================================================")
    
    # Only level 1 and 2 of UD are used
    if args.level > 2:
        level = 2
    else:
        level = args.level

    # Store the UD arguments in a list
    if args.quiet:
        ud_validate_arguments = ["--quiet", "--max-err", str(args.max_err), "--level", str(level), "--lang", "ud"] + conllu_files
    else:
        ud_validate_arguments = ["--max-err", str(args.max_err), "--level", str(level), "--lang", "ud"] + conllu_files

    # Execute the script UD validation using subprocess.run()
    command = ["python3", UD_VALIDATE] + ud_validate_arguments
    result = subprocess.run(command, capture_output=True, text=True)
    print(result.stderr)

    # Remove conllu files
    for file in conllu_files:
        if os.path.exists(file):
            os.remove(file)
    
    return result.returncode


def run_parseme_validation() -> int:
    """Run PARSEME validation tests

    Args:
        None

    Returns:
        0 for passed
        1 for failed
    """
    global DEFAULT_MWE

    # Messages
    if not args.quiet:
        print("========================================================================================", file=sys.stderr)
        print("============================***PARSEME Validation***====================================", file=sys.stderr)
        print("========================================================================================", file=sys.stderr)
    
    # all MWEs are underspecified as "_"
    if args.underspecified_mwes:
        DEFAULT_MWE='_'
    else:
        DEFAULT_MWE='*'
    
    # Sets of tags for every column that needs to be checked
    tagsets = {MWE:None}
    # Load MWE tag sets
    tagsets[MWE] = load_mwe_set('mwe.json', args.lang)

    # Open files and run tests
    try:
        open_files=[]
        for fname in args.input:
            if fname=='-':
                # Set PYTHONIOENCODING=utf-8 before starting Python. See https://docs.python.org/3/using/cmdline.html#envvar-PYTHONIOENCODING
                # Otherwise ANSI will be read in Windows and locale-dependent encoding will be used elsewhere.
                open_files.append(sys.stdin)
            else:
                open_files.append(io.open(fname, 'r', encoding='utf-8'))

        for curr_fname, inp in zip(args.input, open_files):
            # Parseme validation tests
            validate(inp, args, tagsets)
            inp.close()
    except:
        warn('Exception caught!', 'Format')
        # If the output is used in an HTML page, it must be properly escaped
        # because the traceback can contain e.g. "<module>". However, escaping
        # is beyond the goal of validation, which can be also run in a console.
        traceback.print_exc()
    
    # Summarize the warnings and errors.
    parseme_returncode = 0
    nerror = 0
    if error_counter:
        for k, v in sorted(error_counter.items()):
            if k == 'Warning':
                errors = 'Warnings'
            else:
                errors = k+' errors'
                nerror += v
                parseme_returncode = 1
            if not args.quiet:
                print('%s: %d' % (errors, v), file=sys.stderr)

    # Print the final verdict and exit.
    if not parseme_returncode:
        if not args.quiet:
            print('*** PASSED ***')
    else:
        if not args.quiet:
            print('*** FAILED *** with %d errors' % nerror, file=sys.stderr)
    
    return parseme_returncode


def main():
    global args, error_counter, tree_counter
    opt_parser = argparse.ArgumentParser(description="CUPT validation script. Python 3 is needed to run it!")

    io_group = opt_parser.add_argument_group("Input / output options")
    io_group.add_argument('--quiet', dest="quiet", action="store_true", default=False, help='Do not print any error messages. Exit with 0 on pass, non-zero on fail.')
    io_group.add_argument('--max-err', action="store", type=int, default=20, help='How many errors to output before exiting? 0 for all. Default: %(default)d.')
    io_group.add_argument("--underspecified_mwes", action='store_true', default=False, help='If set, check that all MWEs are underspecified as "_" (for blind).')
    io_group.add_argument('input', nargs='*', help='Input file name(s)')

    list_group = opt_parser.add_argument_group("Tag sets", "Options relevant to checking tag sets.")
    list_group.add_argument("--lang", action="store", required=True, default=None, help="Which langauge are we checking? If you specify this (as a two-letter code), the tags will be checked using the language-specific files in the data/ directory of the validator.")
    list_group.add_argument("--level", action="store", type=int, default=3, dest="level", help="The validation tests are organized to several levels. Level 1: Test only the CUPT backbone: order of lines, newline encoding, core tests that check the file integrity. Level 2: PARSEME and UD contents. Level 3: PARSEME releases: NotMWE tag excluded, more constraints on metadata.")
 
    args = opt_parser.parse_args() #Parsed command-line arguments
    error_counter = {} # Incremented by warn()  {key: error type value: its count}
    tree_counter = 0   # number of trees
    # Set of all valid languages in PARSEME corpora
    langs = load_languages_set('languages.code')

    if args.lang.upper() not in langs:
        warn('Invalid language code!', 'Format')
    
    # Level of validation
    if args.level < 1:
        print('Option --level must not be less than 1; changing from %d to 1' % args.level, file=sys.stderr)
        args.level = 1
    
    # Run PARSEME validation tests
    parseme_returncode = run_parseme_validation()
    # If PARSEME validation tests failed
    if parseme_returncode:
        return parseme_returncode
    
    # Run UD validation tests
    ud_returncode = run_ud_validation()
    return ud_returncode


if __name__== "__main__":
    sys.exit(main())
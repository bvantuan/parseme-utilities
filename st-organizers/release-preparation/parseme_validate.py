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
# UD Validation release 2.11
# https://github.com/UniversalDependencies/tools/tree/r2.11
UD_VALIDATE = f"{THISDIR}/UD_Validation_release_2.11/validate.py"

# Constants for the column indices
COLCOUNT=11
ID,FORM,LEMMA,UPOS,XPOS,FEATS,HEAD,DEPREL,DEPS,MISC,MWE=range(COLCOUNT)
MWE_COLNAME = 'PARSEME:MWE'
# Set of all valid languages in PARSEME corpora
LANGS = set("UD AR BG CS DE EL EN ES EU FA FR GA HE HR HU HI IT LT MT PL PT RO SL SR SV TR ZH".split())

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
error_counter = {} # key: error type value: error count


###### Support functions

def is_whitespace(line):
    # checks if the entire line consists of only whitespace characters. 
    return re.match(r"^\s+$", line)

def load_file(filename):
    res = set()
    with io.open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            line=line.strip()
            if not line or line.startswith('#'):
                continue
            res.add(line)
    return res

def load_mwe_set(filename, lcode):
    """
    Loads the list of permitted MWE tags and returns it as a set.
    """
    res = load_file(os.path.join(THISDIR, 'data', filename))
    with open(os.path.join(THISDIR, 'data', filename), 'r', encoding='utf-8') as f:
        all_mwe_categories = json.load(f)
    # Universal mwe tag set
    mwe_set = set(all_mwe_categories['ud'])

    # defined language-specific mwe tag set
    if lcode.lower() in all_mwe_categories:
        mwe_set.update(all_mwe_categories[lcode.lower()])
    return mwe_set

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


##### Tests applicable to the whole sentence
mwecode_re = re.compile(r'^(\d+)(?::([a-zA-Z]+(?:\.[a-zA-Z]+)?))?$')
def validate_character_constraints(cols):
    """
    Checks general constraints on valid characters of MWE codes
    """
    testlevel = 2
    testclass = 'MWE'
    # MWE codes
    # If it is a MWE
    if cols[MWE] not in "*_":
        for mwe_code in cols[MWE].split(";"):
            if not mwecode_re.match(mwe_code):
                testid = 'invalid-mwe'
                testmessage = "Invalid MWE code '%s'." % mwe_code
                warn(testmessage, testclass, testlevel=testlevel, testid=testid)


def validate_mwe(cols: list, tag_sets: dict) -> None:
    """Validate MWE tag set

    Args:
        cols (list): Values of columns of a line
        tag_sets (dict): MWE tag set

    Returns:
        None
    """
    testlevel = 2
    testclass = 'MWE'

    if MWE >= len(cols):
        return # this has been already reported in trees()
    if cols[MWE] == DEFAULT_MWE:
        return
    else:
        if args.underspecified_mwes and cols[MWE] != DEFAULT_MWE:
            testid = 'unknown-mwe'
            testmessage = "Unknown MWE tag, only _ (for blind version): '%s'." % cols[MWE]
            warn(testmessage, testclass, testlevel=testlevel, testid=testid)
    
    # Remove digit elements using a list comprehension
    mwe_tags = set([tag for tag in re.split(r"[:;]", cols[MWE]) if not tag.isdigit()])

    # Level 3, remove NotMWE tag
    if args.level > 2:
        testlevel = 3
        tag_sets[MWE].discard("NotMWE")

    if mwe_tags and not mwe_tags <= tag_sets[MWE]:
            testid = 'unknown-mwe'
            testmessage = "Unknown MWE tag: '%s'." % cols[MWE]
            warn(testmessage, testclass, testlevel=testlevel, testid=testid)


def validate_cols(cols, tag_sets):
    """
    All tests that can run on a single line. Done as soon as the line is read,
    called from trees() if level>1.
    """
    validate_character_constraints(cols) # level 2
    validate_mwe(cols, tag_sets)  # level 2 et up


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
    comment_start_line = None
    # Loop over all lines in the files
    for line_counter, line in enumerate(inp):
        # current line number
        curr_line += 1
        
        if not comment_start_line:
            comment_start_line = curr_line
        # remove the Unicode newline character (\n) from the end of the string. 
        line = line.rstrip(u"\n")

        # If the entire line consists of only whitespace characters. 
        if is_whitespace(line):
            # We will pretend that the line terminates a sentence in order to avoid subsequent misleading error messages.
            if lines:
                yield comments, lines
                comments = []
                lines = []
                comment_start_line = None
        # empty line
        elif not line: 
            if lines: # sentence done
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
            # pertain to the CoNLL-U file format
            validate_cols_level1(cols)
            if args.level > 1:
                validate_cols(cols, tag_sets)
    else: # end of file
        if comments or lines: # These should have been yielded on an empty line!
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

    # Open files
    with open(cupt_input_file, "r", encoding="utf-8") as infile, open(conllu_output_file, "w", encoding="utf-8") as outfile:
        # First line
        line = next(infile)

        colnames = line.split("=")[-1].strip().split()
        if not "global.columns =" in line:
            testid = 'invalid-first-line'
            testmessage = "Spurious first line: '%s'. First line must specify global.columns" % (line)
            warn(testmessage, testclass, testlevel=testlevel, testid=testid)
            sys.exit(1)
        
        try:
            colnames.index(MWE_COLNAME)
        except ValueError:
            testid = 'missing-mwe-column'
            testmessage = "Spurious first line: '%s'. First line must specify column %s" % (line, MWE_COLNAME)
            warn(testmessage, testclass, testlevel=testlevel, testid=testid)
            sys.exit(1)

        # First tokenization line
        token_id = 1

        # Loop over all lines in the .cupt file
        for line in infile:
            ud_columns = ['_' for _ in range(COLCOUNT-1)]
            # Ignore empty lines and comment lines
            if line.strip() == "":
                outfile.write(line)
                # reset for the new sentence
                token_id = 1
                continue
            
            match = sentid_re.match(line)
            if match:
                sentence_id = match.group(3)
                outfile.write(f"# sent_id = {sentence_id}" + "\n")
                # reset for the new sentence
                token_id = 1
                continue

            if line.startswith("#"):
                outfile.write(line)
                # reset for the new sentence
                token_id = 1
                continue

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
            
            # next tokenization line
            token_id += 1

            # Join the columns and write them to the output file
            outfile.write("\t".join([str(x) for x in ud_columns]) + "\n")
        
        # Close files
        infile.close()
        outfile.close()


if __name__=="__main__":
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

    # Transform CUPT to CONLLU
    conllu_files = [filename + ".conllu" for filename in args.input]
    for index in range(len(conllu_files)):
        cupt2conllu(args.input[index], conllu_files[index])
    
    # Store the arguments in a list
    if args.quiet:
        ud_validate_arguments = ["--quiet", "--max-err", str(args.max_err), "--level", str(args.level), "--lang", "ud"] + conllu_files
    else:
        ud_validate_arguments = ["--max-err", str(args.max_err), "--level", str(args.level), "--lang", "ud"] + conllu_files
    # Execute the script UD validation using subprocess.run()
    command = ["python3", UD_VALIDATE] + ud_validate_arguments

    print("========================================================================================")
    print("============================***UD Validation***=========================================")
    print("========================================================================================")
    result = subprocess.run(command, capture_output=True, text=True)
    print(result.stderr)
    # Remove conllu files
    for file in conllu_files:
        if os.path.exists(file):
            os.remove(file)
        

    print("========================================================================================")
    print("============================***PARSEME Validation***====================================")
    print("========================================================================================")
    error_counter={} # Incremented by warn()  {key: error type value: its count}
    tree_counter=0

    if args.underspecified_mwes:
        DEFAULT_MWE='_'

    # Level of validation
    if args.level < 1:
        print('Option --level must not be less than 1; changing from %d to 1' % args.level, file=sys.stderr)
        args.level = 1

    # Sets of tags for every column that needs to be checked, plus (in v2) other sets, like the allowed tokens with space
    tagsets = {MWE:None}

    if args.lang.upper() not in LANGS:
        warn('Invalid language code!', 'Format')
    tagsets[MWE] = load_mwe_set('mwe.json', args.lang)

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
            line = next(inp)
            colnames = line.split("=")[-1].strip().split()
            MWE = colnames.index(MWE_COLNAME)
            curr_line += 1
            
            validate(inp, args, tagsets)
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
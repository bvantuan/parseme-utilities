#! /usr/bin/env python3

import argparse
import collections
import json
from xml.sax.saxutils import escape as ESC

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../lib"))
import dataalign

import _shared_code


parser = argparse.ArgumentParser(description="""
        Read input file from two annotators and generate a
        webpage describing the MWEs. This webpage can be used
        to adjudicate the annotations.
        """)
parser.add_argument("--lang", choices=sorted(dataalign.LANGS), metavar="LANG", required=True,
        help="""ID of the target language (e.g. EN, FR, PL, DE...)""")
parser.add_argument("--annotation-1", type=str, required=True,
        help="""Path to input file for annotator A1 (preferably in FoLiA XML format, but PARSEME TSV works too)""")
parser.add_argument("--annotation-2", type=str, required=True,
        help="""Path to input file for annotator A2 (preferably in FoLiA XML format, but PARSEME TSV works too)""")


class Main:
    def __init__(self, args):
        self.args = args
        self.fname2id = {
            self.args.annotation_1 : 1,
            self.args.annotation_2 : 2,
        }

    def run(self):
        print(HTML_HEADER_1and2)
        print('<script>window.parsemeFilenameMapping = {}</script>'.format(
            json.dumps({i:f for (f,i) in self.fname2id.items()})))
        sents_1 = list(self.iter_sentences(self.args.annotation_1))
        sents_2 = list(self.iter_sentences(self.args.annotation_2))
        if len(sents_1) != len(sents_2):
            raise Exception('Input files have a different number of sentences: ' \
                            '{} and {}'.format(len(sents_1), len(sents_2)))

        for sent_no, (s1, s2) in enumerate(zip(sents_1, sents_2), 1):
            assert len(s1.tokens) == len(s2.tokens), \
                   'Sentence sizes do not match (#{})'.format(sent_no)

            mwes1 = list(s1.mwe_occurs())
            mwes2 = list(s2.mwe_occurs())
            if not mwes1 and not mwes2:
                print('<div class="sent-block">')
                print(' <div class="sent-header sent-header-no-annotations">Sentence #{}</div>'.format(sent_no))
                print(' <div class="mweoccur-block-list list-group"></div>')
                print('</div>')  # sent-block
                continue

            print('<div class="sent-block">')
            print(' <div class="sent-header">Sentence #{}</div>'.format(sent_no))
            print(' <div class="mweoccur-block-list list-group">')

            mwe_perfect_pairs, mwes1, mwes2 = self.extract_perfect_pairs(mwes1, mwes2)
            mwe_subset_pairs, mwes1, mwes2 = self.extract_subset_pairs(mwes1, mwes2)
            self.print_single_annotator(1, mwes1)
            self.print_single_annotator(2, mwes2)
            self.print_subset_pairs(mwe_subset_pairs)
            self.print_perfect_pairs(mwe_perfect_pairs)
            print(' </div>')  # mweoccur-block-list
            print('</div>')  # sent-block

        print(HTML_FOOTER)



    def iter_sentences(self, input_file):
        return dataalign.iter_sentences(self.args.lang, [input_file], None, verbose=False)


    def extract_perfect_pairs(self, mwes1, mwes2):
        r'''Return (List[(mwe1, mwe2)], List[mwe1], List[mwe2]).
        The pairs have the same span, but not necessarily the same MWE category.
        '''
        index_to_mwes1 = {m.indexes: m for m in mwes1}
        perfect_pairs = [(index_to_mwes1[m2.indexes], m2)
                         for m2 in mwes2 if m2.indexes in index_to_mwes1]
        perfect_indices = [m1.indexes for (m1, m2) in perfect_pairs]
        mwes1 = [m1 for m1 in mwes1 if m1.indexes not in perfect_indices]
        mwes2 = [m2 for m2 in mwes2 if m2.indexes not in perfect_indices]
        return perfect_pairs, mwes1, mwes2


    def extract_subset_pairs(self, mwes1, mwes2):
        r'''Return (List[(mwe1, mwe2)], List[mwe1], List[mwe2]).
        The span of MWEs in the pairs are a strict subset/superset of each other.
        '''
        matched = set()
        subset_pairs = []
        for m1 in mwes1:
            for m2 in mwes2:
                if m1 not in matched and m2 not in matched:
                    # If subset/superset, we accept as a partial match
                    if set(m1.indexes).issubset(set(m2.indexes)) \
                            or set(m1.indexes).issuperset(set(m2.indexes)):
                        subset_pairs.append((m1, m2))
                        matched.add(m1)
                        matched.add(m2)

        mwes1 = [m1 for m1 in mwes1 if m1 not in matched]
        mwes2 = [m2 for m2 in mwes2 if m2 not in matched]
        return subset_pairs, mwes1, mwes2




    def print_subset_pairs(self, mwe_subset_pairs):
        r'''Print pairs (a,b) where the span of a is a subset/superset of the span of b.'''
        for mwe1, mwe2 in mwe_subset_pairs:
            self._print_pair(mwe1, mwe2, errortype='SUBSET')

    def print_perfect_pairs(self, mwe_perfect_pairs):
        r'''Print pairs whose span match perfectly.'''
        for mwe1, mwe2 in mwe_perfect_pairs:
            if mwe1.category != mwe2.category:
                self._print_pair(mwe1, mwe2, errortype='LABEL')
        for mwe1, mwe2 in mwe_perfect_pairs:
            if mwe1.category == mwe2.category:
                self._print_pair(mwe1, mwe2, errortype='PERFECT')


    def _print_pair(self, mwe1, mwe2, errortype):
        r'''Print pair of MWEs; e.g.:
        | MWE 7 -- [=] [DECIDE]
        | A1: [LVC] I *had* a *bath* yesterday .
        | A2: [ID] I *had* *a* *bath* yesterday .
        '''
        if any(m.category not in dataalign.Categories.NON_MWES for m in [mwe1, mwe2]):
            self.print_mweoccur_block_header(errortype)
            self._print_mweo_of_annotator(mwe1, 1)
            self._print_mweo_of_annotator(mwe2, 2)
            self.print_mweoccur_block_footer()


    def print_single_annotator(self, annotator_number, mwes):
        r'''Print an MWE for a single annotator; e.g.:
        | MWE 7 -- [=] [DECIDE]
        | A2: [ID] I *had* *a* *bath* yesterday .
        '''
        for mwe in mwes:
            if mwe.category not in dataalign.Categories.NON_MWES:
                self.print_mweoccur_block_header('SINGLE')
                self._print_mweo_of_annotator(mwe, annotator_number)
                self.print_mweoccur_block_footer()

    def print_mweoccur_block_header(self, errortype):
        msg = {
            'SINGLE':  'PROBLEM: Single annotator',
            'SUBSET':  'PROBLEM: Different annotation spans',
            'LABEL':   'PROBLEM: Conflicting labels',
            'PERFECT': 'Perfect match',
        }[errortype]
        print('  <div class="mweoccur-block list-group-item">')
        print('  <button type="button" class="mweoccur-collapse-button mweoccur-collapse-button-problem-{} btn btn-default btn-sm">'.format(errortype))
        print('    <span class="mweoccur-glyph-up glyphicon glyphicon-collapse-up"></span>')
        print('    <span class="mweoccur-glyph-down glyphicon glyphicon-collapse-down" style="display:none"></span>')
        print('    <span class="mweoccur-errortype">{}</span>'.format(msg))
        print('  </button>')
        print('  <span class="mweoccur-hideable-part">')
        print('  <button type="button" class="mweoccur-decide-button btn btn-default btn-sm">DECIDE</button>')

    def print_mweoccur_block_footer(self):
        print('  </span>')  # hideable-part
        print('  </div>')  # mweoccur-block


    def _print_mweo_of_annotator(self, mweo, annot_number):
        r'''Print an MWE for given annotator number; e.g.:
        | A2: [ID] I *had* *a* *bath* yesterday .
        '''
        if mweo is not None:
            mweo_id = (self.fname2id[mweo.sentence.file_path], mweo.sentence.nth_sent, mweo.indexes)
            print('   <div class="mweoccur-of-annotator annotator-{}">'.format(annot_number))
            # Print mweoccur-perAnnotator-id; e.g. ["Foo.xml", 123, [5,7,8]]
            print('   <span class="mweoccur-perAnnotator-id">{}</span>'.format(ESC(json.dumps(mweo_id))))
            print('   <span class="mweo-annotator-name">A{}:</span>'.format(annot_number))
            print("".join(self._occur2html(mweo)))
            print('   </div>')  # mweoccur-of-annotator


    def _occur2html(self, occur):
        r"""Yield one MWE occurrence as HTML; e.g.:
        | [LVC] I *had* a *bath* yesterday
        | | Some comment typed by an annotator.
        """
        # Yield a label; e.g. [LVC]  -- the label contains a tooltip
        if occur.category == "Skipped":
            file_info = 'Possible MWE seen in file &quot;{}&quot;, sentence #{}'.format(
                ESC(occur.sentence.file_path), ESC(str(occur.sentence.nth_sent)))
        else:  # occur.category != "Skipped":
            file_info = 'Annotated in file &quot;{}&quot;, sentence #{}, by &quot;{}&quot; on {}'.format(
                    ESC(occur.sentence.file_path), ESC(str(occur.sentence.nth_sent)),
                    ESC(occur.metadata.annotator or "<unknown>"), ESC(str(occur.metadata.datetime or "<unknown-date>")))
        confidence_info = '' if occur.metadata.confidence is None else ' {}%'.format(int(occur.metadata.confidence*100))
        css_mwe_label = dataalign.Categories.css_name(occur.category)
        yield '<span class="label mwe-label {css_mwe_label}"' \
              'data-toggle="tooltip" title="{title}">{mwe_label}{confidence_info}</span><span> </span>' \
              .format(css_mwe_label=css_mwe_label, title=file_info,
                      mwe_label=ESC(occur.category), confidence_info=confidence_info)

        indexes = set(occur.indexes)
        yield '<span class="mweoccur-sentence">'
        for i, t in enumerate(occur.sentence.tokens):
            if i in indexes:
                posinfo = '' if (not t.univ_pos) else ' title="{}/{}"'.format(t.get('LEMMA', '??'), t.univ_pos)
                yield '<span class="mwe-elem" data-toggle="tooltip"{}>{}</span>'.format(posinfo, ESC(t.surface))
            else:
                yield t.surface
            yield "" if t.nsp else " "
        yield '</span>'

        for comment in occur.metadata.nested:
            c = ESC(comment.value).replace("\n\n", "</p>").replace("\n", "<br/>")
            yield '<div class="mwe-occur-comment">{}</div>'.format(c)


def _iter_mweoccur_and_id(mweoccurs):
    r'''Yield pairs (MWEOccur, id), where `id` is a (str, int, list[int])'''
    ret = []
    for mweoccur in mweoccurs:
        fname = os.path.basename(mweoccur.sentence.file_path)
        ret.append((mweoccur, (fname, mweoccur.sentence.nth_sent, mweoccur.indexes)))
    return sorted(ret, key=lambda x: x[1])


class VerbInfoCalculator:
    r"""Parameters:
    @type mwes: list[MWELexicalItem]
    @type sentences_to_discover_skipped: Iterable[dataalign.Sentence]
    """
    def __init__(self, lang, mwes, sentences_to_discover_skipped):
        self.lang, self.mwes = lang, mwes
        self._find_skipped(sentences_to_discover_skipped)

        self.verb2info = collections.defaultdict(VerbInfo)  # type: dict[str, VerbInfo]
        self.noun2mwes = dict(self._noun2mwes())            # type: dict[str, list[MWELexicalItem]]
        self.all_nounbased_mwes = set()                     # type: set[MWELexicalItem]

        # Update verb2info with noun-based canonics
        for noun, mwes in self.noun2mwes.items():
            merged_mwe_occurs = [mweo for m in mwes for mweo in m.mweoccurs]
            all_heads = [mweo.reordered.head.lemma_or_surface() for mweo in merged_mwe_occurs]
            most_common_verb = dataalign.most_common(all_heads)
            # Group all under "most_common_verb" (note that verb2info may then have a verb entry under another verb!)
            self.verb2info[most_common_verb.lower()].nounbased_mwes[noun.lower()].extend(mwes)
            self.all_nounbased_mwes.update(mwes)

        for verb, info in self.verb2info.items():
            for mwe_list in info.nounbased_mwes.values():
                # We sort by canonicform, with the canonicforms that have `verb` itself appearing first
                mwe_list.sort(key=lambda m: (verb not in m.canonicform, m.canonicform))

        # Update verb2info with verb-based canonics
        for mwe in self.mwes:
            if mwe not in self.all_nounbased_mwes:
                self.verb2info[mwe.canonicform[mwe.i_head].lower()].verbbased_mwes.append(mwe)
        for verbinfo in self.verb2info.values():
            verbinfo.verbbased_mwes.sort(key=lambda mwe: mwe.canonicform)


    def _noun2mwes(self):
        r'''Return a dict[str, list[MWELexicalItem]]'''
        ret = collections.defaultdict(list)
        for mwe in self.mwes:
            if mwe.i_subhead:
                ret[mwe.subhead()].append(mwe)
        # (We skip subheads where only one canonical form contains the noun)
        return {noun: mwes for (noun, mwes) \
                in ret.items() if len(mwes) > 1}


    def _find_skipped(self, sentences):
        r"""For every sentence, add Skipped MWEOccur entries to MWELexicalItems in self.mwes."""
        finder = dataalign.WindowBasedSkippedFinder(
            self.lang, self.mwes, favor_precision=False, max_gaps=MAX_GAPS)
        for mwe, mweoccur in finder.find_skipped_in(sentences):
            mwe.add_skipped_mweoccur(mweoccur)



class VerbInfo:
    r'''Attributes:
    @type  verbbased_mwes: list[MWELexicalItem]
    @param nounbased_mwes: List of verb-based MWEs

    @type  nounbased_mwes: dict[str, list[MWELexicalItem]
    @param nounbased_mwes: Map from `noun`  to noun-based MWEs (heterogeneous verbs!)
    '''
    def __init__(self):
        self.nounbased_mwes = collections.defaultdict(list)  # noun -> list[MWELexicalItem]
        self.verbbased_mwes = []  # list[MWELexicalItem]



############################################################

HTML_HEADER_1and2 = _shared_code.html_header() + """\
<style>
a:hover { cursor:pointer; }

.panel-pre-load { }  /* display at the beginning */
.panel-post-load { display: none; }
#parseme-filename-mapping { display: none; }

.sent-header { margin-bottom: 4px; font-size: 14px; font-weight: bold; }
.sent-header-no-annotations { text-decoration: line-through; }
.mweoccur-perAnnotator-id { display: none; }  /* ID used by javascript (unique for a given annotator) */
.mwe-occur-comment { border-left: 1px solid #AAA; color: #AAA; font-style:italic; margin-left: 4px; padding-left: 7px; margin-top: 6px; margin-bottom: 6px; }
.mwe-elem { font-weight: bold; }

.mweoccur-block { }
.mweoccur-collapse-button { }
.mweoccur-collapsed { color: grey; }
.mweoccur-of-annotator { margin-top: 6px; }
.mweoccur-decide-button { color: red; font-weight: bold; }
.mweoccur-decide-button.mark-decided { color: #20ab20; font-weight: normal; }
.mweoccur-errortype { }
.mweoccur-errortype.mark-decided { text-decoration: line-through; }
.mweo-annotator-name { font-weight: bold; }

p { margin-bottom: 5px; }  /* used inside mwe-occur-comment */

/* Make tooltip easier to read */
.tooltip-inner {
    font-weight: bold;
    max-width: 800px;
}
.tooltip-on-text {
    color: #555;
}
.tooltip-on-text:hover {
    color: black;
}


.mwe-label {
  background-color: #000000;  /* Default black, to catch bugs */
  cursor: default;
}
""" + dataalign.Categories.css_for_labels() + """

.show-only-if-deletable { display: none; }

.glyphicon { color: inherit; }

.global-box {
    padding: 7px;
    border-radius: 10px;
    z-index: 999;
    font-weight: bold;
    background-color: #000;
    color: #fff;
    position: fixed;
    right: 30px;
    top: 50px;
    text-align: center;
}
.global-link, .global-link:visited, .global-link:link {
    color: inherit;
    text-decoration: underline;
    cursor: pointer;
}
.global-link:hover {
    color: #ff0;
}
.global-file-upload { }
</style>


<body>

""" + _shared_code.global_box_and_warning_modal() + """

<div class="panel panel-default">
  <div class="panel-heading">1. Overview</div>
  <div class="panel-body">
      This is a graphical interface for the adjudication of two annotated files. For example:
      <ol>
      <li>For each sentence, you should see a box (gray border) with an annotated entity.</li>
      <li>You should then compare the entity annotated by annotator A1 versus A2.</li>
      <li>Click the DECIDE button to perform the adjudication.</li>
      <ul>
          <li>If you want to keep the annotation of A1 or A2, choose "A1/A2 is correct".</li>
          <li>If neither A1 nor A2 is completely right, you can use a "custom annotation".</li>
          <li>You can also "delete" an annotation or mark it as a "special case" (to be handled manually).</li>
      </ul>
      <li>Generate a list of MWEs marked for re-annotation by clicking on "Generate JSON" on the right.</li>
      <ul>
          <li>The MWEs are stored <strong>locally</strong> on your browser (not on a server). To avoid problems, generate the JSON file often.</li>
          <li>This JSON file can then be converted to a webpage that describes what needs to be modified in annotator A1's file to generate the adjudicated version. The <a data-toggle="tooltip" class="tooltip-on-text" title="lang-leaders/post-annot/jsonNotes2ReannotationWebpage.py">conversion script <span class="info-hint glyphicon glyphicon-info-sign"></span></a> can also automatically re-annotate most of the MWEs for you.</li>
      </ul>
      </ol>
  </div>
</div>

<script>
/* Enable tooltips in Overview (above) */
$('[data-toggle="tooltip"]').tooltip();
</script>


<div class="panel panel-warning panel-pre-load">
  <div class="panel-heading"><strong>Loading MWEs. Please wait.</strong></div>
</div> <!-- div panel -->


<div class="panel panel-default panel-post-load">
  <div class="panel-heading">2. MWEs for adjudication</div>
  <div class="panel-body">
"""


HTML_FOOTER = """
  </div> <!-- div panel-body -->
</div> <!-- div panel -->


<div style="display:none" id="mwe-dropdown-template">
  <span class="dropdown">
    <span class="dropdown-toggle" id="menu1" type="button" data-toggle="dropdown"></span>
    <ul class="dropdown-menu" role="menu" aria-labelledby="menu1">
      <li role="presentation" class="decide-option-A1"><a role="menuitem" tabindex="-1" href="javascript:setDecision('A1_IS_CORRECT')">A1 is correct</a></li>
      <li role="presentation" class="decide-option-A2"><a role="menuitem" tabindex="-1" href="javascript:setDecision('A2_IS_CORRECT')">A2 is correct</a></li>
      <li role="presentation"><a role="menuitem" tabindex="-1" href="javascript:setDecision('REMOVE_ANNOTATION')">Remove annotation</a></li>
      <li role="presentation" class="divider"></li>
      <li role="presentation"><a role="menuitem" tabindex="-1" href="javascript:setDecision('CUSTOM_ANNOTATION')">Custom annotation</a></li>
      <li role="presentation"><a role="menuitem" tabindex="-1" href="javascript:setDecision('SPECIAL_CASE')">Mark as special case</a></li>
      <li role="presentation" class="divider show-only-if-deletable"></li>
      <li role="presentation" class="show-only-if-deletable"><a style="color:#FB2222" role="menuitem" tabindex="-1" href="javascript:resetDecision($('#active-decide-button'))">Reset current decision</a></li>
    </ul>
  </span>
</div>


<script>
""" + _shared_code.consistency_and_adjudication_shared_javascript() + """

/** Mark glyphicon object as mark-decided */
function markDecisionButton(decisionButton, decisionText) {
    decisionButton.text('DECIDED — ' + decisionText);
    decisionButton.addClass('mark-decided');
    decisionButton.parents('.mweoccur-block').find('.mweoccur-errortype').addClass('mark-decided');
}
/** Mark glyphicon object as NOT mark-decided */
function unmarkDecisionButton(decisionButton) {
    decisionButton.text('DECIDE');
    decisionButton.removeClass('mark-decided');
    decisionButton.parents('.mweoccur-block').find('.mweoccur-errortype').removeClass('mark-decided');
}

function killDropdown() {
    g = $("#active-decide-button");
    g.removeAttr("id");
    g.siblings(".dropdown").remove();
}


function setDecision(decision_type) {
    var mweoccur_block = $("#active-decide-button").parents('.mweoccur-block');
    var categ_a1 = mweoccur_block.find('.annotator-1').find('.mwe-label').text();
    var categ_a2 = mweoccur_block.find('.annotator-2').find('.mwe-label').text();
    var mwe_a1 = mweoccur_block.find('.annotator-1').find('.mwe-elem').map(function(x) { return $(this).text(); }).toArray();
    var mwe_a2 = mweoccur_block.find('.annotator-2').find('.mwe-elem').map(function(x) { return $(this).text(); }).toArray();

    switch (decision_type) {
        case 'A1_IS_CORRECT':
            return addNote(null, {adjudication: 'A1_IS_CORRECT', type: "DO-NOTHING",
                    source_mwe: mwe_a1, source_categ: categ_a1});

        case 'A2_IS_CORRECT':
            return addNote(null, {adjudication: 'A2_IS_CORRECT', type: "RE-ANNOT",
                    source_mwe: mwe_a1, source_categ: categ_a1,
                    target_mwe: mwe_a2, target_categ: categ_a2});

        case 'REMOVE_ANNOTATION':
            return addNote(null, {adjudication: 'REMOVE_ANNOTATION', type: "DELETE-ANNOT",
                    source_mwe: mwe_a1, source_categ: categ_a1});

        case 'CUSTOM_ANNOTATION':
            return addNoteCustom(mweoccur_block, mwe_a1, mwe_a2, categ_a1, categ_a2);

        case 'SPECIAL_CASE':
            return addNoteSpecialCase(mwe_a1, categ_a1);
    }
    alert("BUG: decision_type==" + decision_type); throw 1;
}

function addNoteCustom(mweoccur_block, mwe_a1, mwe_a2, categ_a1, categ_a2) {
    var source_mwe = ((mwe_a1.length > mwe_a2.length) ? mwe_a1 : mwe_a2).join(" ");
    g = $("#active-decide-button");
    sent = $(mweoccur_block.find(".mweoccur-sentence").get()[0]);
    var reply_mwe = prompt("Type below the MWE tokens, separated by whitespace\\n(You can add/remove tokens to correct the MWE):", source_mwe);

    if (reply_mwe != null && reply_mwe.trim() != "") {
        current_sent = sent.text().trim();
        if (areTokensInside(current_sent, reply_mwe)) {
            var reply_categ = prompt("Indicate the MWE label to use", categ_a1 || categ_a2);
            if (reply_categ != null && reply_categ.trim() != "") {
                addNote(null, {adjudication: 'CUSTOM_ANNOTATION', type: "RE-ANNOT",
                    source_mwe: mwe_a1, source_categ: categ_a1,
                    target_mwe: reply_mwe.split(/ +/), target_categ: reply_categ.trim()});
            }
        } else {
            alert("ERROR: MWE sub-text " + JSON.stringify(reply_mwe) + " not found in sentence\\n(You can mark this as a \\"special case\\" if you want).");
        }
    }
    killDropdown();
}

function addNoteSpecialCase(mwe_a1, categ_a1) {
    var reply = prompt("Describe the special case below", "???");
    if (reply != null && reply.trim() != "") {
        addNote(null, {adjudication: 'SPECIAL_CASE', type: "SPECIAL-CASE",
            source_mwe: mwe_a1, source_categ: categ_a1, human_note: reply});
    }
    killDropdown();
}

/** Add note to window.parsemeData and update GUI */
function addNote(decisionButtonOrNull, annotEntry) {
    var decisionButton = decisionButtonOrNull || $("#active-decide-button");

    if (annotEntry.source_categ == '') {
        switch (annotEntry.adjudication) {
            case 'REMOVE_ANNOTATION': annotEntry.type = 'DO-NOTHING'; break;
            case 'A2_IS_CORRECT':     annotEntry.type = 'NEW-ANNOT'; break;
            case 'CUSTOM_ANNOTATION': annotEntry.type = 'NEW-ANNOT'; break;
            default: alert('BUG: bad adjudication in ' + JSON.stringify(annotEntry)); throw 1;
        }
        delete annotEntry.source_categ;
        delete annotEntry.source_mwe;
    }
    if (JSON.stringify(annotEntry.target_mwe) == JSON.stringify(annotEntry.source_mwe)) {
        delete annotEntry.target_mwe;  // remove target_mwe if it's useless
    }

    var decisionText = annotEntryToDecisionText(annotEntry);
    window.havePendingParsemeNotes = true;
    var entryID = calculateEntryID(decisionButton);
    window.parsemeData[entryID] = annotEntry;
    markDecisionButton(decisionButton, decisionText);
    updateCounter();
    killDropdown();
}

function annotEntryToDecisionText(annotEntry) {
    switch(annotEntry.adjudication) {
        case "A1_IS_CORRECT":
            return "A1 is correct";
        case "A2_IS_CORRECT":
            return "A2 is correct";
        case "REMOVE_ANNOTATION":
            return "Annotation will be removed";
        case "CUSTOM_ANNOTATION":
            var mwe = annotEntry.target_mwe || annotEntry.source_mwe;
            var mwe_text = JSON.stringify(mwe.join(" "));
            return "Will annotate " + mwe_text + " as " + annotEntry.target_categ;
        case "SPECIAL_CASE":
            return "SPECIAL-CASE: " + annotEntry.human_note;
    }
}

function calculateEntryID(decisionButton) {
    var mweoccur_block = $(decisionButton).parents('.mweoccur-block')
    var id_for_annotator_A1 = mweoccur_block.find(".annotator-1").find('.mweoccur-perAnnotator-id').text() || 'null';
    var id_for_annotator_A2 = mweoccur_block.find(".annotator-2").find('.mweoccur-perAnnotator-id').text() || 'null';
    return "MWE_KEY=[" + id_for_annotator_A1 + "," + id_for_annotator_A2 + "]";
}


function collapseMweoccur() {
    $(this).siblings(".mweoccur-hideable-part").toggle();
    $(this).toggleClass("mweoccur-collapsed");
    $(this).find(".mweoccur-glyph-up").toggle();
    $(this).find(".mweoccur-glyph-down").toggle();
}





/********* Post-load actions *******/

$(document).ready(function() {
    window.addEventListener("beforeunload", function (e) {
        try { saveStateInLocalStorage(); } catch(e) { }
        if (!window.havePendingParsemeNotes) {
            return undefined;
        } else {
            var msg = 'You should download the JSON with decisions before quitting!';
            (e || window.event).returnValue = msg; //Gecko + IE
            return msg; //Gecko + Webkit, Safari, Chrome etc.
        }
    });

    $('[data-toggle="tooltip"]').tooltip();

    $(document).click(function() {
        killDropdown();
    });

    $(".mweoccur-decide-button").click(function(e) {
        killDropdown();
        e.stopPropagation();
        $(this).prop("id", "active-decide-button");
        $(this).after($("#mwe-dropdown-template").html());

        let d = $(this).siblings(".dropdown");
        if (!$(this).parents('.mweoccur-block').find('.annotator-1').get().length != 0) {
            d.find('.decide-option-A1').hide();
        }
        if (!$(this).parents('.mweoccur-block').find('.annotator-2').get().length != 0) {
            d.find('.decide-option-A2').hide();
        }
        if ($(this).hasClass("mark-decided")) {
            d.find(".show-only-if-deletable").show();
        }

        d.find(".dropdown-toggle").dropdown("toggle");
        $(this).siblings(".dropdown").click(function(e) {
            e.stopPropagation();  /* keep it alive */
        });
    });

    $(".mweoccur-collapse-button").click(collapseMweoccur);
    $(".mweoccur-collapse-button").mouseup(function() {
        $(this).blur();  /* remove focus after mouse-up */
    });

    $('.mweoccur-collapse-button-problem-PERFECT').each(collapseMweoccur);

    updateCounter();
    $(".panel-pre-load").hide();
    $(".panel-post-load").show();

});  // finish $(document).ready


</script>
</body>
</html>
"""


#####################################################

if __name__ == "__main__":
    Main(parser.parse_args()).run()

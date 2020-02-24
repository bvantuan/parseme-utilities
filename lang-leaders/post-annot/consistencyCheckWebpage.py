#! /usr/bin/env python3

import argparse
import collections
import json
from xml.sax.saxutils import escape as ESC

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../lib"))
import dataalign

import _shared_code


DEFAULT_METH = 'WindowGap5'

parser = argparse.ArgumentParser(description="""
        Read input files and generate a webpage describing the MWEs.
        This webpage can be used to homogenize annotations.

        If multiple input files have the same basename, the webpage
        can also be used to adjudicate their annotations.
        """)
parser.add_argument("--lang", choices=sorted(dataalign.LANGS), metavar="LANG", required=True,
        help="""ID of the target language (e.g. EN, FR, PL, DE...)""")
parser.add_argument("--find-skipped", action="store_true",
        help="""Also find possibly missed MWEs, using the `Skipped` label""")
parser.add_argument("--skipped-finding-method", type=str, metavar='METH', required=False, nargs='+',
        help="""Method of finding missing MWEs (when using --find-skipped).
                One of {} (default: {}).""".format(dataalign.SKIPPED_FINDER_PATTERNS, DEFAULT_METH))
parser.add_argument("--input", type=str, nargs="+", required=True,
        help="""Path to input files (in FoLiA, CUPT, PARSEME-TSV)""")
parser.add_argument("--conllu", type=str, nargs="+",
        help="""Path to parallel input CoNLL files, if input does not contain CoNLL-U columns""")


class Main:
    def __init__(self, args):
        self.args = args
        self.mwe_mixed = []  # type: list[MWELexicalItem]
        self.mwe_nvmwe = []  # type: list[MWELexicalItem]
        self.fname2id = {fname: i+1 for (i, fname) in enumerate(self.args.input)}
        if not self.args.find_skipped and self.args.skipped_finding_method:
            exit("ERROR: Option --skipped-finding-method requires --find-skipped")
        self.args.skipped_finding_method = self.args.skipped_finding_method or [DEFAULT_METH]

    def run(self):
        self.mwe_mixed, self.mwe_nvmwe = dataalign.read_mwelexitems(
            self.iter_sentences(verbose=True))
        self.print_html()

    def iter_sentences(self, verbose):
        conllu_paths = self.args.conllu or dataalign.calculate_conllu_paths(self.args.input, warn=False) #warn=verbose) #Carlos Feb 24, 2020 - remove warning about conllu files - not necessary anymore when working on cupt directly
        return dataalign.IterAlignedFiles(self.args.lang, self.args.input, conllu_paths, keep_nvmwes=True, debug=verbose)


    def print_html(self):
        print(HTML_HEADER_1and2)
        print('<script>window.parsemeFilenameMapping = {}</script>'.format(
            json.dumps({i:f for (f,i) in self.fname2id.items()})))
        skip_sents = self.iter_sentences(False) if self.args.find_skipped else ()
        vic = VerbInfoCalculator(self.args, self.mwe_mixed, skip_sents)
        self.print_html_mwes(vic)

        print(HTML_HEADER_3)
        vic = VerbInfoCalculator(self.args, self.mwe_nvmwe, ())
        self.print_html_mwes(vic)
        print(HTML_FOOTER)


    def print_html_mwes(self, vic):
        r"""Print a big list with all MWEs."""
        print('<div class="mwe-list list-group">')

        for verb, verbinfo in sorted(vic.verb2info.items()):
            print('<div class="verb-block">')
            for mwe in verbinfo.verbbased_mwes:
                self.print_html_mwe_entry(verb, None, mwe)

            for noun, mwes in sorted(verbinfo.nounbased_mwes.items()):
                print(' <div class="noun-subblock">')
                for mwe in mwes:
                    self.print_html_mwe_entry(verb, mwe.subhead(), mwe)
                print(' </div>') # noun-subblock
            print('</div>')  # verb-block
        print('</div>')  # mwe-list


    def print_html_mwe_entry(self, head, subhead, mwe):
        r"""Print all MWE occurrences of an MWE entry as HTML; e.g.:
        | have bath [LVC (2)]
        | [LVC] I *had* a *bath* yesterday
        | [LVC] When will you *have* a *bath*?
        """
        print(' <div class="mwe-entry list-group-item">')

        # Print MWE; e.g. "kick the bucket"
        tooltip = 'Sorted by verb &quot;{}&quot'.format(ESC(head))
        if subhead: tooltip += ' and grouped by noun &quot;{}&quot;'.format(ESC(subhead))
        print('  <a class="mwe-canonic" data-toggle="tooltip" title="{title}">{canonic}</a>'.format(
                canonic=ESC(" ".join(mwe.canonicform)), title=tooltip))

        # Print labels; e.g. [VID (5) LVC(3)]
        counter = collections.Counter(o.category for o in mwe.mweoccurs)
        print('<span class="mwe-label-header">')
        print('  ' + ' '.join('<span class="label mwe-label {css_mwe_label}">{mwe} ({n})</span>' \
                .format(css_mwe_label=dataalign.Categories.css_name(mwe), mwe=ESC(mwe), n=n)
                for (mwe, n) in counter.most_common()))
        print('</span>')

        # Print examples
        print('  <div class="mwe-occurs">')
        for mweoccur, mweo_id in self._iter_mweoccur_and_id(mwe.mweoccurs):
            print('   <div class="mwe-occur">')
            # Print mwe-occur-id; e.g. ["Foo.xml", 123, [5,7,8]]
            print('   <span class="mwe-occur-id">{}</span>'.format(ESC(json.dumps(mweo_id))))
            print("".join(self._occur2html(mweoccur)))
            print('   </div>')
        print('  </div>')  # mwe-occurs
        print(' </div>')   # mwe-entry


    def _occur2html(self, occur):
        r"""Yield one MWE occurrence as HTML; e.g.:
        | [LVC] I *had* a *bath* yesterday
        | | Some comment typed by an annotator.
        """
        # Modified by Carlos on Feb 24, 2020: add sentence ID in addition to sentence number
        sent_id_kvpair = occur.sentence.get_kvpair("sent_id",occur.sentence.get_kvpair("source_sent_id",None))
        sent_pos_id = "sentence #{}{}".format(ESC(str(occur.sentence.nth_sent))," (ID: {})".format(ESC(sent_id_kvpair.value.split()[-1])) if sent_id_kvpair else "")
        # Yield a label; e.g. [LVC]  -- the label contains a tooltip
        if occur.category == "Skipped":
            file_info = 'Possible MWE seen in file &quot;{}&quot;, {}'.format(
                ESC(occur.sentence.file_path), sent_pos_id)
        else:  # occur.category != "Skipped":
            file_info = 'Annotated in file &quot;{}&quot;, {}, by &quot;{}&quot; on {}'.format(
                    ESC(occur.sentence.file_path), sent_pos_id,
                    ESC(occur.metadata.annotator or "<unknown>"), ESC(str(occur.metadata.datetime or "<unknown-date>")))
        confidence_info = '' if occur.metadata.confidence is None else ' {}%'.format(int(occur.metadata.confidence*100))
        css_mwe_label = dataalign.Categories.css_name(occur.category)
        yield '<span class="label mwe-label {css_mwe_label}"' \
              'data-toggle="tooltip" title="{title}">{mwe_label}{confidence_info}</span><span> </span>' \
              .format(css_mwe_label=css_mwe_label, title=file_info,
                      mwe_label=ESC(occur.category), confidence_info=confidence_info)

        indexes = set(occur.indexes)
        yield '<span class="mwe-occur-sentence">'
        for i, t in enumerate(occur.sentence.tokens):
            if i in indexes:
                posinfo = '' if (not t.univ_pos) else ' title="{}/{}"'.format(t.get('LEMMA', '??'), t.univ_pos)
                yield '<span class="mwe-elem" data-toggle="tooltip"{}>{}</span>'.format(posinfo, ESC(t.surface))
            else:
                yield t.surface
            yield "" if t.nsp else " "
        yield '</span>'

        yield ' <span class="mweoccur-decide-button"><span class="glyphicon glyphicon-edit"></span><span class="mwe-glyphtext"></span></span>'

        for comment in occur.metadata.nested:
            c = ESC(comment.value).replace("\n\n", "</p>").replace("\n", "<br/>")
            yield '<div class="mwe-occur-comment">{}</div>'.format(c)


    def _iter_mweoccur_and_id(self, mweoccurs):
        r'''Yield pairs (MWEOccur, id), where `id` is a (int, int, list[int])'''
        ret = []
        for mweoccur in mweoccurs:
            fname_id = self.fname2id[mweoccur.sentence.file_path]
            ret.append((mweoccur, (fname_id, mweoccur.sentence.nth_sent, mweoccur.indexes)))
        return sorted(ret, key=lambda x: x[1])


class VerbInfoCalculator:
    r"""Parameters:
    @type mwes: list[MWELexicalItem]
    @type sentences_to_discover_skipped: Iterable[dataalign.Sentence]
    """
    def __init__(self, args, mwes, sentences_to_discover_skipped):
        self.args, self.mwes = args, mwes
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
        # Create all finders right away, to find cases of misspelled finding_method's
        finders = [dataalign.skipped_finder(m, self.args.lang, self.mwes, favor_precision=False)
                   for m in self.args.skipped_finding_method]

        sentences = list(sentences)  # allow multiple iterations
        for finder in finders:
            for mwe, mweoccur in finder.find_skipped_in(sentences):
                # Add 'Skipped', but only if this MWE was not seen at this position
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

.mwe-list { }
.verb-block { margin-bottom: -1px; }  /* fix tiny Bootstrap weirdness */
.noun-subblock { margin-bottom: -1px; }  /* fix tiny Bootstrap weirdness */
.mwe-entry { }
.mwe-canonic { }
.mwe-occurs { display: none; margin-left: 10px; margin-top: 2px; margin-bottom: 10px; }
.mwe-occur { margin-top: 6px; }
.mwe-occur-id { display: none; }  /* unique ID used by javascript */
.mwe-occur-sentence { }
.mwe-occur-comment { border-left: 1px solid #AAA; color: #AAA; font-style:italic; margin-left: 4px; padding-left: 7px; margin-top: 6px; margin-bottom: 6px; }
.mwe-elem { font-weight: bold; }

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

.mweoccur-decide-button { margin-left: 5px; color: #AAA; cursor: pointer; }
.mweoccur-decide-button:hover { color: #88f; }
.mweoccur-decide-button-marked { color: #6BE24D; }
.mwe-glyphtext { margin-left: 3px; font-style: italic; }
.glyphicon { color: inherit; }
.example-glyphbox { color: #AAA; }

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
      This is a graphical interface with all the annotated MWEs and their contexts. For example:
      <ol>
      <li>Click on an MWE to expand its box (or <a href="javascript:toggleExpandAll();">expand all</a>) and see all the sentences where it was annotated.</li>
      <li>Mouse over a tag (to the left of a sentence), to see where this sentence comes from.</li>
      <li>Click on the <span class="example-glyphbox"><span style="margin-left:2px; margin-right:2px;" class="glyphicon glyphicon-edit"></span></span> icon to the right of a sentence.</li>
      <li>Mark this MWE occurrence for re-annotation (e.g. by clicking on "Annotate as LVC.full").</li>
      <ul>
          <li>If you want to add/remove tokens from the MWE, use "custom annotation".</li>
          <li>You can also mark something for non-annotation, or as a "special case".</li>
      </ul>
      <li>Generate a list of MWEs marked for re-annotation by clicking on "Generate JSON" on the right.</li>
      <ul>
          <li>The MWEs are stored <strong>locally</strong> on your browser (not on a server). To avoid problems, generate the JSON file often.</li>
          <li>This JSON file can then be <a data-toggle="tooltip" class="tooltip-on-text" title="See the script lang-leaders/post-annot/jsonNotes2ReannotationWebpage.py, which can also be used to automatically re-annotate some of the MWEs.">converted to a webpage <span class="info-hint glyphicon glyphicon-info-sign"></span></a> that describes what needs to be annotated in each file.</li>
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
  <div class="panel-heading">2. MWEs</div>
  <div class="panel-body">
"""

HTML_HEADER_3 = """
  </div> <!-- div panel-body -->
</div> <!-- div panel -->

<div class="panel panel-default panel-post-load">
  <div class="panel-heading">3. NotMWEs</div>
  <div class="panel-body">
"""


def mwe_dropdown_items(list_of_pairs):
    return '\n'.join(
            '''<li role="presentation"><a role="menuitem" tabindex="-1"'''\
            '''href="javascript:noteQ('{}')">{}</a></li>'''.format(ESC(categ), ESC(annot_info))
            for categ, annot_info in list_of_pairs)

HTML_FOOTER = """
  </div> <!-- div panel-body -->
</div> <!-- div panel -->


<div style="display:none" id="mwe-dropdown-template">
  <span class="dropdown">
    <span class="dropdown-toggle" id="menu1" type="button" data-toggle="dropdown"></span>
    <ul class="dropdown-menu" role="menu" aria-labelledby="menu1">
      """ + mwe_dropdown_items(dataalign.Categories.consistency_check_mwe_pairs()) + """
      <li role="presentation"><a role="menuitem" tabindex="-1" href="javascript:noteCustom()">Custom annotation</a></li>
      <li role="presentation" class="divider"></li>
      """ + mwe_dropdown_items(dataalign.Categories.consistency_check_nonmwe_pairs()) + """
      <li role="presentation"><a role="menuitem" tabindex="-1" href="javascript:noteSpecialCase()">Mark as special case</a></li>
      <li role="presentation" class="divider show-only-if-deletable"></li>
      <li role="presentation" class="show-only-if-deletable"><a style="color:#FB2222" role="menuitem" tabindex="-1" href="javascript:resetDecision($('#glyphbox-with-dropdown'))">Reset current decision</a></li>
    </ul>
  </span>
</div>


<script>
""" + _shared_code.consistency_and_adjudication_shared_javascript() + """

/** Mark glyphicon object as mweoccur-decide-button-marked */
function markGlyphbox(glyphbox, glyphtext) {
    eachTwinGlyphbox(glyphbox, function(twinGlyphbox) {
        g = twinGlyphbox.siblings(".mweoccur-decide-button");  // a sibling glyphbox
        g.addClass("mweoccur-decide-button-marked");
        glyph = g.find(".glyphicon");
        glyph.addClass("glyphicon-check");
        glyph.removeClass("glyphicon-edit");
        g.find(".mwe-glyphtext").text(glyphtext);
    });
}
/** Mark glyphicon object as NOT mweoccur-decide-button-marked */
function unmarkDecisionButton(glyphbox) {
    eachTwinGlyphbox(glyphbox, function(twinGlyphbox) {
        g = twinGlyphbox.siblings(".mweoccur-decide-button");  // a sibling glyphbox
        g.removeClass("mweoccur-decide-button-marked");
        glyph = g.find(".glyphicon");
        glyph.addClass("glyphicon-edit");
        glyph.removeClass("glyphicon-check");
        g.find(".mwe-glyphtext").text("");
    });
}
/** Run code for all siblings with same ID (e.g. for adjudication) */
function eachTwinGlyphbox(glyphbox, func) {
    var mwe_occur_id = glyphbox.siblings(".mwe-occur-id").text();
    glyphbox.parents(".mwe-occurs").find(".mwe-occur-id").each(function() {
        if ($(this).text() == mwe_occur_id) {
            func($(this));
        }
    });
}

function killDropdown() {
    g = $("#glyphbox-with-dropdown");
    g.removeAttr("id");
    g.siblings(".dropdown").remove();
}


function noteQ(categ) {
    addNote(null, {type: "RE-ANNOT", target_categ: categ});
}

function noteCustom() {
    g = $("#glyphbox-with-dropdown");
    sent = g.siblings(".mwe-occur-sentence");
    source_mwe = sent.find(".mwe-elem").map(function() { return $(this).text(); }).get().join(" ");
    var reply_mwe = prompt("Type below the MWE tokens, separated by whitespace\\n(You can add/remove tokens to correct the MWE):", source_mwe);

    if (reply_mwe != null && reply_mwe.trim() != "") {
        current_sent = sent.text().trim();
        if (areTokensInside(current_sent, reply_mwe)) {
            var source_categ_noPercent = g.siblings(".mwe-label").text().split(/ /)[0];
            var reply_categ = prompt("Indicate the MWE label to use", source_categ_noPercent);
            if (reply_categ != null && reply_categ.trim() != "") {
                addNote(null, {type: "RE-ANNOT", target_categ: reply_categ, target_mwe: reply_mwe.split(/ +/)});
            }
        } else {
            alert("ERROR: MWE sub-text " + JSON.stringify(reply_mwe) + " not found in sentence\\n(You can mark this as a \\"special case\\" if you want).");
        }
    }
    killDropdown();
}

function noteSpecialCase() {
    var reply = prompt("Describe the special case below", "???");
    if (reply != null && reply.trim() != "") {
        addNote(null, {type: "SPECIAL-CASE", human_note: reply});
    }
    killDropdown();
}

/** Add note to window.parsemeData and update GUI */
function addNote(glyphboxOrNull, annotEntry) {
    var gbox = glyphboxOrNull || $("#glyphbox-with-dropdown");
    annotEntry.source_categ = gbox.siblings(".mwe-label").text();
    annotEntry.source_mwe = gbox.siblings(".mwe-occur-sentence")
            .find(".mwe-elem").map(function() { return $(this).text(); }).get();
    if (JSON.stringify(annotEntry.target_mwe) == JSON.stringify(annotEntry.source_mwe))
        delete annotEntry.target_mwe;  // remove target_mwe if it's useless
    var glyphtext = annotEntryToGlyphtext(annotEntry);
    window.havePendingParsemeNotes = true;
    var mweoccur_id = calculateEntryID(gbox);
    window.parsemeData[mweoccur_id] = annotEntry;
    markGlyphbox(gbox, glyphtext);
    updateCounter();
    killDropdown();
}

function annotEntryToGlyphtext(annotEntry) {
    switch(annotEntry.type) {
        case "RE-ANNOT":
            var as_info = annotEntry.target_mwe ? JSON.stringify(annotEntry.target_mwe.join(" ")) + " as " : "";
            return as_info + annotEntry.target_categ;
        case "SPECIAL-CASE":
            return "SPECIAL-CASE: " + annotEntry.human_note;
    }
}


function calculateEntryID(decisionButton) {
    var mweoccur_id = $(decisionButton).siblings('.mwe-occur-id').text();
    return "MWE_KEY=[" + mweoccur_id + "]";
}



function toggleExpandAll() {
    window.allExpanded = !window.allExpanded;
    honorExpansionVariable();
}
function honorExpansionVariable() {
    if (window.allExpanded) {
        $(".mwe-occurs").show();
        $(".mwe-label-header").hide();
    } else {
        $(".mwe-occurs").hide();
        $(".mwe-label-header").show();
    }
}


function updateCounter() {
    $("#global-counter").text(Object.keys(window.parsemeData).length);
}



/********** Handle localStorage **************/
function saveStateInLocalStorage() {
    window.localStorage.allExpanded = window.allExpanded;
}

function loadStateFromLocalStorage() {
    try {
        allExpanded = window.localStorage.allExpanded;
    } catch(e) {
        return;  // we can't really load it
    }
    window.allExpanded = (allExpanded == "true");
    honorExpansionVariable();
}



/********* Post-load actions *******/

$(document).ready(function() {
    window.addEventListener("beforeunload", function (e) {
        try { saveStateInLocalStorage(); } catch(e) { }
        if (!window.havePendingParsemeNotes) {
            return undefined;
        } else {
            var msg = 'You must download your MWEs before quitting!';
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

        $(this).prop("id", "glyphbox-with-dropdown");
        $(this).after($("#mwe-dropdown-template").html());
        let d = $(this).siblings(".dropdown");
        d.find(".dropdown-toggle").dropdown("toggle");
        if ($(this).hasClass("mweoccur-decide-button-marked")) {
            d.find(".show-only-if-deletable").show();
        }

        $(this).siblings(".dropdown").click(function(e) {
            e.stopPropagation();  /* keep it alive */
        });
    });


    $(".mwe-canonic").click(function() {
        $(this).siblings(".mwe-occurs").toggle();
        $(this).siblings(".mwe-label-header").toggle();
    });

    loadStateFromLocalStorage();
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

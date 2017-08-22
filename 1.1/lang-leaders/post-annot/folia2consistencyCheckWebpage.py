#! /usr/bin/env python3

import argparse
import collections
import json
from xml.sax.saxutils import escape as ESC

import os, sys
sys.path.insert(0, os.path.dirname(__file__)+"/../../lib")
import dataalign


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
parser.add_argument("--output-skipped-info", action='store_true',
        help="""Output info about skipped MWEs at given path (instead of normal HTML output)""")  # XXX this is a hack
parser.add_argument("--input", type=str, nargs="+", required=True,
        help="""Path to input files (preferably in FoLiA XML format, but PARSEME TSV works too)""")
parser.add_argument("--conllu", type=str, nargs="+",
        help="""Path to parallel input CoNLL files""")

MAX_GAPS = 5


class Main:
    def __init__(self, args):
        self.args = args
        self.canonicform2mwe_mixed = collections.OrderedDict()  # type: dict[tuple[str], MWELexicalItem]
        self.canonicform2mwe_nvmwe = collections.OrderedDict()  # type: dict[tuple[str], MWELexicalItem]

    def run(self):
        cf2mweoccurs = self._canonicform2mweoccurs()
        for canonicform, mweoccurs in cf2mweoccurs.items():
            mwe = dataalign.MWELexicalItem(canonicform, mweoccurs)
            if mwe.only_non_vmwes():
                self.canonicform2mwe_nvmwe[canonicform] = mwe
            else:
                self.canonicform2mwe_mixed[canonicform] = mwe

        if self.args.output_skipped_info:  # XXX this is a hack
            global MAX_GAPS
            MAX_GAPS = 1  # XXX HACK
            skip_sents = self.iter_sentences(verbose=False)
            vic = VerbInfoCalculator(self.args.lang, self.canonicform2mwe_mixed, skip_sents)
            vic.print_skipped_info()
            exit(0)
        else:
            self.print_html()


    def _canonicform2mweoccurs(self):
        r'''Return a dict[tuple[str], list[dataalign.MWEOccur]].'''
        ret = collections.defaultdict(list)  # type: dict[tuple[str], list[dataalign.MWEOccur]]
        for sentence in self.iter_sentences():
            for mwe_occur in sentence.mwe_occurs(self.args.lang):
                canonicform = tuple(mwe_occur.reordered.mwe_canonical_form)
                ret[canonicform].append(mwe_occur)
        return ret

    def iter_sentences(self, verbose=True):
        r"""Yield all sentences in `self.args.input` (aligned, if CoNLL-U was provided)"""
        conllu_path = self.args.conllu or dataalign.calculate_conllu_paths(self.args.input, warn=verbose)
        for elem in dataalign.iter_aligned_files(self.args.input, conllu_path, keep_nvmwes=True, debug=verbose):
            if isinstance(elem, dataalign.Sentence):
                yield elem


    def print_html(self):
        print(HTML_HEADER_1and2)
        skip_sents = self.iter_sentences(False) if self.args.find_skipped else ()
        vic = VerbInfoCalculator(self.args.lang, self.canonicform2mwe_mixed, skip_sents)
        self.print_html_mwes(vic)

        print(HTML_HEADER_3)
        vic = VerbInfoCalculator(self.args.lang, self.canonicform2mwe_nvmwe, ())
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

        # Print labels; e.g. [ID (5) LVC(3)]
        counter = collections.Counter(o.category for o in mwe.mweoccurs)
        print('<span class="mwe-label-header">')
        print('  ' + ' '.join('<span class="label mwe-label mwe-label-{0}">{0} ({1})</span>' \
                .format(ESC(mwe), n) for (mwe, n) in counter.most_common()))
        print('</span>')

        # Print examples
        print('  <div class="mwe-occurs">')
        for occur in mwe.mweoccurs:
            print('   <div class="mwe-occur">')
            # Print mwe-occur-id; e.g. ["Foo.xml", 123, [5,7,8]]
            mweo_id = [os.path.basename(occur.sentence.file_path), occur.sentence.nth_sent, occur.indexes]
            print('   <span class="mwe-occur-id">{}</span>'.format(ESC(json.dumps(mweo_id))))
            print("".join(self._occur2html(occur)))
            print('   </div>')
        print('  </div>')  # mwe-occurs
        print(' </div>')   # mwe-entry


    def _occur2html(self, occur):
        r"""Yield one MWE occurrence as HTML; e.g.:
        | [LVC] I *had* a *bath* yesterday
        | | Some comment typed by an annotator.
        """
        # Yield a label; e.g. [LVC]  -- the label contains a tooltip
        if occur.category == "Skipped":
            file_info = 'Possible VMWE seen in file &quot;{}&quot;, sentence #{}'.format(
                ESC(occur.sentence.file_path), ESC(str(occur.sentence.nth_sent)))
        else:  # occur.category != "Skipped":
            file_info = 'Annotated in file &quot;{}&quot;, sentence #{}, by &quot;{}&quot; on {}'.format(
                    ESC(occur.sentence.file_path), ESC(str(occur.sentence.nth_sent)),
                    ESC(occur.annotator or "<unknown>"), ESC(str(occur.datetime or "<unknown-date>")))
        confidence_info = '' if occur.confidence is None else ' {}%'.format(int(occur.confidence*100))
        yield '<span class="label mwe-label mwe-label-{0}" data-toggle="tooltip" title="{1}">{0}{2}</span><span> </span>' \
                .format(ESC(occur.category), file_info, confidence_info)

        indexes = set(occur.indexes)
        yield '<span class="mwe-occur-sentence">'
        for i, t in enumerate(occur.sentence.tokens):
            if i in indexes:
                posinfo = '' if (not t.univ_pos) else ' title="CoNLL-U: {}/{}"'.format(t.lemma, t.univ_pos)
                yield '<span class="mwe-elem" data-toggle="tooltip"{}>{}</span>'.format(posinfo, ESC(t.surface))
            else:
                yield t.surface
            yield "" if t.nsp else " "
        yield '</span>'

        yield ' <span class="mwe-glyphbox"><span class="glyphicon glyphicon-edit"></span><span class="mwe-glyphtext"></span></span>'

        for comment in occur.comments:
            c = ESC(comment).replace("\n\n", "</p>").replace("\n", "<br/>")
            yield '<div class="mwe-occur-comment">{}</div>'.format(c)


class VerbInfoCalculator:
    r"""Parameters:
    @type canonicform2mwe: dict[tuple[str], MWELexicalItem]
    @type sentences_to_discover_skipped: Iterable[dataalign.Sentence]
    """
    def __init__(self, lang, canonicform2mwe, sentences_to_discover_skipped):
        self.lang = lang
        self.canonicform2mwe = canonicform2mwe
        self._find_skipped(sentences_to_discover_skipped)

        self.verb2info = collections.defaultdict(VerbInfo)  # type: dict[str, VerbInfo]
        self.noun2mwes = dict(self._noun2mwes())            # type: dict[str, list[MWELexicalItem]]
        self.all_nounbased_mwes = set()                     # type: set[MWELexicalItem]

        # Update verb2info with noun-based canonics
        for noun, mwes in self.noun2mwes.items():
            merged_mwe_occurs = [mweo for m in mwes for mweo in m.mweoccurs]
            all_heads = [mweo.reordered.head.lemma_or_surface() for mweo in merged_mwe_occurs]
            most_common_verb = collections.Counter(all_heads).most_common(1)[0][0]
            # Group all under "most_common_verb" (note that verb2info may then have a verb entry under another verb!)
            self.verb2info[most_common_verb.lower()].nounbased_mwes[noun.lower()].extend(mwes)
            self.all_nounbased_mwes.update(mwes)

        for verb, info in self.verb2info.items():
            for mwe_list in info.nounbased_mwes.values():
                # We sort by canonicform, with the canonicforms that have `verb` itself appearing first
                mwe_list.sort(key=lambda m: (verb not in m.canonicform, m.canonicform))

        # Update verb2info with verb-based canonics
        for canonicform, mwe in self.canonicform2mwe.items():
            if mwe not in self.all_nounbased_mwes:
                self.verb2info[canonicform[mwe.i_head].lower()].verbbased_mwes.append(mwe)
        for verbinfo in self.verb2info.values():
            verbinfo.verbbased_mwes.sort(key=lambda mwe: mwe.canonicform)


    def print_skipped_info(self):
        r'''Print TSV with "Skipped" info'''
        total, total_annotated = 0, 0
        # XXX we use "literal" instead of "skipped", because we interpret post-adjudication skipped as literal cases
        print("MWE", "n-idiomatic", "n-literal", "idiomaticity-rate", "example-literal", sep='\t')
        for canonicform, mwe in sorted(self.canonicform2mwe.items()):
            n_annotated = sum(1 for o in mwe.mweoccurs if o.category != 'Skipped')
            n = len(mwe.mweoccurs)
            total += n
            total_annotated += n_annotated

            example_skipped = '---'
            if n != n_annotated:
                example_occur = next(o for o in mwe.mweoccurs if o.category == 'Skipped')
                example_skipped = " ".join(t.surface for t in example_occur.sentence.tokens)
            print("_".join(canonicform), n, n-n_annotated, n_annotated/n, example_skipped, sep="\t")
        print("TOTAL", total, total-total_annotated, total_annotated/total, '---', sep="\t")


    def _noun2mwes(self):
        ret = collections.defaultdict(list)
        for canonicform, mwe in self.canonicform2mwe.items():
            if mwe.i_subhead:
                ret[mwe.subhead()].append(mwe)
        # (We skip subheads where only one canonical form contains the noun)
        return {noun: mwes for (noun, mwes) \
                in ret.items() if len(mwes) > 1}


    def _find_skipped(self, sentences):
        r"""For every sentence, add Skipped MWEOccur entries to MWELexicalItems in self.canonicform2mwe."""
        finder = dataalign.DependencyBasedSkippedFinder(self.lang, self.canonicform2mwe.values())
        for mwe, mweoccur in finder.find_skipped_in(sentences):
            mwe.add_skipped_mweoccur(mweoccur)

        #finder = dataalign.WindowBasedSkippedFinder(self.lang, self.canonicform2mwe.values(), MAX_GAPS)
        #for mwe, mweoccur in finder.find_skipped_in(sentences):
        #    mwe.add_skipped_mweoccur(mweoccur)


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

HTML_HEADER_1and2 = """\
<html>
<meta charset="UTF-8">
<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css">
<script src="https://ajax.googleapis.com/ajax/libs/jquery/3.1.1/jquery.min.js"></script>
<script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/js/bootstrap.min.js"></script>

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

.mwe-label { cursor: default; }
.mwe-label-LVC { background-color: #9AA6FF; }
.mwe-label-ID { background-color: #FF6AFF; }
.mwe-label-OTH { background-color: #EF4AEF; }
.mwe-label-VPC { background-color: #CC8833; }
.mwe-label-IReflV { background-color: #FFB138; }
.mwe-label-NonVMWE { background-color: #DCC8C8; }
.mwe-label-Skipped { background-color: #DDDDDD; }

.show-only-if-deletable { display: none; }

.mwe-glyphbox { margin-left: 5px; color: #AAA; cursor: pointer; }
.mwe-glyphbox:hover { color: #88f; }
.mwe-glyphbox-marked { color: #6BE24D; }
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

<div class="global-box">
    Notes added: <span id="global-counter">0</span>

    <div><a class="global-link" href="javascript:downloadData()">Generate JSON</a></div>

    <label for="file-upload" class="global-link global-file-input">Load JSON file</label>
    <input style="display:none" id="file-upload" type="file" onchange="javascript:uploadData(this.files[0])"/>
</div>

<div class="panel panel-default">
  <div class="panel-heading">1. Overview</div>
  <div class="panel-body">
      This is a graphical interface with all the annotated VMWEs and their contexts. For example:
      <ol>
      <li>Click on a VMWE to expand its box (or <a href="javascript:toggleExpandAll();">expand all</a>) and see all the sentences where it was annotated.</li>
      <li>Mouse over a tag (to the left of a sentence), to see where this sentence comes from.</li>
      <li>Click on the <span class="example-glyphbox"><span style="margin-left:2px; margin-right:2px;" class="glyphicon glyphicon-edit"></span></span> icon to the right of a sentence.</li>
      <li>Mark this VMWE occurrence for re-annotation (e.g. by clicking on "Annotate as LVC").</li>
      <ul>
          <li>If you want to add/remove tokens from the MWE, use "custom annotation".</li>
          <li>You can also mark something for non-annotation, or as a "special case".</li>
      </ul>
      <li>Generate a list of VMWEs marked for re-annotation by clicking on "Generate JSON" on the right.</li>
      <ul>
          <li>The VMWEs are stored <strong>locally</strong> on your browser (not on a server). To avoid problems, generate the JSON file often.</li>
          <li>This JSON file can then be <a data-toggle="tooltip" class="tooltip-on-text" title="See the script bin/jsonNotes2humanNotes_webpage.py, which can also be used to automatically re-annotate some of the MWEs.">converted to a webpage <span class="info-hint glyphicon glyphicon-info-sign"></span></a> that describes what needs to be annotated in each file.</li>
      </ul>
      </ol>
  </div>
</div>

<script>
/* Enable tooltips in Overview (above) */
$('[data-toggle="tooltip"]').tooltip();
</script>


<div class="panel panel-warning panel-pre-load">
  <div class="panel-heading"><strong>Loading VMWEs. Please wait.</strong></div>
</div> <!-- div panel -->


<div class="panel panel-default panel-post-load">
  <div class="panel-heading">2. VMWEs</div>
  <div class="panel-body">
"""

HTML_HEADER_3 = """
  </div> <!-- div panel-body -->
</div> <!-- div panel -->

<div class="panel panel-default panel-post-load">
  <div class="panel-heading">3. NonVMWEs</div>
  <div class="panel-body">
"""


HTML_FOOTER = """
  </div> <!-- div panel-body -->
</div> <!-- div panel -->


<div style="display:none" id="mwe-dropdown-template">
  <span class="dropdown">
    <span class="dropdown-toggle" id="menu1" type="button" data-toggle="dropdown"></span>
    <ul class="dropdown-menu" role="menu" aria-labelledby="menu1">
      <li role="presentation"><a role="menuitem" tabindex="-1" href="javascript:noteQ('ID')">Annotate as ID</a></li>
      <li role="presentation"><a role="menuitem" tabindex="-1" href="javascript:noteQ('IReflV')">Annotate as IReflV</a></li>
      <li role="presentation"><a role="menuitem" tabindex="-1" href="javascript:noteQ('LVC')">Annotate as LVC</a></li>
      <li role="presentation"><a role="menuitem" tabindex="-1" href="javascript:noteQ('OTH')">Annotate as OTH</a></li>
      <li role="presentation"><a role="menuitem" tabindex="-1" href="javascript:noteQ('VPC')">Annotate as VPC</a></li>
      <li role="presentation"><a role="menuitem" tabindex="-1" href="javascript:noteCustom()">Custom annotation</a></li>
      <li role="presentation" class="divider"></li>
      <li role="presentation"><a role="menuitem" tabindex="-1" href="javascript:noteQ('NonVMWE')">Mark as Non-VMWE</a></li>
      <li role="presentation"><a role="menuitem" tabindex="-1" href="javascript:noteSpecialCase()">Mark as special case</a></li>
      <li role="presentation" class="divider show-only-if-deletable"></li>
      <li role="presentation" class="show-only-if-deletable"><a style="color:#FB2222" role="menuitem" tabindex="-1" href="javascript:deleteNote()">Delete current note</a></li>
    </ul>
  </span>
</div>


<script>
window.parsemeData = {};
window.havePendingParsemeNotes = false;


/** Mark glyphicon object as mwe-glyphbox-marked */
function markGlyphbox(glyphbox, glyphtext) {
    eachTwinGlyphbox(glyphbox, function(twinGlyphbox) {
        g = twinGlyphbox.siblings(".mwe-glyphbox");  // a sibling glyphbox
        g.addClass("mwe-glyphbox-marked");
        glyph = g.find(".glyphicon");
        glyph.addClass("glyphicon-check");
        glyph.removeClass("glyphicon-edit");
        g.find(".mwe-glyphtext").text(glyphtext);
    });
}
/** Mark glyphicon object as NOT mwe-glyphbox-marked */
function unmarkGlyphbox(glyphbox) {
    eachTwinGlyphbox(glyphbox, function(twinGlyphbox) {
        g = twinGlyphbox.siblings(".mwe-glyphbox");  // a sibling glyphbox
        g.removeClass("mwe-glyphbox-marked");
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


function escapeRegExp(str) {
    return str.replace(/[\-\[\]\/\{\}\(\)\*\+\?\.\\\^\$\|]/g, "\\$&");
}
/** Return whether the space-separated tokens in innerText appears inside fullText */
function areTokensInside(fullText, innerText) {
    var regex = escapeRegExp(innerText).replace(/ +/g, ".*");
    return new RegExp(regex, "g").test(fullText);
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
            var reply_categ = prompt("Indicate the VMWE label to use", source_categ_noPercent);
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
    var mweoccur_id = "MODIF:" + gbox.siblings(".mwe-occur-id").text();
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

/** Remove note from window.parsemeData and update GUI */
function deleteNote(glyphboxOrNull) {
    var gbox = glyphboxOrNull || $("#glyphbox-with-dropdown");
    window.havePendingParsemeNotes = true;
    var mweoccur_id = "MODIF:" + gbox.siblings(".mwe-occur-id").text();
    delete window.parsemeData[mweoccur_id];
    unmarkGlyphbox(gbox);
    updateCounter();
    killDropdown();
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


function downloadData() {
    var json = JSON.stringify(window.parsemeData, null, 2);
    var blob = new Blob([json], {type: "application/json"});
    var url  = URL.createObjectURL(blob);
    saveAs(url, "ParsemeNotes.json");
    window.havePendingParsemeNotes = false;  // assume they have downloaded it...
}
function saveAs(uri, filename) {
    var link = document.createElement('a');
    if (typeof link.download === 'string') {
        document.body.appendChild(link); // Firefox requires the link to be in the body
        link.download = filename;
        link.href = uri;
        link.click();
        document.body.removeChild(link); // remove the link when done
    } else {
        location.replace(uri);
    }
}

function uploadData(filePath) {
    var reader = new FileReader();
    reader.onload = function() {
      var havePending = window.havePendingParsemeNotes;
      var data = JSON.parse(reader.result);
      $(".mwe-occur-id").each(function() {
          var mweoccur_id = "MODIF:" + $(this).text();
          if (data[mweoccur_id]) {
              var annotEntry = data[mweoccur_id];
              if (annotEntry.to) {
                // 2016-12-19 hack to rename `to` => `target_categ`
                // (this can be removed in the future)
                annotEntry.target_categ = annotEntry.to;
                delete annotEntry.to;
                delete annotEntry.from;
              }
              if (annotEntry.text) {
                // 2016-12-19 hack to rename `text` => `human_note`
                // (this can be removed in the future)
                annotEntry.human_note = annotEntry.text;
                delete annotEntry.text;
              }
              glyphbox = $(this).siblings(".mwe-glyphbox");
              addNote(glyphbox, annotEntry);
          }
      });
      window.havePendingParsemeNotes = havePending;
    };
    reader.readAsText(filePath);
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
            var msg = 'You must download your VMWEs before quitting!';
            (e || window.event).returnValue = msg; //Gecko + IE
            return msg; //Gecko + Webkit, Safari, Chrome etc.
        }
    });

    $('[data-toggle="tooltip"]').tooltip();

    $(document).click(function() {
        killDropdown();
    });

    $(".mwe-glyphbox").click(function(e) {
        killDropdown();
        e.stopPropagation();

        $(this).prop("id", "glyphbox-with-dropdown");
        $(this).after($("#mwe-dropdown-template").html());
        let d = $(this).siblings(".dropdown");
        d.find(".dropdown-toggle").dropdown("toggle");
        if ($(this).hasClass("mwe-glyphbox-marked")) {
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

#! /usr/bin/env python3

import argparse
import collections
import dataalign
import json
import os
from xml.sax.saxutils import escape as ESC

parser = argparse.ArgumentParser(description="""
        Read input files and generate a webpage describing the MWEs.
        This webpage can be used to homogenize annotations.

        If multiple input files have the same basename, the webpage
        can also be used to adjudicate their annotations.
        """)
parser.add_argument("--lang", choices=sorted(dataalign.LANGS), metavar="LANG", required=True,
        help="""ID of the target language (e.g. EN, FR, PL, DE...)""")
parser.add_argument("--input", type=str, nargs="+", required=True,
        help="""Path to input files (preferably in FoLiA XML format, but PARSEME TSV works too)""")
parser.add_argument("--conllu", type=str, nargs="+",
        help="""Path to parallel input CoNLL files""")


class Main:
    def __init__(self, args):
        self.args = args
        self.canonic2occurs = collections.defaultdict(list)  # canonicized_tuple -> [MWEOccur]
        self.del_canonic2occurs = collections.defaultdict(list)

    def run(self):
        conllu_path = self.args.conllu or dataalign.calculate_conllu_paths(self.args.input)
        for elem in dataalign.iter_aligned_files(self.args.input, conllu_path, debug=True):
            if isinstance(elem, dataalign.Sentence):
                for mwe_occur in elem.mwe_occurs(self.args.lang):
                    canonic = tuple(mwe_occur.reordered.mwe_canonical_form)
                    self.canonic2occurs[canonic].append(mwe_occur)
        self.delete_purely_nonvmwe_canonics()
        self.print_html()


    def delete_purely_nonvmwe_canonics(self):
        r"""Remove entries that are fully NonVMWE from `self.canonic2occurs`."""
        for canonic, mwe_occurs in list(self.canonic2occurs.items()):
            if all((o.category=="NonVMWE" and o.confidence is None) for o in mwe_occurs):
                self.del_canonic2occurs[canonic] = self.canonic2occurs.pop(canonic)


    def print_html(self):
        print(HTML_HEADER_1and2)
        self.print_html_mwes(self.canonic2occurs)
        print(HTML_HEADER_3)
        self.print_html_mwes(self.del_canonic2occurs)
        print(HTML_FOOTER)


    def print_html_mwes(self, canonic2occurs):
        r"""Print a big list with all MWEs."""
        print('<div class="mwe-list list-group">')
        vic = VerbInfoCalculator(canonic2occurs)

        for verb, verbinfo in sorted(vic.verb2info.items()):
            print('<div class="verb-block">')
            for canonic in verbinfo.verbbased_canonics:
                self.print_html_mwe_entry(canonic, verb, None, canonic2occurs[canonic])

            print(' <div class="noun-subblock">')
            for canonic in verbinfo.nounbased_canonics:
                i = vic.canonic2isubhead[canonic]
                self.print_html_mwe_entry(canonic, verb, canonic[i], canonic2occurs[canonic])
            print(' </div>') # noun-subblock
            print('</div>')  # verb-block
        print('</div>')  # mwe-list


    def print_html_mwe_entry(self, canonic, head, subhead, occurs):
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
                canonic=ESC(" ".join(canonic)), title=tooltip))

        # Print labels; e.g. [ID (5) LVC(3)]
        counter = collections.Counter(o.category for o in occurs)
        print('<span class="mwe-label-header">')
        print('  ' + ' '.join('<span class="label mwe-label mwe-label-{0}">{0} ({1})</span>' \
                .format(ESC(mwe), n) for (mwe, n) in counter.most_common()))
        print('</span>')

        # Print examples
        print('  <div class="mwe-occurs">')
        for occur in occurs:
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
    def __init__(self, canonic2occurs):
        self.canonic2occurs = canonic2occurs
        self.canonic2ihead = dict(self._all_canonics())
        self.noun2canonic2isubhead = dict(self._nounbased_canonics())
        self.canonic2isubhead = {c: i for c2i in
                self.noun2canonic2isubhead.values() for (c,i) in c2i.items()}
        self.verb2info = collections.defaultdict(VerbInfo)

        # Update verb2info with verb-based canonics
        for noun, canonic2isubhead in self.noun2canonic2isubhead.items():
            canonics = canonic2isubhead.keys()
            for c in canonics: self.canonic2ihead.pop(c)  # leave only the verb-based ones there
            merged_mwe_occurs = [mweo for c in canonics for mweo in self.canonic2occurs[c]]
            all_heads = [mweo.reordered.head.lemma_or_surface() for mweo in merged_mwe_occurs]
            most_common_verb = collections.Counter(all_heads).most_common(1)[0][0]
            canonics_a = list(sorted(c for c in canonics if most_common_verb in c))
            canonics_b = list(sorted(c for c in canonics if most_common_verb not in c))
            self.verb2info[most_common_verb].nounbased_canonics.extend(canonics_a + canonics_b)

        # Update verb2info with verb-based canonics
        for canonic, i_head in self.canonic2ihead.items():
            self.verb2info[canonic[i_head]].verbbased_canonics.append(canonic)
        for verbinfo in self.verb2info.values():
            verbinfo.verbbased_canonics.sort()


    def _all_canonics(self):
        r"""Yield (canonical_form, i_head) for all canonical forms."""
        for canonic, mwe_occurs in self.canonic2occurs.items():
            # Find most common `i_head` attribution in all occurs
            i_head = collections.Counter(m.reordered.i_head for m in mwe_occurs).most_common(1)[0][0]
            yield canonic, i_head


    def _nounbased_canonics(self):
        r"""Yield (canonical_form, i_subhead) for all
        canonical forms that are centered on a noun.
        """
        noun2canonic2isubhead = collections.defaultdict(dict)
        for canonic, mwe_occurs in self.canonic2occurs.items():
            nounbased_mweos = [m for m in mwe_occurs if m.reordered.subhead]
            if nounbased_mweos:
                m = nounbased_mweos[0]
                L = m.reordered.subhead.lemma_or_surface()
                noun2canonic2isubhead[L][canonic] = m.reordered.i_subhead

        # (We skip subheads where only one canonical form contains the noun)
        return {noun: canonic2isubhead for (noun, canonic2isubhead) \
                in noun2canonic2isubhead.items() if len(canonic2isubhead) > 1}


class VerbInfo:
    def __init__(self):
        self.nounbased_canonics = []
        self.verbbased_canonics = []



############################################################

HTML_HEADER_1and2 = """\
<html>
<meta charset="UTF-8">
<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css">
<script src="https://ajax.googleapis.com/ajax/libs/jquery/3.1.1/jquery.min.js"></script>
<script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/js/bootstrap.min.js"></script>

<style>
a:hover { cursor:pointer; }

.mwe-list { }
.verb-block { }
.noun-subblock { }
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

.mwe-label { cursor: default; }
.mwe-label-LVC { background-color: #9AA6FF; }
.mwe-label-ID { background-color: #FF6AFF; }
.mwe-label-OTH { background-color: #EF4AEF; }
.mwe-label-VPC { background-color: #CC8833; }
.mwe-label-IReflV { background-color: #FFB138; }
.mwe-label-NonVMWE { background-color: #DCC8C8; }
.mwe-label-Skipped { background-color: #DDDDDD; }

.mwe-glyphtext { margin-left: 3px; font-style: italic; }
.mwe-glyphbox { margin-left: 5px; color: #AAA; cursor: pointer; }
.mwe-glyphbox:hover { color: #88f; }
.glyphicon { color: inherit; }
.glyph-marked { color: #6BE24D; }
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
      <li>Click on the <span class="example-glyphbox"><span style="margin-left:2px; margin-right:2px;" class="glyphicon glyphicon-edit"></span></span> icon close to one of these sentences.</li>
      <li>Mark this VMWE occurrence for re-annotation (e.g. by clicking on "Annotate as LVC").</li>
      <ul>
          <li>You can also mark something for non-annotation or as a "special case".</li>
          <li>In the future, notes that are not "special case" may be automatically re-annotated.</li>
      </ul>
      <li>Generate a list of VMWEs marked for re-annotation by clicking on "Generate JSON" on the right.</li>
      <ul>
          <li>The VMWEs are stored <strong>locally</strong> on your browser (not on a server). To avoid problems, generate the JSON file often.</li>
      </ul>
      </ol>
  </div>
</div>


<div class="panel panel-default">
  <div class="panel-heading">2. VMWEs</div>
  <div class="panel-body">
"""

HTML_HEADER_3 = """
  </div> <!-- div panel-body -->
</div> <!-- div panel -->

<div class="panel panel-default">
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
      <li role="presentation" class="divider"></li>
      <li role="presentation"><a role="menuitem" tabindex="-1" href="javascript:noteQ('NonVMWE')">Do not annotate</a></li>
      <li role="presentation"><a role="menuitem" tabindex="-1" href="javascript:noteCustom()">Mark as special case</a></li>
    </ul>
  </span>
</div>


<script>
window.parsemeData = {};
window.havePendingParsemeNotes = false;

window.onload = function() {
    window.addEventListener("beforeunload", function (e) {
        if (!window.havePendingParsemeNotes) {
            return undefined;
        } else {
            var msg = 'You must download your VMWEs before quitting!';
            (e || window.event).returnValue = msg; //Gecko + IE
            return msg; //Gecko + Webkit, Safari, Chrome etc.
        }
    });
}


/* Mark glyphicon object as glyph-marked */
function markGlyphbox(glyphbox, glyphtext) {
    // Extra convoluted code to find all siblings with same ID and mark them all
    var mwe_occur_id = glyphbox.siblings(".mwe-occur-id").text();
    glyphbox.parents(".mwe-occurs").find(".mwe-occur-id").each(function() {
        if ($(this).text() == mwe_occur_id) {
            g = $(this).siblings(".mwe-glyphbox");  // a sibling glyphbox
            glyph = g.find(".glyphicon");
            g.addClass("glyph-marked");
            glyph.addClass("glyphicon-check");
            glyph.removeClass("glyphicon-edit");
            g.find(".mwe-glyphtext").text(glyphtext);
        }
    });
}

function killDropdown() {
    g = $("#glyphbox-with-dropdown");
    g.removeAttr("id");
    g.siblings(".dropdown").remove();
}
$(document).click(function() {
    killDropdown();
});


function noteQ(categ) {
    var g = $("#glyphbox-with-dropdown");
    var prev_categ = g.siblings(".mwe-label").text();
    addNote(null, {type: "RE-ANNOT", from: prev_categ, to: categ});
}
function noteCustom() {
    // TODO: collect txt from user using a popover with an input field and
    // an [OK] button. When the button is clicked, it calls addNote
    // with the content of the input field.
    var reply = prompt("Describe the special case below", "???");
    if (reply != null) {
        addNote(null, {type: "SPECIAL-CASE", text: reply});
    } else {
        killDropdown();
    }
}
function addNote(glyphboxOrNull, annotEntry) {
    var glyphtext = annotEntryToGlyphtext(annotEntry);
    var gbox = glyphboxOrNull || $("#glyphbox-with-dropdown");
    window.havePendingParsemeNotes = true;
    var mweoccur_id = "MODIF:" + gbox.siblings(".mwe-occur-id").text();
    window.parsemeData[mweoccur_id] = annotEntry;
    markGlyphbox(gbox, glyphtext);
    updateCounter();
    killDropdown();
}
function annotEntryToGlyphtext(annotEntry) {
    switch(annotEntry.type) {
        case "RE-ANNOT": return annotEntry.to;
        case "SPECIAL-CASE": return "SPECIAL-CASE: " + annotEntry.text;
    }
}


$(".mwe-glyphbox").click(function(e) {
    killDropdown();
    e.stopPropagation();

    $(this).prop("id", "glyphbox-with-dropdown");
    $(this).after($("#mwe-dropdown-template").html());
    let d = $(this).siblings(".dropdown");
    d.find(".dropdown-toggle").dropdown("toggle");

    $(this).siblings(".dropdown").click(function(e) {
        e.stopPropagation();  /* keep it alive */
    });
});


$(".mwe-canonic").click(function() {
    $(this).siblings(".mwe-occurs").toggle();
    $(this).siblings(".mwe-label-header").toggle();
});

function toggleExpandAll() {
    if (window.allExpanded) {
        $(".mwe-occurs").hide();
        window.allExpanded = false;
    } else {
        $(".mwe-occurs").show();
        window.allExpanded = true;
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
              var annotData = data[mweoccur_id];
              glyphbox = $(this).siblings(".mwe-glyphbox");
              addNote(glyphbox, annotData);
          }
      });
      window.havePendingParsemeNotes = havePending;
    };
    reader.readAsText(filePath);
}


function updateCounter() {
    $("#global-counter").text(Object.keys(window.parsemeData).length);
}
updateCounter();


$('[data-toggle="tooltip"]').tooltip();
</script>
</body>
</html>
"""


#####################################################

if __name__ == "__main__":
    Main(parser.parse_args()).run()

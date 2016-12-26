#! /usr/bin/env python3

import argparse
import collections
import datetime
import json
import os
import re
import subprocess
import sys

parser = argparse.ArgumentParser(description="""
        Read JSON notes and output a pretty page that indicates what should be annotated.""")
parser.add_argument("--json-input", metavar="ParsemeNotesJson", type=argparse.FileType('r'), required=True,
        help="""Path to a JSON file with adjudication/homogenization information""")
parser.add_argument("--xml-input", nargs="+",
        help="""Path to input FoLiA XML files (annotation downloaded from FLAT).
        If this option is specified, only the required manual corrections are shown.""")

parser.add_argument("--generate-xml", action="store_true",
        help="""Output automatically corrected XML in "./AfterAutoAdjudic" directory.""")
parser.add_argument("--only-special", action='store_true',
        help="""Show only corrections corresponding to "special cases".""")


KNOWN_CATEGS = "ID IReflV LVC OTH VPC NonVMWE".split()
ISOTIME = datetime.datetime.now().isoformat()

class AnnotEntry(collections.namedtuple('AnnotEntry', 'filename sent_id indexes json_data')):
    def warn(self, msg, *args, **kwargs):
        r"""Assign self._bad with a warning message (to show in output)"""
        self._bad = msg.format(*args, J=self.json_data, **kwargs)
        print("{}:#{}: WARNING:".format(self.filename, self.sent_id), self._bad, file=sys.stderr)
        return False


class Main(object):
    def __init__(self, args):
        self.args = args
        self.fname2annots = collections.defaultdict(list)  # filename -> List[AnnotEntry]
        if self.args.only_special and self.args.xml_input:
            print("WARNING: did you really mean to specify both " \
                    "--xml-input and --only-special?", file=sys.stderr)
        if self.args.generate_xml and not self.args.xml_input:
            raise Exception("Option --xml-input required if --generate-xml is specified")

        self.fname2foliadoc = {}
        if self.args.xml_input:
            from pynlpl.formats import folia
            self.fname2foliadoc = {os.path.basename(fname):
                    folia.Document(file=fname) for fname in self.args.xml_input}
            self.folia = folia

    def run(self):
        self.load_fname2annots()
        print(HTML_HEADER)
        for fname, annots in sorted(self.fname2annots.items()):
            self.print_panel(fname, annots)
            if fname in self.fname2foliadoc:
                subprocess.check_call("mkdir -p ./AfterAutoAdjudic", shell=True)
                output = "./AfterAutoAdjudic/" + os.path.basename(fname)
                self.fname2foliadoc[fname].save(output)
                print("INFO: saving to \"{}\"".format(output), file=sys.stderr)
        print(HTML_FOOTER)

    def print_panel(self, fname, annots):
        manual, auto = self.split_corrections(fname, annots)
        print('<div class="panel panel-default file-block">')
        print('<div class="panel-heading filename">{} <a class="show-link">' \
                '[show {} automatically annotated]</a></div>'.format(fname, len(auto)))
        print('<div class="panel-body">')
        print('<div class="list-group">')
        try:
            for annot in sorted(manual):
                self.print_annot(annot, True)
            for annot in sorted(auto):
                self.print_annot(annot, False)
        except Exception:
            import traceback
            traceback.print_exc()
            mwe = " ".join(str(x) for x in annot.json_data.get("source_mwe", annot.indexes))
            print(annot.json_data, file=sys.stderr)
            exit("===============\nERROR when processing JSON file for \"{}\", " \
                    "sentence #{}, MWE \"{}\"".format(fname, annot.sent_id, mwe))
        print('</div>')  # list-group
        print('</div>')  # panel-body
        print('</div>')  # file-block


    def print_annot(self, annot_entry, is_manual):
        if is_manual:
            right_span = ""
            if hasattr(annot_entry, "_bad"):
                right_span = '<span class="warn-txt">{}</span>'.format(annot_entry._bad)
            print('<div class="list-group-item annot-entry wtd-list-manual">{}{}</div>'.format(
                    right_span, "".join(self.annot2str(annot_entry, "what-to-do-manual"))))
        else:
            right_span = '<span class="auto-txt">Automatically annotated</span>'
            print('<div class="list-group-item annot-entry wtd-list-auto">{}{}</div>'.format(
                    right_span, "".join(self.annot2str(annot_entry, "what-to-do-auto"))))


    def annot2str(self, annot_entry, wtd_class):
        J = annot_entry.json_data
        yield '<span class="label label-default sent-id">#{}</span>'.format(annot_entry.sent_id)
        yield '<span class="source-mwe">{}</span>'.format(" ".join(J["source_mwe"]))
        if annot_entry.json_data["type"] == "SPECIAL-CASE":
            yield '<div class="{} wtd-special">{}</div>'.format(wtd_class, J["human_note"])
        elif annot_entry.json_data["type"] == "RE-ANNOT":
            if "target_mwe" in J:
                yield '<div class="{} wtd-reannot">Re-annotate tokens: &quot;{}&quot; &rarr; &quot;{}&quot;</div>' \
                        .format(wtd_class, " ".join(J["source_mwe"]), " ".join(J["target_mwe"]))
            yield '<div class="{} wtd-reannot">Re-annotate category: {} &rarr; {}</div>' \
                    .format(wtd_class, J["source_categ"], J["target_categ"])

    def load_fname2annots(self):
        J = json.load(self.args.json_input)
        for coded_key, json_data in J.items():
            if coded_key.startswith("MODIF:"):
                # Decode the key (it's a JSON inside a JSON string)
                key = json.loads(re.sub("^MODIF:", "", coded_key))
                key[2] = tuple(key[2])  # json list becomes python list...
                annot_entry = AnnotEntry(*(key + [json_data]))
                self.fname2annots[annot_entry.filename].append(annot_entry)
            else:
                raise Exception("Unknown coded-key: " + coded_key)

    def split_corrections(self, fname, annots):
        r"""Split `annots` in two lists: (manual_annots, auto_annots)"""
        indexinfo2entity = dict(self.make_indexinfo2entity(fname))
        manual, auto = [], []
        for annot in sorted(annots):
            to_ignore = self.args.only_special and annot.json_data["type"] != "SPECIAL-CASE"
            if (indexinfo2entity and self.folia_modify(indexinfo2entity, annot)) or to_ignore:
                auto.append(annot)
            else:
                manual.append(annot)
        return manual, auto

    def make_indexinfo2entity(self, fname):
        if fname in self.fname2foliadoc:
            foliadoc = self.fname2foliadoc[fname]
            for sent_id, sentence in enumerate(foliadoc.sentences(), 1):
                for entity in sentence.select(self.folia.Entity):
                    indexes = tuple(int(w.id.rsplit(".", 1)[-1])-1 for w in entity.wrefs())
                    yield (sent_id, indexes), entity

    def folia_modify(self, indexinfo2entity, annot):
        r"""Return True iff we can modify the FoliA data."""
        if annot.json_data["type"] == "RE-ANNOT":
            try:
                entity = indexinfo2entity[(annot.sent_id, annot.indexes)]
            except KeyError:
                return annot.warn("MWE not found in input XML")

            if entity.cls != annot.json_data["source_categ"].split()[0]:
                return annot.warn("XML has unexpected category {}", entity.cls)
            if annot.json_data["target_categ"] not in KNOWN_CATEGS:
                return annot.warn("Target VMWE category is either language-specific or a typo")

            folia_mwe = [w.text() for w in entity.wrefs()]
            if folia_mwe != annot.json_data["source_mwe"]:
                return annot.warn("MWE mismatch: JSON {J[source_mwe]} vs XML {}", folia_mwe)

            if "target_mwe" in annot.json_data:
                target_mwe = annot.json_data["target_mwe"]
                kept_words = [w for w in target_mwe if w in folia_mwe]
                if not kept_words:
                    return annot.warn("Unable to automatically annotate, all words changed")
                mid = target_mwe.index(kept_words[0])
                left, right = target_mwe[:mid], target_mwe[mid+1:]
                sentence = list(entity.parent.parent.words())
                return annot.warn("Automatic token re-annotation not yet implemented")

            entity.cls = annot.json_data["target_categ"]
            entity.append(self.folia.Comment, annotatortype="auto", datetime=ISOTIME,
                    value="[AUTO RE-ANNOT CATEGORY: {} → {}]".format(
                    annot.json_data["source_categ"], annot.json_data["target_categ"]))
            return True
        return False


HTML_HEADER = '''
<html>
<body>
<meta charset="UTF-8">
<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css">
<script src="https://ajax.googleapis.com/ajax/libs/jquery/3.1.1/jquery.min.js"></script>
<script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/js/bootstrap.min.js"></script>

<style>
.source-mwe {
    padding-left: 5px;
    font-weight: bold;
}
.what-to-do-auto { color: #E3A933; }
.what-to-do-manual { color: #19BF26; }
.wtd-list-auto { display: none; background-color: #FDFDFD; }
.wtd-list-manual { }

.list-group {
    margin-bottom: 0px;
}
.show-link {
    cursor: pointer;
    float: right;
}

.auto-txt { float: right; color: #ccc3ab; }
.warn-txt { float: right; color: #ccc3ab; }

</style>

<div class="panel panel-default">
<div class="panel-heading">Overview</div>
<div class="panel-body">
  This webpage was built from a JSON file describing re-annotations. In order to re-annotate a file:
  <ol>
  <li>Open the FLAT interface and start editing the XML file you want to re-annotate.</li>
  <li>Look for the name of this XML file in the list of files below.</li>
  <li>For each MWE, in the order that they are displayed here:</li>
  <ul>
      <li>Re-annotate this <strong>MWE</strong> in FLAT according to the <span class="what-to-do-manual">instructions</span>.</li>
      <li>(Note: There is an indication of the <span class="label label-default sent-id">sentence number</span> for each MWE).</li>
  </ul>
  </ol>
</div>
</div>
'''

HTML_FOOTER = '''
<script>
$(".show-link").click(function() {
    $(this).parents(".file-block").find(".wtd-list-auto").toggle();
});
</script>


</body>
</html>
'''


#####################################################

if __name__ == "__main__":
    Main(parser.parse_args()).run()

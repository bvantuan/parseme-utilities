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
    r"""`sent_id` is 0-based, `indexes` is 0-based."""
    def err(self, msg, *args, **kwargs):
        r"""Assign self._bad with a warning message (to show in output)"""
        self._bad = msg.format(*args, J=self.json_data, **kwargs)
        return NoteError(msg=self._bad, fname=self.filename, sent_id=self.sent_id)


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
        print(HTML_FOOTER)

        if self.args.generate_xml:
            subprocess.check_call("rm -rf ./AfterAutoAdjudic", shell=True)
            subprocess.check_call("mkdir -p ./AfterAutoAdjudic", shell=True)
            for fname, foliadoc in sorted(self.fname2foliadoc.items()):
                output = "./AfterAutoAdjudic/" + os.path.basename(fname)
                print("INFO: saving to \"{}\"".format(output), file=sys.stderr)
                foliadoc.save(output)

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
        try:
            id2foliasent = dict(enumerate(self.fname2foliadoc[fname].sentences(), 1))
        except KeyError:
            print('WARNING: File {} not passed in as argument'.format(fname), file=sys.stderr)
            id2foliasent = None  # We cannot shortcut here, because we still need to filter `only_special`

        manual, auto = [], []
        for annot in sorted(annots):
            if self.args.only_special and annot.json_data["type"] != "SPECIAL-CASE":
                auto.append(annot)
                continue

            try:
                if id2foliasent and self.folia_modify(id2foliasent.get(annot.sent_id), annot):
                    auto.append(annot)
                    continue
            except NoteError as e:
                print(e, file=sys.stderr)  # fallback on manual below
            manual.append(annot)
        return manual, auto


    def folia_modify(self, foliasent, annot):
        r"""Modify the FoliA data (raise NoteError on failure)."""
        if foliasent is None:
            raise annot.err("File {} does not have sentence #{}!", annot.filename, annot.sent_id)

        if annot.json_data["type"] == "RE-ANNOT":
            entity = self.folia_get_entity(foliasent, annot)
            if entity is None:
                raise annot.err("MWE not found in input XML")

            RE_SOURCEINFO = re.compile(r"^(?P<categ>\S+)( (?P<confid>[0-9]+)%)?$")
            sourceinfo = RE_SOURCEINFO.match(annot.json_data["source_categ"]).groupdict()
            expected_categ, categ = sourceinfo["categ"], entity.cls
            expected_confid, confid = int(sourceinfo["confid"] or 100), int((entity.confidence or 1)*100)
            if expected_categ != categ:
                raise annot.err("XML has unexpected category {} (not {})", categ, expected_categ)
            if expected_confid != confid:
                raise annot.err("XML has unexpected confidence {}% (not {}%)", confid, expected_confid)
            if annot.json_data["target_categ"] not in KNOWN_CATEGS:
                raise annot.err("Target VMWE category is either language-specific or a typo")

            folia_mwe = [w.text() for w in entity.wrefs()]
            if folia_mwe != annot.json_data["source_mwe"]:
                raise annot.err("MWE mismatch: JSON {J[source_mwe]} vs XML {}", folia_mwe)

            self.folia_reannot_tokens(entity, annot)
            # WARNING: First call folia_reannot_tokens, which may fail before changing `entity`
            # .......: Then, you can change it further (must not `raise` from here on)
            if annot.json_data["source_categ"] != annot.json_data["target_categ"]:
                entity.cls, entity.confidence = annot.json_data["target_categ"], None
                entity.append(self.folia.Comment, annotatortype="auto", datetime=ISOTIME,
                        value="[AUTO RE-ANNOT CATEGORY: {} → {}]".format(
                        annot.json_data["source_categ"], annot.json_data["target_categ"]))
            return True


    def folia_get_entity(self, foliasent, annot):
        r"""Find folia.Entity object. Creates one if Skipped. Returns None on failure."""
        foliaentity = self.folia_find_entity(foliasent, annot.indexes)
        if not foliaentity and annot.json_data["source_categ"] == "Skipped":
            layers = list(foliasent.select(self.folia.EntitiesLayer))
            if not layers:
                layers = [foliasent.append(self.folia.EntitiesLayer)]
            foliaentity = layers[0].append(self.folia.Entity, cls="Skipped")
            self.folia_entity_set_indexes(annot, foliaentity, annot.indexes)
        return foliaentity  # may be None


    def folia_find_entity(self, foliasent, target_indexes):
        r"""Find folia.Entity object. Returns None on failure."""
        for foliaentity in foliasent.select(self.folia.Entity):
            indexes = tuple(int(w.id.rsplit(".", 1)[-1])-1 for w in foliaentity.wrefs())
            if indexes == target_indexes:
                return foliaentity


    def folia_entity_set_indexes(self, annot, foliaentity, target_indexes):
        r"""Make sure `foliaentity` points to given MWEAnnot's indexes"""
        try:
            sentence = list(foliaentity.parent.parent.words())
            foliaentity.setspan(*[sentence[i] for i in target_indexes])
        except IndexError:  # python does not give us the index value, and I'm not in the mood for that...
            raise annot.err('Index out of bounds in {}', list(target_indexes))

    def folia_reannot_tokens(self, foliaentity, annot):
        r"""Change `foliaentity` according to annot.json_data["target_mwe"]."""
        if "target_mwe" in annot.json_data:
            source_words = foliaentity.wrefs()
            target_mwe = annot.json_data["target_mwe"]
            kept_words = [w for w in source_words if w.text() in target_mwe]
            if not kept_words:
                raise annot.err("Unable to automatically annotate, all words changed")
            mwemid = target_mwe.index(kept_words[0].text())
            sentmid = int(kept_words[0].id.split(".")[-1])-1
            sent_surfaces = list(w.text() for w in foliaentity.parent.parent.words())
            sent_words = list(w for w in foliaentity.parent.parent.words())
            left_i = self.find_words(annot, reversed(sent_words[:sentmid]),
                    reversed(sent_surfaces[:sentmid]), reversed(target_mwe[:mwemid]))
            right_i = self.find_words(annot, sent_words[sentmid:],
                    sent_surfaces[sentmid:], target_mwe[mwemid:])
            target_words = list(reversed(list(left_i))) + list(right_i)
            foliaentity.setspan(*target_words)
            foliaentity.append(self.folia.Comment, annotatortype="auto", datetime=ISOTIME,
                    value="[AUTO RE-ANNOT TOKENS: \"{}\" → \"{}\"]".format(
                    " ".join(annot.json_data["source_mwe"]), " ".join(annot.json_data["target_mwe"])))

    def find_words(self, annot, foliawords, surfaces, mwe):
        foliawords, surfaces = list(foliawords), list(surfaces)
        base_i = -1
        for word in mwe:
            try:
                base_i = surfaces.index(word, base_i+1)
                yield foliawords[base_i]
            except ValueError:
                raise annot.err('Target MWE tokens not found in XML sentence')


class NoteError(Exception):
    r"""Exception raised for errors in this library."""
    def __init__(self, fname, sent_id, msg):
        super().__init__("{}:#{}: WARNING: {}".format(fname, sent_id, msg))



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
#! /usr/bin/env python3

import argparse
import collections
import datetime
import json
import os
import re
import subprocess
import sys

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../lib"))
import dataalign

from pynlpl.formats import folia


parser = argparse.ArgumentParser(description="""
        Read JSON notes and output a pretty page that indicates what should be (re-)annotated.""")
parser.add_argument("--json-input", metavar="ParsemeNotesJson", type=argparse.FileType('r'), required=True,
        help="""Path to JSON notes file generated by the consistency-check/adjudication webpage""")
parser.add_argument("--xml-input", nargs="+",
        help="""Path to input FoLiA XML files (annotation downloaded from FLAT).
        If this option is specified, only the required manual corrections are shown.""")

parser.add_argument("--generate-xml", action="store_true",
        help="""Output automatically corrected XML in "./AfterAutoUpdate" directory.""")
parser.add_argument("--only-special", action='store_true',
        help="""Show only corrections corresponding to "special cases".""")


ISOTIME = datetime.datetime.now().isoformat()


class IndexInfo(collections.namedtuple('IndexInfo', 'filename sent_id indexes')):
    r"""`sent_id` is 0-based, `indexes` is 0-based."""
    def likely_the_same_as(self, other):
        r"""True iff the IndexInfo instances are likely to be related.
        (Used as a shortcut to avoid having a detailed algorithm...
        This is a hack which should be fixed at some point).
        """
        return self.filename == other.filename and self.sent_id == other.sent_id \
               and set(self.indexes) & set(other.indexes)

class AnnotEntry(collections.namedtuple('AnnotEntry', 'index_infos json_data')):
    r"""index_infos: List[IndexInfo], json_data: dict"""
    def good(self, msg, *args, **kwargs):
        r"""Assign self.message with an OK message (to show in output)"""
        self.message = msg.format(*args, J=self.json_data, **kwargs)

    def err(self, msg, *args, **kwargs):
        r"""Assign self.message with a warning message (to show in output)"""
        self.message = msg.format(*args, J=self.json_data, **kwargs)
        return NoteError(msg=self.message, fname=self.index_infos[0].filename, sent_id=self.index_infos[0].sent_id)

    def target_x(self, x):
        r"""Return JSON data --- e.g. target_mwe or source_mwe (if x == "mwe")"""
        return self.json_data.get('target_'+x) or self.json_data['source_'+x]

    def can_merge(self, other):
        r"""True iff we can merge these two AnnotEntry instances.
        Two instances can be merged iff they represent the same re-annotation.
        (e.g. merge the AnnotEntry "take_a_shower LVC => take_shower LVC"
        with the AnnotEntry "take_shower Skipped => take_shower LVC").
        """
        # Note that we simplify the code because we don't know the target
        # indexes (only source index and target MWEs), but the chance of error is minimal:
        return self.index_infos[0].likely_the_same_as(other.index_infos[0]) \
               and self.target_x("mwe") == other.target_x("mwe")


class Main(object):
    def __init__(self, args):
        self.args = args
        self.fname2annots = collections.defaultdict(list)  # filename -> List[AnnotEntry]
        if self.args.only_special and self.args.xml_input:
            dataalign.do_warn("Did you really mean to specify both " \
                              "--xml-input and --only-special?")
        if self.args.generate_xml and not self.args.xml_input:
            raise Exception("Option --xml-input required if --generate-xml is specified")

        self.fname2foliadoc = {}
        self.basefname2fname = {}
        if self.args.xml_input:
            self.fname2foliadoc = {fname: folia.Document(file=fname) for fname in self.args.xml_input}
            self.basefname2fname = {os.path.basename(fname): fname for fname in self.fname2foliadoc}

    def run(self):
        self.load_fname2annots()
        print(HTML_HEADER)
        for fname, annots in sorted(self.fname2annots.items()):
            self.n_manual = self.n_auto = 0
            self.print_panel(fname, annots)
        print(HTML_FOOTER)

        if self.args.generate_xml:
            subprocess.check_call("rm -rf ./AfterAutoUpdate", shell=True)
            subprocess.check_call("mkdir -p ./AfterAutoUpdate", shell=True)
            for fname, foliadoc in sorted(self.fname2foliadoc.items()):
                output = "./AfterAutoUpdate/" + os.path.basename(fname)
                dataalign.do_info("Saving to \"{}\"".format(output))
                foliadoc.save(output)
            if self.n_auto == 0:
                dataalign.do_warn('Zero annotations were done automatically. Check for warnings above.', error=True)

    def print_panel(self, fname, annots):
        r"""print_panel(str, list[AnnotEntry])
        Print panel for a given file name, along with all of its annotations.
        """
        manual, auto = self.split_corrections(fname, annots)
        print('<div class="panel panel-default file-block">')
        print('<div class="panel-heading filename">{} <a class="show-link">' \
                '[<span class="show-or-hide-text">show</span>' \
                '<span class="show-or-hide-text" style="display:none">hide</span>' \
                ' {}/{} automatically annotated]</a></div>'.format(
                    fname, len(auto), len(auto)+len(manual)))
        print('<div class="panel-body">')
        print('<div class="list-group">')
        try:
            for annot in sorted(manual):
                self.print_annot(annot, True)
            if self.n_manual == 0:
                print('<div class="list-group-item annot-entry wtd-list-manual">No re-annotations need to be done manually!</div>')
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


    def print_annot(self, annot_entry: AnnotEntry, is_manual: bool):
        r"""Print the annotation item corresponding to one MWE occurrence."""
        if annot_entry.json_data['type'] == 'DO-NOTHING':
            return  # completely hide it, nobody cares when it's DO-NOTHING

        right_span = ""
        if hasattr(annot_entry, "message"):
            right_span = '<span class="{}">{}</span>'.format(
                ("warn-txt" if is_manual else "auto-txt"), annot_entry.message)

        if is_manual:
            print('<div class="list-group-item annot-entry wtd-list-manual">{}{}</div>'.format(
                    right_span, "".join(self.annot2str(annot_entry, "what-to-do-manual"))))
            self.n_manual += 1
        else:
            print('<div class="list-group-item annot-entry wtd-list-auto">{}{}</div>'.format(
                    right_span, "".join(self.annot2str(annot_entry, "what-to-do-auto"))))
            self.n_auto += 1


    def annot2str(self, annot_entry: AnnotEntry, wtd_class: str) -> str:
        r"""Return the annotation entry corresponding to one MWE occurrence."""
        J = annot_entry.json_data
        yield '<span class="label label-default sent-id">Sentence #{}</span>'.format(annot_entry.index_infos[0].sent_id)
        yield '<span class="focus-mwe">{}</span>'.format(" ".join(J.get("source_mwe") or ['+']))
        if annot_entry.json_data["type"] == "SPECIAL-CASE":
            yield '<div class="{} wtd-special">{}</div>'.format(wtd_class, J["human_note"])

        elif annot_entry.json_data["type"] == "DELETE-ANNOT":
            yield '<div class="{} wtd-reannot">Delete annotation: &quot;{}&quot;</div>' \
                    .format(wtd_class, " ".join(J["source_mwe"]))

        elif annot_entry.json_data["type"] == "NEW-ANNOT":
            yield '<div class="{} wtd-reannot">Annotate: &quot;{}&quot;</div>' \
                    .format(wtd_class, " ".join(J["target_mwe"]))
            yield '<div class="{} wtd-reannot">With category: {}</div>' \
                    .format(wtd_class, J["target_categ"])

        elif annot_entry.json_data["type"] == "RE-ANNOT":
            if "target_mwe" not in J or J["source_mwe"] == J["target_mwe"]:
                yield '<div class="{} wtd-reannot">In token annotation: &quot;{}&quot;</div>' \
                        .format(wtd_class, " ".join(J["source_mwe"]))
            else:
                yield '<div class="{} wtd-reannot">Re-annotate tokens: &quot;{}&quot; &rarr; &quot;{}&quot;</div>' \
                        .format(wtd_class, " ".join(J["source_mwe"]), " ".join(J["target_mwe"]))

            if J["source_categ"] == J["target_categ"]:
                yield '<div class="{} wtd-reannot">Keep category: {}</div>' \
                        .format(wtd_class, J["source_categ"])
            else:
                yield '<div class="{} wtd-reannot">Re-annotate category: {} &rarr; {}</div>' \
                        .format(wtd_class, J["source_categ"], J["target_categ"])

        else:
            raise Exception("Unknown ANNOT type: " + annot_entry.json_data['type'])

    def load_fname2annots(self):
        J = json.load(self.args.json_input)
        if not 'META' in J:
            raise Exception('JSON file is too old -- is it from parseme ST 1.0?')
        json_v = J['META']['parseme_json_version']
        if json_v.split('.')[0] > '2':
            raise Exception('BUG: Must update this script for JSON version {}'.format(json_v))

        self.json_id2fname = J['META']['filename_mapping']

        for coded_key, json_data in J['DECISIONS'].items():
            if coded_key.startswith("MWE_KEY="):
                # Decode the key (it's a JSON inside a JSON string)
                key = json.loads(re.sub("^MWE_KEY=", "", coded_key))
                line_num = next(k[1] for k in key if k)
                index_infos = tuple(IndexInfo(self.json_id2fname[str(k[0])], k[1], tuple(k[2]))
                                    if k else IndexInfo(self.json_id2fname[str(i)], line_num, ())
                                    for i, k in enumerate(key, 1))
                annot_entry = AnnotEntry(index_infos, json_data)
                filename = str(index_infos[0].filename) if index_infos[0] else '1'
                self.fname2annots[filename].append(annot_entry)
            else:
                raise Exception("Unknown coded-key: " + coded_key)


    def split_corrections(self, fname, annots):
        r"""Split `annots` in two lists: (manual_annots, auto_annots)"""
        try:
            id2foliasent = dict(enumerate(self.fname2foliadoc[fname].sentences(), 1))
        except KeyError:
            dataalign.do_warn('File \"{f}\" expected as an argument!', f=fname)
            try:
                new_fname = self.basefname2fname[os.path.basename(fname)]
                if new_fname in self.json_id2fname.values():
                    dataalign.do_warn('Refusing to use \"{f}\" (it looks like the wrong filename)', f=new_fname, header=True)
                    raise KeyError
                else:
                    id2foliasent = dict(enumerate(self.fname2foliadoc[new_fname].sentences(), 1))
                    print('Using \"{f}\" instead (you must CHECK if this is correct!)', f=new_fname, header=True)
            except KeyError:
                id2foliasent = None  # We cannot shortcut here, because we still need to filter `only_special`

        manual, auto = [], []
        for annot in sorted(annots):
            if self.args.only_special and annot.json_data["type"] != "SPECIAL-CASE":
                auto.append(annot)
                continue

            try:
                if not id2foliasent:
                    raise annot.err('Underlying XML file not given as input')
                folia_sent = id2foliasent.get(annot.index_infos[0].sent_id)
                self.folia_modify(folia_sent, annot, auto)
            except NoteError as e:
                dataalign.do_warn(str(e), prefix=e.prefix)  # fallback on manual below
                manual.append(annot)
            else:
                auto.append(annot)
        return manual, auto


    def folia_modify(self, foliasent: folia.Sentence,
                     annot: AnnotEntry, recently_auto_annotated: list):
        r"""Modify the FoliA data (raise NoteError on failure)."""
        if foliasent is None:
            raise annot.err("File does not have sentence #{}!", annot.index_infos[0].sent_id)

        if annot.json_data["type"] == "DO-NOTHING":
            return annot.good("Nothing do to")  # literally do nothing

        elif annot.json_data["type"] in "SPECIAL-CASE":
            raise annot.err("Marked as SPECIAL CASE (cannot be automatically corrected)")

        elif annot.json_data["type"] == "NEW-ANNOT":
            indexes = {i for iinfos in annot.index_infos for i in iinfos.indexes}
            entity = foliasent.add(folia.Entity, *[foliasent[i] for i in indexes])
            entity.cls = annot.json_data['target_categ']
            self.folia_reannot_tokens(entity, annot)
            return annot.good("Automatically annotated")

        elif annot.json_data["type"] in ["RE-ANNOT", "DELETE-ANNOT"]:
            entity = self.folia_get_entity(foliasent, annot)
            if entity is None:
                raise annot.err("MWE not found in input XML")

            if annot.json_data["type"] == "DELETE-ANNOT":
                entity.parent.remove(entity)
                return annot.good("Automatically deleted")

            RE_SOURCEINFO = re.compile(r"^(?P<categ>\S+)( (?P<confid>[0-9]+)%)?$")
            sourceinfo = RE_SOURCEINFO.match(annot.json_data["source_categ"]).groupdict()
            expected_categ, categ = sourceinfo["categ"], entity.cls
            expected_confid, confid = int(sourceinfo["confid"] or 100), int((entity.confidence or 1)*100)
            if expected_categ != categ:
                if expected_categ == "Skipped":
                    for previous_annot in reversed(recently_auto_annotated):
                        if previous_annot.can_merge(annot):
                            if previous_annot.target_x("categ") == categ:
                                return annot.good("Merged with another annotation")
                            raise annot.err("New category conflicts with {}", previous_annot.target_x("categ"))
                raise annot.err("XML has unexpected category {} (not {})", categ, expected_categ)
            if expected_confid != confid:
                raise annot.err("XML has unexpected confidence {}% (not {}%)", confid, expected_confid)
            if annot.json_data["target_categ"] not in dataalign.Categories.KNOWN:
                raise annot.err("Target MWE category is unknown (might be a typo)")

            folia_mwe = [w.text() for w in entity.wrefs()]
            if folia_mwe != annot.json_data["source_mwe"]:
                raise annot.err("MWE mismatch: JSON {J[source_mwe]} vs XML {}", folia_mwe)

            self.folia_reannot_tokens(entity, annot)
            # WARNING: First call folia_reannot_tokens, which may fail before changing `entity`
            # .......: Then, you can change it further (must not `raise` from here on)
            if annot.json_data["source_categ"] != annot.json_data["target_categ"]:
                entity.cls, entity.confidence = annot.json_data["target_categ"], None
                entity.append(folia.Comment, annotatortype="auto", datetime=ISOTIME,
                        value="[AUTO RE-ANNOT CATEGORY: {} → {}]".format(
                        annot.json_data["source_categ"], annot.json_data["target_categ"]))
            return annot.good("Automatically reannotated")
        else:
            raise Exception("Unknown ANNOT type: " + annot.json_data['type'])


    def folia_get_entity(self, foliasent, annot):
        r"""Find folia.Entity object. Creates one if Skipped. Returns None on failure."""
        foliaentity = self.folia_find_entity(foliasent, annot.index_infos[0].indexes)
        if not foliaentity and annot.json_data["source_categ"] == "Skipped":
            layers = list(foliasent.select(folia.EntitiesLayer))
            if not layers:
                layers = [foliasent.append(folia.EntitiesLayer)]
            foliaentity = layers[0].append(folia.Entity, cls="Skipped")
            self.folia_entity_set_indexes(annot, foliaentity, annot.index_infos[0].indexes)
        return foliaentity  # may be None


    def folia_find_entity(self, foliasent, target_indexes):
        r"""Find folia.Entity object. Returns None on failure."""
        for foliaentity in foliasent.select(folia.Entity):
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

            if 'source_mwe' in annot.json_data:
                annot_comment = "[AUTO RE-ANNOT TOKENS: \"{}\" → \"{}\"]".format(
                        " ".join(annot.json_data["source_mwe"]), " ".join(annot.json_data["target_mwe"]))
            else:
                annot_comment = "[AUTO ANNOT TOKENS: \"{}\"]".format(
                        " ".join(annot.json_data["target_mwe"]))
            foliaentity.append(folia.Comment, annotatortype="auto", datetime=ISOTIME, value=annot_comment)

    def find_words(self, annot, foliawords, surfaces, mwe):
        foliawords, surfaces = list(foliawords), list(surfaces)
        base_i = -1
        for word in mwe:
            try:
                base_i = surfaces.index(word, base_i+1)
                yield foliawords[base_i]
            except ValueError:
                if word not in surfaces:
                    raise annot.err('Target MWE token "{}" not found in XML sentence'.format(word))
                raise annot.err('Target MWE token "{}" seems misplaced -- better do it manually'.format(word))


class NoteError(Exception):
    r"""Exception raised for errors in this library."""
    def __init__(self, fname, sent_id, msg):
        self.prefix = "{}:#{}".format(fname, sent_id)
        super().__init__(msg)



HTML_HEADER = '''
<html>
<body>
<meta charset="UTF-8">
<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css">
<script src="https://ajax.googleapis.com/ajax/libs/jquery/3.1.1/jquery.min.js"></script>
<script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/js/bootstrap.min.js"></script>

<style>
.focus-mwe {
    padding-left: 5px;
    font-weight: bold;
}
.what-to-do-auto { color: #E3A933; }
.what-to-do-manual { color: #19BF26; }
.wtd-list-auto { display: none; background-color: #FAFAFA; }
.wtd-list-manual { }

.list-group {
    margin-bottom: 0px;
}
.show-link {
    cursor: pointer;
    float: right;
}

.auto-txt { float: right; color: #9e9e9e; }
.warn-txt { float: right; color: #9e9e9e; }

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
      <li>Re-annotate this <strong>MWE</strong> in FLAT according to the <span class="what-to-do-manual">instructions in green</span>.</li>
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
    $(".show-or-hide-text").toggle();
});
</script>


</body>
</html>
'''


#####################################################

if __name__ == "__main__":
    Main(parser.parse_args()).run()

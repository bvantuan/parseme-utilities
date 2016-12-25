#! /usr/bin/env python3

import argparse
import collections
import json
import os
import re
import sys

parser = argparse.ArgumentParser(description="""
        Read JSON notes and output a pretty page that indicates what should be annotated.""")
parser.add_argument("--json", metavar="ParsemeNotesJson", type=argparse.FileType('r'), required=True,
        help="""Path to a JSON file with adjudication/homogenization information""")
parser.add_argument("--onlyspecial", action='store_true', required=False,
        help="""Outputs only corrections corresponding to special cases.""")

AnnotEntry = collections.namedtuple('AnnotEntry', 'filename sent_id indexes json_data')


class Main(object):
    def __init__(self, args):
        self.args = args
        self.fname2annots = collections.defaultdict(list)  # filename -> List[AnnotEntry]

    def run(self):
        self.load_fname2annots()
        print(HTML_HEADER)
        for fname, annots in sorted(self.fname2annots.items()):
            self.print_panel(fname, annots)
        print(HTML_FOOTER)

    def print_panel(self, fname, annots):
        print('<div class="panel-heading filename">{}</div>'.format(fname))
        print('<div class="panel-body">')
        print('<div class="list-group">')
        for annot in sorted(annots):
            try:
                print('<div class="list-group-item annot-entry">{}</div>'.format("".join(self.annot2str(annot))))
            except Exception as e:
                import traceback
                traceback.print_exc()
                mwe = " ".join(str(x) for x in annot.json_data.get("source_mwe", annot.indexes))
                print(annot.json_data, file=sys.stderr)
                exit("===============\nERROR when processing JSON file for \"{}\", " \
                        "sentence #{}, MWE \"{}\"".format(fname, annot.sent_id, mwe))
        print('</div>')  # list-group
        print('</div>')  # panel-body

    def annot2str(self, annot_entry):
        J = annot_entry.json_data
        yield '<span class="label label-default sent-id">#{}</span>'.format(annot_entry.sent_id)
        yield '<span class="source-mwe">{}</span>'.format(" ".join(J["source_mwe"]))
        if annot_entry.json_data["type"] == "SPECIAL-CASE":
            yield '<div class="what-to-do wtd-special">{}</div>'.format(J["human_note"])
        elif annot_entry.json_data["type"] == "RE-ANNOT":
            yield '<div class="what-to-do wtd-reannot">Re-annotate: {} &rarr; {}</div>' \
                    .format(J["source_categ"], J["target_categ"])

    def load_fname2annots(self):
        J = json.load(self.args.json)
        for coded_key, json_data in J.items():
            if coded_key.startswith("MODIF:"):
                #import pdb
                #pdb.set_trace()
                if not self.args.onlyspecial or ( self.args.onlyspecial and json_data["type"] == "SPECIAL-CASE") :
                    # Decode the key (it's a JSON inside a JSON string)
                    key = json.loads(re.sub("^MODIF:", "", coded_key))
                    annot_entry = AnnotEntry(*(key + [json_data]))
                    self.fname2annots[annot_entry.filename].append(annot_entry)
            else:
                raise Exception("Unknown coded-key: " + coded_key)


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
.what-to-do {
    color: #3BA220;
}
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
      <li>Re-annotate this <strong>MWE</strong> in FLAT according to the <span class="what-to-do">instructions</span>.</li>
      <li>(Note: There is an indication of the <span class="label label-default sent-id">sentence number</span> for each MWE).</li>
  </ul>
  </ol>
</div>
'''

HTML_FOOTER = '''
</div>  <!-- panel-default -->
</body>
</html>
'''


#####################################################

if __name__ == "__main__":
    Main(parser.parse_args()).run()

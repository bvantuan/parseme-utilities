#! /usr/bin/env python3

import argparse
import csv
import re
import sys
from bs4 import BeautifulSoup  # sudo pip3 install beautifulsoup4


NEWLINE = re.compile(r" *\n *")
LINEBR = re.compile(r"<br */?>")
ID_PARTS = re.compile(r"([0-9.]*)_([A-Z0-9]*)_(.*)")
CLASS_LANG = re.compile(r"\bl-([a-z]*)\b")
ALL_LANGS = {
  "bg": "Bulgarian",
  "cs": "Czech",
  "de": "German",
  "el": "Greek",
  "en": "English",
  "es": "Spanish",
  "fa": "Farsi",
  "fr": "French",
  "he": "Hebrew",
  "hr": "Croatian",
  "hu": "Hungarian",
  "it": "Italian",
  "lt": "Lithuanian",
  "mt": "Maltese",
  "pl": "Polish",
  "pt": "Brazilian Portuguese",
  "ro": "Romanian",
  "se": "Swedish",
  "sl": "Slovene",
  "tr": "Turkish",
  "yi": "Yiddish",
}

parser = argparse.ArgumentParser(description="""
        Read HTML in stdin and print the language examples.""")


def main():
  csv_writer = csv.writer(sys.stdout, delimiter="\t",
                                      quoting=csv.QUOTE_NONE,
                                      quotechar="")
  csv_writer.writerow(["ID-section","ID-order","ID-name","lang","HTML-example"])

  if sys.argv[1] == "-" :
    html = sys.stdin.read()
  else :
    html = open(sys.argv[1])
  parsed_html = BeautifulSoup(html, 'lxml')

  for ul in parsed_html.findAll("ul"):
    attrs = dict(ul.attrs)
    ul_id = attrs.get("id")
    if not ul_id: continue

    id_section, id_order, id_name = ID_PARTS.match(ul_id).groups()
    txt_lines = {}
    for ex in ul.findAll("div", "ex"):
      class_str = " ".join(dict(ex.attrs)["class"])
      lang = CLASS_LANG.search(class_str).group(1)
      txt = "".join(str(x) for x in ex.find('li').children).strip()
      if txt_lines.get(lang,None) :
        print("Error: example {} has several {} elements".format("_".join(
              [id_section,id_order,id_name]),lang),file=sys.stderr)
        sys.exit(-1)
      txt_lines[lang] = LINEBR.split(NEWLINE.sub("", txt))      
    for lang in sorted(ALL_LANGS.keys()):
      txt_line = txt_lines.get(lang,None)
      if txt_line :
        csv_writer.writerow([id_section, id_order, id_name, lang.upper(), 
                             "<br/>".join(map(lambda x : x.strip(),txt_line))])
      else :
        csv_writer.writerow([id_section, id_order, id_name, lang.upper(), ""])
    csv_writer.writerow(["----"]*5)


if __name__ == "__main__":
  main()

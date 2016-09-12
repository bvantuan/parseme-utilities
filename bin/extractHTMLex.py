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


parser = argparse.ArgumentParser(description="""
        Read HTML in stdin and print the language examples.""")


def main():
    csv_writer = csv.writer(sys.stdout, delimiter="\t")

    html = sys.stdin.read()
    parsed_html = BeautifulSoup(html, 'lxml')

    for ul in parsed_html.findAll("ul"):
        attrs = dict(ul.attrs)
        ul_id = attrs.get("id")
        if not ul_id: continue

        id_section, id_order, id_name = ID_PARTS.match(ul_id).groups()

        for ex in ul.findAll("div", "ex"):
            class_str = " ".join(dict(ex.attrs)["class"])
            lang = CLASS_LANG.search(class_str).group(1).upper()
            txt = "".join(str(x) for x in ex.find('li').children).strip()
            txt_lines = LINEBR.split(NEWLINE.sub("", txt))
            for txt_line in txt_lines:
                csv_writer.writerow([id_section, id_order, id_name, lang, txt_line])
        print("---------------")


if __name__ == "__main__":
    main()

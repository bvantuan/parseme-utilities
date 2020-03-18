#!/usr/bin/env python3

import argparse
import os.path

################################################
# ARGUMENTS
################################################


parser = argparse.ArgumentParser(description='add_sent_ids')
# subparsers = parser.add_subparsers(dest='command', help='available commands')

# parser_estimate = subparsers.add_parser('estimate', help='estimate test size')
parser.add_argument(
    "-i",
    dest="input_path",
    required=True,
    # nargs='+',
    help="input .conllu file",
    metavar="FILE"
)
# parser.add_argument(
#     "-o",
#     dest="output_path",
#     required=True,
#     # nargs='+',
#     help="output .conllu file",
#     metavar="FILE"
# )
# parser.add_argument(
#     "--discard_raw",
#     dest="discard_raw",
#     action="store_true",
#     help="Discard 'raw' from sent ID names"
# )


################################################
# IDs
################################################


def add_ids(input_path):
    base = os.path.splitext(os.path.basename(input_path))[0]
    # Specific for PL
    base = base.lstrip("raw-")
    # Local sentence ID
    k = 1
    with open(input_path, "r", encoding="utf-8") as data_file:
        for line in data_file:
            if line.startswith("# text"):
                sent_id = ".".join((base, str(k)))
                print("# sent_id =", sent_id)
                k += 1
            print(line, end='')


#################################################
# MAIN
#################################################


if __name__ == '__main__':
    args = parser.parse_args()
    add_ids(args.input_path)

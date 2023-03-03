#! /usr/bin/env python3

import sys

# Check that the user has provided a filename as a command line argument
if len(sys.argv) < 2:
    print("Please provide a filename as a command line argument.")
    sys.exit()

# Get the filename from the command line argument
filename = sys.argv[1]

# Open the CoNLL-U file in read mode
with open(filename, 'r') as f:
    # Read the contents of the file into a string variable
    file_contents = f.read()
    # Split the contents of the file into lines
    lines = file_contents.split('\n')

    # Loop through each line in the file and check if it conforms to the CoNLL-U format
    for line in lines:
        # Skip comment lines
        if not line.strip() or line.startswith('#'):
            continue

        # Split the line into fields
        fields = line.strip().split('\t')
        # Check if the line has the expected number of fields
        if len(fields) != 10:
            exit("ERROR: Line does not conform to CoNLL-U format: {}".format(line))

print(f"{filename} validated: no errors in format.", file=sys.stderr)
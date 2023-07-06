#!/bin/bash

SCHEMA_FILE="../lang-leaders/morphosyntax-update/configs/config-schema.json"
CONFIG_DIRECTORY="../lang-leaders/morphosyntax-update/configs"
HERE="$(cd "$(dirname "$0")" && pwd)"

cd "$HERE"

# Check if the JSON schema file exists
if [ ! -f "$SCHEMA_FILE" ]; then
  echo "JSON schema file '$SCHEMA_FILE' not found."
  exit 1
fi

# Check if the configuration file exists
if [ ! -d "$CONFIG_DIRECTORY" ]; then
  echo "Configuration directory '$CONFIG_DIRECTORY' not found."
  exit 1
fi

# find all cupt files
json_files=$(find "$CONFIG_DIRECTORY" -type f -name "config_*.json")
# loop through each file
while read -r f; do
    # remove redundant / characters from treebank file path
    f=$(readlink -m -f "$f")
   
    # Validate the configuration file against the JSON schema
    if ajv -s "$SCHEMA_FILE" -d "$f"; then
        echo "The configuration file '$f' is valid."
    else
        echo "The configuration file '$f' is invalid."
        exit 1
    fi
done <<< "$json_files"


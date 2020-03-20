#!/bin/bash

# TODO: reoranize this script, so that it takes arguments with
# all relevant paths

# Echo on
set -x

# Pull latest versions of all corpora
apply-all-corpora.sh "git pull"

# Check if the datasets are identical
./scripts/check_all.sh scripts/langs/all.txt data/ST1.2 data/preliminary-sharedtask-data-alt

# Move to directory with splits
cd data/preliminary-sharedtask-data-alt

# Inspect all validation logs
cat */*valid*

# Check for "sent_id"
grep -l "# sent_id =" -R .

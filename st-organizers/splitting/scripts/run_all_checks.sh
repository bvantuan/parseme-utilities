#!/bin/bash

# TODO: reoranize this script, so that it takes arguments with
# all relevant paths

# Echo on
set -x

# Otherwise, I get encoding errors
export LC_ALL=en_US.UTF-8

# Pull latest versions of all corpora
apply-all-corpora.sh "git pull"

# Check if the datasets are identical
./scripts/check_all.sh scripts/langs/all.txt data/ST1.2 data/preliminary-sharedtask-data

# Move to directory with splits
cd data/preliminary-sharedtask-data

# Inspect all validation logs
cat */*valid*

# Check for "sent_id"
grep -l "# sent_id =" -R .

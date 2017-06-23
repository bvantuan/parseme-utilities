#!/bin/bash
HERE="$(cd "$(dirname "$0")" && pwd)"
set -o nounset    # Using "$UNDEF" var raises error
set -o errexit    # Exit on error, do not continue quietly

source ../../lib/parseme_st_data_dev_path.bash
cd "${PARSEME_SHAREDTASK_DATA_DEV:?}"


# To run for specific languages, run LANGUAGES="XX YY" ./gen_blind.sh
# By default, runs for all two-letter folders (languages)

for lang in ${LANGUAGES:-??}; do
  if [ -f ${lang}/parsemetgz/OUT/test.parsemetsv ]; then    
    cat ${lang}/parsemetgz/OUT/test.parsemetsv |
    awk 'BEGIN{FS=OFS="\t"}{if (NF == 4 && $0 !~ "^#"){ print $1,$2,$3,"_"; } else { print $0; }}' |
    cat > ${lang}/parsemetgz/OUT/test.blind.parsemetsv
    echo "Generated ${lang}/parsemetgz/OUT/test.blind.parsemetsv" >&2
  else
    echo "No test data in ${lang}" >&2
  fi
done

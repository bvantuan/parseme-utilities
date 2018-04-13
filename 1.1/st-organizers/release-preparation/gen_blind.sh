#!/bin/bash
HERE="$(cd "$(dirname "$0")" && pwd)"
set -o nounset    # Using "$UNDEF" var raises error
set -o errexit    # Exit on error, do not continue quietly

source ../../lib/parseme_st_data_dev_path.bash
cd "${PARSEME_SHAREDTASK_DATA_DEV:?}"


# To run for specific languages, run LANGUAGES="XX YY" ./gen_blind.sh
# By default, runs for all two-letter folders (languages)

for lang in ${LANGUAGES:-??}; do
  if [ -f 1.1/preliminary-sharedtask-data/${lang}/SPLIT/test.cupt ]; then    
    cat 1.1/preliminary-sharedtask-data/${lang}/SPLIT/test.cupt |
    awk 'BEGIN{FS=OFS="\t"}{if (NF == 11 && $0 !~ "^#"){ print $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,"_"; } else { print $0; }}' |
    cat > 1.1/preliminary-sharedtask-data/${lang}/SPLIT/test.blind.cupt
    echo "Generated 1.1/preliminary-sharedtask-data/${lang}/SPLIT/test.blind.cupt" >&2
  else
    echo "No test data in ${lang}" >&2
  fi
done

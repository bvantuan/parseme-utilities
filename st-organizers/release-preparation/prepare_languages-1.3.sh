#!/bin/bash
HERE="$(cd "$(dirname "$0")" && pwd)"
set -o nounset    # Using "$UNDEF" var raises error
set -o errexit    # Exit on error, do not continue quietly

source ../../lib/parseme_release_dev_path.bash
cd "${PARSEME_RELEASE_DATA_DEV:?}"/preliminary-release-data


gen_stats() {
    for part in train test dev; do    
        if [ -f $lang"/${part}.cupt" ]; then
            echo "Statistics $lang" > $lang"/${part}-stats.md"
            echo "=============" >> $lang"/${part}-stats.md"
            echo "### ${part}.cupt" >> $lang"/${part}-stats.md"
            "$HERE/../corpus-statistics/mwe-stats-simple.py" --lang=$lang --input $lang"/${part}.cupt" >> $lang"/${part}-stats.md"
        fi
    done
    echo "Statistics $lang" > $lang"/total-stats.md"
    echo "=============" >> $lang"/total-stats.md"
    echo "### TOTAL" >> $lang"/total-stats.md"
    "$HERE/../corpus-statistics/mwe-stats-simple.py" --lang=$lang --input $lang/{train,test,dev}.cupt >> $lang"/total-stats.md"
}

# To run for specific languages, run LANGUAGES="XX YY" ./gen_blind.sh
# By default, runs for all two-letter folders (languages)

for lang in ${LANGUAGES:-??}; do  
  if [ -f ${lang}/test.cupt ]; then    
    cat ${lang}/test.cupt |
    awk 'BEGIN{FS=OFS="\t"}{if (NF == 11 && $0 !~ "^#"){ print $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,"_"; } else { print $0; }}' |
    cat > ${lang}/test.blind.cupt
    echo "Generated $PWD/${lang}/test.blind.cupt" >&2
    gen_stats "$lang"    
  else
    echo "No test data in ${lang}" >&2
  fi
done

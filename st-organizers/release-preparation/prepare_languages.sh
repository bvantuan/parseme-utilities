#! /bin/bash
HERE="$(cd "$(dirname "$0")" && pwd)"
set -o errexit

source ../../lib/parseme_st_data_dev_path.bash
cd "${PARSEME_SHAREDTASK_DATA_DEV:?}"


if test "${1:-}" = "-h"; then
    echo "Usage: ./prepare_languages.sh"
    echo ""
    echo "Prepare all languages:"
    echo "  * generate test.blind"
    echo "  * generate OUT directory"
    echo "  * generate stats.md"
    echo ""
    echo "For each language, there should be a script \$LANG/parsemetgz/genOUT.sh"
    echo "to generate the OUT directory. If genOUT.sh is missing, the language will be skipped."
    echo ""
    echo "To run for specific languages: LANGUAGES='XX YY' ./prepare_languages.sh"
    echo "By default, runs for all two-letter folders (languages)"
    exit 0
fi


gen_stats() {
    echo "Statistics $LANG"
    echo "============="
    echo ""
    for part in train test; do
        if [ -f $LANG"/parsemetgz/OUT/${part}.parsemetsv" ]; then
            echo "### ${part}.parsemetsv"
            "$HERE/../eval-statistics/folia2statsMarkdown.py" --lang=$LANG --input $LANG"/parsemetgz/OUT/${part}.parsemetsv"
            echo ""
        fi
    done   
}


# Export path to splitTrainTest, to be used by genOUT.sh
export SPLIT_TRAIN_TEST="$HERE/splitTrainTest.py"


for LANG in ${LANGUAGES:-??}; do
    echo "==> $LANG/parsemetgz" >&2
    if ! test -f $LANG/parsemetgz/genOUT.sh; then
        echo "WARNING: $LANG/parsemetgz/genOUT.sh is missing"
    else
        echo "Running $LANG/parsemetgz/genOUT.sh"
        pushd "$LANG/parsemetgz" >/dev/null
        rm -rf ./OUT
        mkdir -p ./OUT
        ./genOUT.sh
        for F in OUT/train.conllu OUT/train.parsemetsv; do test -s "$F" || rm -f "$F"; done
        popd >/dev/null
        LANGUAGES="$LANG" ./gen_blind.sh
        gen_stats "$LANG" >"$LANG/parsemetgz/stats.md"
    fi
done

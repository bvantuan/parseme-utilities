#! /bin/bash
HERE="$(cd "$(dirname "$0")" && pwd)"

set -o nounset    # Using "$UNDEF" var raises error
set -o errexit    # Exit on error, do not continue quietly

UDPIPE_PATH="${UDPIPE_PATH:-"$HERE/udpipe"}"


usage() {
    echo "Usage: $(basename "$0") [OPTIONS] <udpipe-model> <input-file-01> [<input-file-02> ...]"
    echo "OPTIONS are one of:"
    echo "  -h: show this usage help message"
    echo "  -r: input is raw text (UTF-8, LF line endings, one sentence per line)"
    echo "  -s: segmented sentences in raw input (only makes sense for -r), does not segment"
    echo "Run UDPipe on input files using given UDPipe model."
    echo "Accepts raw txt (-r) or vertical format (FoLiA, CUPT, parseme-tsv, CoNLL-U)."
    echo "Any existing information in vertical files (other than tokenisation) will be overwritten."
    echo "Creates resulting conllu files in the same directory as the input files, changing extension to .udpipe.conllu."
}
fail() {
    echo "$(basename "$0"): $1"; exit 1
}

segmented=""
rawinput=""
# Handle optional args
while getopts :"hrs" FLAG; do
    case "$FLAG" in
        h)  usage; exit 0 ;;
        r)  rawinput="--input=horizontal --tokenize" ;;
        s)  segmented="--tokenizer=presegmented" ;;
        :)  fail "missing arg to -$OPTARG" ;;
        \?) fail "bad flag: -$OPTARG" ;;
        *)  fail "NOT IMPLEMENTED: -$FLAG" ;;
    esac
done
shift "$((OPTIND - 1))"


# Handle positional args
test "$#" -lt 2  && fail "expected 1 model file and at least 1 input file"
udpipe_model="$1"; shift

########################################

conllup2conllu() {
    awk 'NR==1 {next} /# *source_sent_id/ {printf("# sent_id = %s\n", $NF); next} 1' | cut -f -10
}
bold_echo() {
    (tput bold; echo "$@"; tput sgr0)
}

#--------------------------------
if ! test -e "$UDPIPE_PATH"; then
    bold_echo '===> Downloading UDPipe'
    pushd "$(dirname "$UDPIPE_PATH")"
    git clone https://github.com/ufal/udpipe "$(basename "$UDPIPE_PATH")"
    bold_echo '===> Compiling UDPipe'
    cd "$(basename "$UDPIPE_PATH")/src"
    make
    popd
fi

#-----------------------
for inputtxt in "$@"; do
    #tmpfile="${TMPDIR:-/tmp}/run-udpipe.tmpfile"
    bold_echo "===> Started at: `date`"
    bold_echo "===> Generating: ${inputtxt}.udpipe.conllu"
    if [ "${rawinput}" = "" ]; then # input is vertical file, convert to conllu        
        ../../st-organizers/to_cupt.py --lang EN --input "${inputtxt}" | conllup2conllu
    else # does not preprocess, input is raw text, will tokenise
        cat "${inputtxt}" 
    fi |
    "$UDPIPE_PATH"/src/udpipe ${rawinput} ${segmented} --tag --parse "$udpipe_model" >| "${inputtxt}.udpipe.conllu"
    bold_echo "===> File ready: ${inputtxt}.udpipe.conllu"
    bold_echo "===> Finished at: `date`"
done

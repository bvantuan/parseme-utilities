#! /bin/bash
HERE="$(cd "$(dirname "$0")" && pwd)"

set -o nounset    # Using "$UNDEF" var raises error
set -o errexit    # Exit on error, do not continue quietly

UDPIPE_PATH="${UDPIPE_PATH:-./udpipe}"


usage() {
    echo "Usage: $(basename "$0") <udpipe-model> <xml-or-parsemetsv-files...>"
    echo "Run UDPipe on input XML/parsemetsv files using given UDPipe model."
    echo "Creates conllu files in the same directory as the input files."
}
fail() {
    echo "$(basename "$0"): $1"; exit 1
}

# Handle optional args
while getopts :"h" FLAG; do
    case "$FLAG" in
        h)  usage; exit 0 ;;
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
for inputtsv in "$@"; do
    tmpfile="${TMPDIR:-/tmp}/run-udpipe.tmpfile"

    bold_echo "===> Pre-processing: ${inputtsv}"
    "$HERE/../../st-organizers/parsemetsv2cupt.py" --artificial --input "$inputtsv"  | conllup2conllu >"$tmpfile"

    bold_echo "===> Generating: ${inputtsv}.GENERATED.conllu"
    "$UDPIPE_PATH"/src/udpipe --tag --parse "$udpipe_model" --input=conllu "$tmpfile" >|${inputtsv}.GENERATED.conllu
done

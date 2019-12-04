#! /bin/bash
HERE="$(cd "$(dirname "$0")" && pwd)"

set -o nounset    # Using "$UNDEF" var raises error
set -o errexit    # Exit on error, do not continue quietly

UDPIPE_PATH="${UDPIPE_PATH:-"$HERE/udpipe"}"


usage() {
    echo "Usage: $(basename "$0") <udpipe-model> <raw-txt-file-01> [<raw-txt-file-02> ...]"
    echo "Run UDPipe on input raw text files using given UDPipe model."
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
    bold_echo "===> Started at: `date`"
    bold_echo "===> Generating: ${inputtxt%.txt}.conllu"    
    "$UDPIPE_PATH"/src/udpipe --tokenize --tag --parse "$udpipe_model" --input=horizontal "${inputtxt}" >|${inputtxt%.txt}.conllu
    # If you want to keep original sentence splitting (one sentence per line), comment the line above and uncomment the line below
    #"$UDPIPE_PATH"/src/udpipe --tokenize --tokenizer=presegmented --tag --parse "$udpipe_model" --input=horizontal "${inputtxt}" >|${inputtxt%.txt}.conllu
    bold_echo "===> File ready: ${inputtxt%.txt}.conllu"
    bold_echo "===> Finished at: `date`"
done

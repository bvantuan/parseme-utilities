#! /bin/bash
HERE="$(cd "$(dirname "$0")" && pwd)"

set -o nounset    # Using "$UNDEF" var raises error
set -o errexit    # Exit on error, do not continue quietly


usage() {
    echo "Usage: $(basename "$0") <sharedtask-data-path>"
    echo "Gen statistics about all languages"
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
test "$#" -ne 1  && fail "expected 1 positional arg"

input_path="$1"; shift
output_path="./OUT"


########################################


mkdir -p "$output_path"
echo "Writing to: $output_path"


{
    for lang in FR BG CS DE EL ES FA HE HU IT LT MT PL PT RO SL SV TR; do
        if test -f "$input_path/$lang/train.parsemetsv"; then
            for method in Dependency WinGap0 WinGap1 WinGap2; do
                mkdir -p "$output_path/$lang"
                langpath="$input_path/$lang"
                echo "================== lang=$lang method=$method ===============" >&2

                "$HERE/folia2idiomaticityStats.py" --lang=$lang --input "$input_path/$lang/train.parsemetsv" --literal-finding-method="$method"  --out-mwes "$output_path/$lang/mwes.$method.tsv" --out-mweoccurs "$output_path/$lang/mweoccurs.$method.tsv" --out-categories "$output_path/$lang/categories.$method.tsv"
            done
        else
            echo "WARNING: Language not found: $lang" >&2
        fi
    done
} 2> >(tee "$output_path/stderr")

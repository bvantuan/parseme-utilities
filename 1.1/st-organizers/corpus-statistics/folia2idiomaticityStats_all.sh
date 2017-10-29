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

loud_exec() { echo "$@" >&2; "$@"; }


for lang in FR PL PT  EL BG CS DE ES FA HE HU IT LT MT RO SL SV TR; do
    if test -f "$input_path/$lang/train.parsemetsv"; then
        mkdir -p "$output_path/$lang"
        {
            echo "================== lang=$lang ===============" >&2
            loud_exec "$HERE/folia2idiomaticityStats.py" --lang=$lang --input "$input_path/$lang/train.parsemetsv" --literal-finding-method BagOfDeps Dependency UnlabeledDep WindowGap{0,1,2}  --out-mweoccurs "$output_path/$lang/all_mweoccurs.tsv"

            echo "====== Generating PDF with intersection between Dependency and WinGapX for $lang =====" >&2
            loud_exec "$HERE/mweoccur_intersection.py" --lang="$lang" --input "$output_path/$lang/all_mweoccurs.tsv" --output-pdf-idiomat "$output_path/$lang/intersection_idiomat.pdf" --output-pdf-literal "$output_path/$lang/intersection_literal.pdf" >"$output_path/$lang/intersection.tsv"
        } 2> >(tee "$output_path/$lang/stderr.txt")

    else
        echo "WARNING: Language not found: $lang" >&2
    fi
done

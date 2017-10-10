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


for lang in FR EL PL BG CS DE ES FA HE HU IT LT MT PT RO SL SV TR; do
    if test -f "$input_path/$lang/train.parsemetsv"; then
        mkdir -p "$output_path/$lang"
        {
            for method in Dependency BagOfDeps UnlabeledDep WindowGap0 WindowGap1 WindowGap2; do
                mkdir -p "$output_path/$lang/$method"
                langpath="$input_path/$lang"
                echo "================== lang=$lang method=$method ===============" >&2

                loud_exec "$HERE/folia2idiomaticityStats.py" --lang=$lang --input "$input_path/$lang/train.parsemetsv" --literal-finding-method="$method"  --out-mwes "$output_path/$lang/$method/mwes.tsv" --out-mweoccurs "$output_path/$lang/$method/mweoccurs.tsv" --out-categories "$output_path/$lang/$method/categories.tsv"
            done

            if tail -n 1 "$output_path/$lang/Dependency/categories.tsv" | awk '{exit($2==0)}'; then
                echo "====== Generating PDF with intersection between Dependency and WinGapX for $lang =====" >&2
                loud_exec "$HERE/mweoccur_intersection.py" --lang="$lang" --input-dependency "$output_path/$lang/Dependency/mweoccurs.tsv" --input-window "$output_path/$lang/"{UnlabeledDep,BagOfDeps,WindowGap}*"/mweoccurs.tsv" --out "$output_path/$lang/intersection.pdf" >"$output_path/$lang/intersection.tsv"
            fi
        } 2> >(tee "$output_path/$lang/stderr.txt")

    else
        echo "WARNING: Language not found: $lang" >&2
    fi
done

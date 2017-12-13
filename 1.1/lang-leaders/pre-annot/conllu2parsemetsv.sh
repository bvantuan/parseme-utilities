#! /bin/bash
set -o nounset    # Using "$UNDEF" var raises error
set -o errexit    # Exit on error, do not continue quietly


if test "${1:-}" = "--help" || test "${1:-}" = "-h" || test -t 0; then
    echo "Convert CONLL-U (in stdin) to PARSEME TSV format (in stdout)" >&2
    echo '' >&2
    echo 'The PARSEME TSV format contains 4 columns: WordID,Surface,nsp,MWE.' >&2
    echo 'This script also outputs an extra 5th column with a "V" for verbs.' >&2
    echo 'This 5-column TSV can be uploaded to FLAT for annotation.' >&2
    exit 0
fi

perl -pe 's@\r\n?@\n@g' | awk 'BEGIN{FS=OFS="\t"} /^$/ || /^#/ {print; next} {x = ($10=="SpaceAfter=No"?"nsp":"_"); print "'\''"$1, $2, x, "_", ($4=="VERB"?"V":"_")}'

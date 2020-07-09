#!/bin/bash

# This script formats the PARSEME shared task macro-average results into HTML tables for display.
# Parameter:
# $1 = results directory path
#	It is supposed to contain one folder per system; with the .closed or .open extension.
#	Each system folder contains one folder per language, and a results.txt file in it.
#
# As a result, an HTML table is printed to the results.html file in $1
#
# Sample call:
# ./step4-results2html.all.sh ~/shared-task/Gitlab/sharedtask-data-dev/1.1/system-results

LANGUAGES=(DE EL EU FR GA HE HI IT PL PT RO SV TR ZH)
# PHENOMENA=(Unseen-in-train Seen-in-train Variant-of-train Identical-to-train Continuous Discontinuous Multi-token Single-token)
export LC_ALL="en_US.UTF-8" #Needed to rank everything in correct numerical order

# JW 09.07.2020: pairs of phenomena to report in the same table
PHENOMENA_LEFT=(Discontinuous Unseen-in-train Variant-of-train Single-token)
PHENOMENA_RIGHT=(Continuous Seen-in-train Identical-to-train Multi-token)

#Check the number of parameters
if [ $# -ne 1 ]; then
	echo "usage: $0 results-dir"
	echo "   results-dir = directory of system results. It should contain one folder per system, with one folder per language, with a results.txt file in each."
	exit 1
fi

RES_DIR=$1
RES_HTML=$1/macro-ave.html

export LC_ALL="en_US.UTF-8" #Needed by evaluate.py


#Rank and format the global evaluation (for all categories in total). If different systems run for a given language in both tracks, the rankings are done separately.
#As a result, a file named macro-ave-<PH>.<TRACK>.ranked.txt is created for every phenomenon PH and every TRACK
../../lib/formatMacroAve.sh $RES_DIR ${LANGUAGES[*]}

rm -f $RES_HTML

#Print the result table style
echo "<style>" >> $RES_HTML
echo "table, th, td { " >> $RES_HTML
echo "    text-align:center;" >> $RES_HTML
echo "    border-collapse: collapse;" >> $RES_HTML
echo "    border: 1px solid black;" >> $RES_HTML
echo "    padding: 5px;" >> $RES_HTML
echo "}" >> $RES_HTML
echo "</style>" >> $RES_HTML

echo "<h1 id=\"avg\">Cross-lingual macro-averages</h1>" >> $RES_HTML


# Display the general maro-averages
gawk -f ../../lib/macroavegen_unseen2html.gawk $RES_DIR/macro-ave.ranked.txt >> $RES_HTML
# rm $RES_DIR/macro-ave.ranked.txt

# JW 08.07.2020: Separate MWE-based and Token-based macro-average rankings
for TP in MWE Token; do
  # echo "Formatting the global results for $TP..."
  # gawk -f ../../lib/macroaveglobal2html.gawk $TP $RES_DIR/macro-ave-${TP}.ranked.txt >> $RES_HTML
  # rm $RES_DIR/macro-ave-${TP}.ranked.txt
  rm -f $RES_DIR/macro-ave-${TP}.ranked.txt
done

# # Rankings for different phenomena
# for PH in ${PHENOMENA[*]}; do
#   echo "Formatting the global results for $PH..."
#   gawk -f ../../lib/macroave2html.gawk $PH $RES_DIR/macro-ave-${PH}.ranked.txt >> $RES_HTML
#   # rm $RES_DIR/macro-ave-${PH}.ranked.txt
#   # rm -f $RES_DIR/macro-ave-${PH}.ranked.txt #Delete the formatted fileb
# done

# Rankings for different phenomena pairs
for i in "${!PHENOMENA_LEFT[@]}"; do
  PHL=${PHENOMENA_LEFT[$i]}
  PHR=${PHENOMENA_RIGHT[$i]}
  echo "Formatting the global results for $PHL vs $PHR..."

  # paste $RES_DIR/macro-ave-${PHL}.ranked.txt $RES_DIR/macro-ave-${PHR}.ranked.txt > $RES_DIR/macro-ave-${PHL}_${PHR}.ranked.txt

  gawk -f ../../lib/macroave_pair2html.gawk $PHL $PHR $RES_DIR/macro-ave-${PHL}_${PHR}.ranked.txt >> $RES_HTML

#   # rm $RES_DIR/macro-ave-${PH}.ranked.txt
#   # rm -f $RES_DIR/macro-ave-${PH}.ranked.txt #Delete the formatted fileb

  rm -f $RES_DIR/macro-ave-${PHL}_${PHR}.ranked.txt
done

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

PHENOMENA=(Continuous Discontinuous Multi-token Single-token Seen-in-train Unseen-in-train Variant-of-train Identical-to-train)

#Check the number of parameters
if [ $# -ne 1 ]; then
	echo "usage: $0 results-dir"
	echo "   results-dir = directory of system results. It should contain one folder per system, with one folder per language, with a results.txt file in each."
	exit 1
fi

RES_DIR=$1
RES_HTML=$1/macro-ave.html

#Rank and format the global evaluation (for all categories in total). If different systems run for a given language in both tracks, the rankings are done separately.
#As a result, a file named macro-ave-<PH>.<TRACK>.ranked.txt is created for every phenomenon PH and every TRACK
../../lib/formatMacroAve.sh $RES_DIR

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


#Displau=y the geleral maro-averages
gawk -f ../../lib/macroavegen2html.gawk $RES_DIR/macro-ave.ranked.txt >> $RES_HTML
#rm $RES_DIR/macro-ave.ranked.txt

for PH in ${PHENOMENA[*]}; do 
	echo "Formatting the global results for $PH..."
	gawk -f ../../lib/macroave2html.gawk $PH $RES_DIR/macro-ave-${PH}.ranked.txt >> $RES_HTML
	rm $RES_DIR/macro-ave-${PH}.ranked.txt
	#rm -f $RES_DIR/macro-ave-${PH}.ranked.txt #Delete the formatted fileb
done


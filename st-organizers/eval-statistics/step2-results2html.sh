#!/bin/bash

# This script formats the PARSEME shared task evaluation results into HTML tables for display.
# Parameter:
# $1 = results directory path
#	It is supposed to contain one folder per system; with the .closed or .open extension.
#	Each system folder contains one folder per language, and a results.txt file in it.
#
# As a result, an HTML table is printed to the results.html file in $1
#
# Sample call:
# ./step2-results2html.all.sh ~/shared-task/Gitlab/sharedtask-data-dev/1.1/system-results

#LANGUAGES=(AR BG DE EL EN ES EU FA FR HE HI HR HU IT LT PL PT RO SL TR)
#LANGUAGES=(BG DE EL EN ES EU FA FR HE HI HR HU IT LT PL PT RO SL TR)
LANGUAGES=(DE EL EU FR GA HE HI IT PL PT RO SV TR ZH)

#Check the number of parameters
if [ $# -ne 1 ]; then
	echo "usage: $0 results-dir"
	echo "   results-dir = directory of system results. It should contain one folder per system, with one folder per language, with a results.txt file in each."
	exit 1
fi

RES_DIR=$1
RES_HTML=$1/results.html

#Rank and format the global evaluation (for all categories in total). If different systems run for a given language in both tracks, the rankings are done separately.
#As a result, a file named <LANG>.ranked.txt is created for every language in $1, containing ranked results of all systems for this language
../../lib/formatEvalResults.sh $RES_DIR ${LANGUAGES[*]}

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

echo "<h1 id=\"lang\">Language-specific system rankings</h1>" >> $RES_HTML

# ?? instead of * because macro-ave.ranked.txt may be present
for f in `ls $RES_DIR/??.ranked.txt`; do
	#Get the language code
	fname=`echo $f | sed 's/.*\///g'`
	lang=${fname:0:2}
	echo "Formatting the global results for $lang..."
	gawk -f ../../lib/results2html.gawk $lang $f >> $RES_HTML
done

#Delete the formatted results
for LANG in ${LANGUAGES[*]}; do
	rm -f $RES_DIR/$LANG.ranked.txt
done

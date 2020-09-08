#!/bin/bash

# This script formats the PARSEME shared task evaluation results per category into HTML tables for display.
# Parameter:
# $1 = results directory path
#	It is supposed to contain one folder per system; with the .closed or .open extension.
#	Each system folder contains one folder per language, and one test.system.cupt file in it.
#
# The HTML table is printed to the results-cat.html file in $1


LANGUAGES=(DE EL EU FR GA HE HI IT PL PT RO SV TR ZH)
#LANGUAGES=(AR BG DE EL EN ES EU FA FR HE HI HR HU IT LT PL PT RO SL TR)

export LC_ALL="en_US.UTF-8" #Needed to rank everything in correct numerical order

#Check the number of parameters
if [ $# -ne 1 ]; then
	echo "usage: $0 results-dir"
	echo "   results-dir = directory of system results. It should contain one folder per system, with one folder per language, with a results.txt file in each."
	exit 1
fi

RES_DIR=$1
RES_HTML=$1/results-cat.html

#Format the (unranked) per-category evaluation results.
#As a result, a file named <LANG>.percat.txt is created for every language in $1, containing (unranked) results of all systems for this language:
../../lib/formatEvalResults-cat.sh $RES_DIR ${LANGUAGES[*]}

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

echo "<h1 id=\"cat\">Results per VMWE category (not ranked)</h1>" >> $RES_HTML


for f in `ls $RES_DIR/*.percat.txt`; do

	#Get the language code
	fname=`echo $f | sed 's/.*\///g'`
	lang=${fname:0:2}
#	echo "LANG=$lang"
	echo "Formatting the per-category results for $lang..."
	gawk -f ../../lib/results2html-cat.gawk $lang $f >> $RES_HTML
done

#Delete the formatted results
for LANG in ${LANGUAGES[*]}; do
	rm -f $RES_DIR/$LANG.percat.txt
done

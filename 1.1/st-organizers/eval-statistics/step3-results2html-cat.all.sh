#!/bin/bash

# This script formats the PARSEME shared task evaluation results per category into HTML tables for display.
# Parameters:
# $1 = results directory path
#	It is supposed to contain one folder per system; with the .closed or .open extension.
#	Each system folder contains one folder per language, and one test.system.cupt file in it.
# $2 = gold data directory path
#	It is supposed to contain one folder per language. 
#	Each of them should contain the SPLIT/test.cupt file with the gold version of the test data.
#
# The HTML table is printed to the results-cat.html file in $1
#
# Sample call:
# ./step3-results2html-cat.all.sh ~/shared-task/Gitlab/sharedtask-data-dev/1.1/system-results  ~/shared-task/Gitlab/sharedtask-data-dev/1.1/preliminary-sharedtask-data/

#Check the number of parameters
if [ $# -ne 2 ]; then
	echo "usage: $0 results-dir gold-data-dir"
	echo "   results-dir = directory of system results. It should contain one folder per system, with one folder per language, with one test.system.parsemetsv file in each."
	echo "   gold-data-dir = directory with the test gold data. It should contain one folder per language, with the SPLIT/test.cupt file in each."
	exit 1
fi

#Format the (unranked) per-category evaluation results.
#As a result, a file named <LANG>.percat.txt is created for every language in $1, containing (unranked) results of all systems for this language:
../../lib/formatEvalResults-cat.sh $1 $2

rm -f $1/results-cat.html

#Print the result table style
echo "<style>" >> $1/results-cat.html
echo "table, th, td { " >> $1/results-cat.html
echo "    text-align:center;" >> $1/results-cat.html
echo "    border-collapse: collapse;" >> $1/results-cat.html
echo "    border: 1px solid black;" >> $1/results-cat.html
echo "    padding: 5px;" >> $1/results-cat.html
echo "}" >> $1/results-cat.html
echo "</style>" >> $1/results-cat.html


for f in `ls $1/*.percat.txt`; do 

	#Get the language code
	fname=`echo $f | sed 's/.*\///g'` 
	lang=${fname:0:2}
#	echo "LANG=$lang"
	echo "Formatting the per-category results for $lang..."
	gawk -f ../../lib/results2html-cat.gawk $lang $f >> $1/results-cat.html
done

#Delete the formatted results
for LANG in ${LANGUAGES[*]}; do
	rm -f $1/$LANG.percat.txt
done



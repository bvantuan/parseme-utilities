#!/bin/bash

#This script formats the PARSEME shared task evaluation results per category into HTML tables for display.
#Parameters:
# $1 = results directory (should contain a XX.ranked.txt file for each language)
#
# The HTML table is printed to the results-cat.html file in $1
#
# Sample call:
# ./step5-results2html-cat.all.sh ~/shared-task/Gitlab/sharedtask-data-dev/1.1/system-results

#Check the number of parameters
if [ $# -ne 1 ]; then
	echo "usage: $0 results-dir"
	echo "   results-dir = directory of system results. It should contain a XX.ranked.txt file for each language."
	exit 1
fi

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

	gawk -f ../../lib/results2html-cat.gawk $lang $f >> $1/results-cat.html
done




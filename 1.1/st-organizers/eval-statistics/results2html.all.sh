#!/bin/bash

#This script formats the PARSEME shared task evaluation results into HTML tables for display.
#Parameters:
# $1 = results directory (should contain a XX.ranked.txt file for each language)
#
# The HTML table is printed to the results.html file in $1

#Check the number of parameters
if [ $# -ne 1 ]; then
	echo "usage: $0 results-dir"
	echo "   results-dir = directory of system results. It should contain a XX.ranked.txt file for each language."
	exit 1
fi

rm -f $1/results.html

#Print the result table style
echo "<style>" >> $1/results.html
echo "table, th, td { " >> $1/results.html
echo "    text-align:center;" >> $1/results.html
echo "    border-collapse: collapse;" >> $1/results.html
echo "    border: 1px solid black;" >> $1/results.html
echo "    padding: 5px;" >> $1/results.html
echo "}" >> $1/results.html
echo "</style>" >> $1/results.html


for f in `ls $1/*.ranked.txt`; do 

	#Get the language code
	fname=`echo $f | sed 's/.*\///g'` 
	lang=${fname:0:2}
#	echo "LANG=$lang"

	gawk -f results2html.gawk $lang $f >> $1results.html
done




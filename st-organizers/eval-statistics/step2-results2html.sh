#!/bin/bash

# This script formats the PARSEME shared task evaluation results into HTML tables for display.
# Parameter:
# $1 = results directory path
#	It is supposed to contain one folder per system; with the .closed or .open extension.
#	Each system folder contains one folder per language, and a results.txt file in it.
#
# As a result, an HTML table is printed to the results.html file in $1
# Alternatively, results-traindev.html contains the same data but unseen are considered wrt. train+dev

LANGUAGES=(DE EL EU FR GA HE HI IT PL PT RO SV TR ZH)

export LC_ALL="en_US.UTF-8" #Needed to rank everything in correct numerical order

#Check the number of parameters
if [ $# -ne 1 ]; then
	echo "usage: $0 results-dir"
	echo "   results-dir = directory of system results. It should contain one folder per system, with one folder per language, with a results.txt file in each."
	exit 1
fi

RES_DIR=$1

#Rank and format the global evaluation (for all categories in total). If different systems run for a given language in both tracks, the rankings are done separately.
#As a result, a file named <LANG>.ranked.txt is created for every language in $1, containing ranked results of all systems for this language
../../lib/formatEvalResults.sh $RES_DIR TRAIN ${LANGUAGES[*]}
#Same as above, but now consider unseen wrt. train+dev instead of train
../../lib/formatEvalResults.sh $RES_DIR TRAINDEV ${LANGUAGES[*]}

########################################################################
formatResults(){
	RES_HTML=$1 # File where to store the results in HTML format
	TRAINDEV=$2 # Use regular version or "-traindev" version of results
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
	for f in `ls $RES_DIR/??$TRAINDEV.ranked.txt`; do
		#Get the language code
		fname=`echo $f | sed 's/.*\///g'`
		lang=${fname:0:2}
		echo "Formatting the global results for $lang..."
		gawk -f ../../lib/results2html.gawk $lang $f >> $RES_HTML
	done

	#Delete the formatted results
	for LANG in ${LANGUAGES[*]}; do
		rm -f $RES_DIR/$LANG${TRAINDEV}.ranked.txt
	done
}
########################################################################

formatResults $1/results.html ""
formatResults $1/results-traindev.html "-traindev"


#!/bin/bash

#This script formats the PARSEME shared task general (i.e. not phenomenon-specific) evaluation results for display.
# 3 types of tables are created:
#	* per language disregarding VMWE categories
#	* per language, including VMWE categories
#	* per system, including VMWE categories
#Parameter:
# $1 = results directory path
#	It is supposed to contain one folder per system; with the .closed or .open extension.
#	Each system folder contains one folder per language, and one test.system.cupt file in it.
# $2 = TRAIN or TRAINDEV -- results on unseen wrt. train (TRAIN) or wrt. train+dev (TRAINDEV)
# $3... = language codes
# A list of language codes covered
# As a result, a file named <LANG>.ranked.txt is created for every language in $1, containing ranked results of all systems for this language.

source ../../lib/parseme_st_data_dev_path.bash #Define the PARSEME_SHAREDTASK_DATA_DEV variable
LANGUAGES=${@:3} # parameters $@ after the 3rd


##############################################################################
# Get the evaluation results for a given system and a given language
# Parameters:
# $1 = language code (BG for Bulgarian, EL for Greek, etc.)
# $2... = path to the system directory
# If the system submitted results for the given language, they are printed on standard output in one line:
#   language system track P-mwe R-mwe F-mwe P-token R-token F-token
# X-mwe is a MWE-based result; X-token is a token-based result
# Otherwise nothing is printed.
getResultsLanSys() {
	LANG=$1
	SYS_PATH=$2
	TRAINDEV=$3
	SDIR=`echo $SYS_PATH | sed 's/.*\///g'` #get the system directory name
	SNAME=${SDIR%.*}  #Get the system name (directory prefix without .open or .closed)
	STRACK=${SDIR#*.} #Get the track (directory suffix: open or closed)
	PRED=$SYS_PATH/$LANG/test.system.cupt #Get the expected results file name

	#Check if the system submitted results
	if [ -f $PRED ]; then
		cat $SYS_PATH/$LANG/results${TRAINDEV}.txt > results.txt
		P_UNSEEN=`grep Unseen.*F= results.txt | cut -d ' ' -f4 | cut -d= -f3 | awk '{print $0 * 100}'`
		R_UNSEEN=`grep Unseen.*F= results.txt | cut -d ' ' -f5 | cut -d= -f3 | awk '{print $0 * 100}'`
		F_UNSEEN=`grep Unseen.*F= results.txt | cut -d ' ' -f6 | cut -d= -f2 | awk '{print $0 * 100}'`
		P_MWE=`cat results.txt | head -2 | tail -1 | cut -d' ' -f3 | cut -d= -f3 | awk '{print $0 * 100}'`
		R_MWE=`cat results.txt | head -2 | tail -1 | cut -d' ' -f4 | cut -d= -f3 | awk '{print $0 * 100}'`
		F_MWE=`cat results.txt | head -2 | tail -1 | cut -d' ' -f5 | cut -d= -f2 | awk '{print $0 * 100}'`
		P_TOKEN=`cat results.txt | head -3 | tail -1 | cut -d' ' -f3 | cut -d= -f3 | awk '{print $0 * 100}'`
		R_TOKEN=`cat results.txt | head -3 | tail -1 | cut -d' ' -f4 | cut -d= -f3 | awk '{print $0 * 100}'`
		F_TOKEN=`cat results.txt | head -3 | tail -1 | cut -d' ' -f5 | cut -d= -f2 | awk '{print $0 * 100}'`
		rm results.txt
		echo "$LANG $SNAME $STRACK $P_UNSEEN $R_UNSEEN $F_UNSEEN $P_MWE $R_MWE $F_MWE $P_TOKEN $R_TOKEN $F_TOKEN"
	fi
}

##############################################################################
# Make the ranking of the systems per language and per track
# Parameters:
#  $1 = results directory path
#  $2 = suffix "" or "-traindev"
# Sorts the result files according to F-measure (both token-based and MWE-based)
makeRanking() {
	RESDIR=$1
	TRAINDEV=$2
	for LANG in ${LANGUAGES[*]}; do
		#Initiate the ranking file
		echo "System Track P-token R-token F-token P-MWE R-MWE F-MWE P-unseen R-unseen F-unseen Rank-token Rank-MWE Rank-unseen" > ${RESDIR}/${LANG}${TRAINDEV}.ranked.txt 
		for TRACK in `echo closed open`; do
			# echo "Processing $LANG.$TRACK.txt"
			if [ -f ${RESDIR}/${LANG}${TRAINDEV}.${TRACK}.txt ]; then
				#Rank the systems according to 2 measures. If a system F-measure is 0, the ranking is not applicable
				cat ${RESDIR}/${LANG}${TRAINDEV}.${TRACK}.txt |
		  sort -nr --key=5 | gawk 'BEGIN{prev=-1}{if(prev != $5){r++} prev=$5; if ($5=="0") print $0, "n/a"; else print $0, r; }' |
		  sort -nr --key=8 | gawk 'BEGIN{prev=-1}{if(prev != $8){r++} prev=$8; if ($8=="0") print $0, "n/a"; else print $0, r; }' |
				sort -nr --key=11 | gawk 'BEGIN{prev=-1}{if(prev != $11){r++} prev=$8; if ($11=="0") print $0, "n/a"; else print $0, r; }' |
		  sort -nr --key=5 |
		  cat >> ${RESDIR}/${LANG}${TRAINDEV}.ranked.txt
				rm -f ${RESDIR}/${LANG}${TRAINDEV}.${TRACK}.txt
			fi
		done
	done
}

##############################################################################

usage() {	
	echo "usage: $1 results-dir train-or-traindev lang1 lang2 ..."
	echo "   results-dir = directory of system results. It should contain one folder per system, with one folder per language, with a results.txt file in each."
	echo "   train-or-traindev = TRAIN (unseen wrt. train) or TRAINDEV (unseen wrt. train+dev)"
	echo "   lang1 lang2 ... = language codes of the languages covered."
	exit 1
}

##############################################################################
# Main script

#Check the number of parameters
if [ $# -lt 3 ]; then
	usage $0
fi
RESULTS_DIR=$1
if [ "$2" = "TRAIN" ]; then
	TRAINDEV=""
elif [ "$2" = "TRAINDEV" ]; then
	TRAINDEV="-traindev"
else
	echo "Second parameter \"train-or-traindev\" must be TRAIN or TRAINDEV, found $2"
	usage $0
fi

#Run the evaluation for each language
for LANG in ${LANGUAGES[*]}; do
	#Initiate the results file for a language
	rm -f $RESULTS_DIR/${LANG}${TRAINDEV}.open.txt
	rm -f $RESULTS_DIR/${LANG}${TRAINDEV}.closed.txt
	#For a given language, evaluate each system
	for SYS_DIR in `ls $RESULTS_DIR | grep -E '(closed)|(open)$'`; do
		#Run the evaluation for the given language and system
		if [ -d $RESULTS_DIR/$SYS_DIR/$LANG ]; then
			res=`getResultsLanSys $LANG $RESULTS_DIR/$SYS_DIR $TRAINDEV`
			#echo "res=$res"
			if [ "$res" != "" ]; then
				#Print to the result files for the language
				TRACK=`echo $res | cut -d' ' -f3`
				echo $res | cut -d' ' -f2-12 >> $RESULTS_DIR/${LANG}${TRAINDEV}.${TRACK}.txt
			fi
		fi
	done
done

#Make rankings
makeRanking $RESULTS_DIR $TRAINDEV

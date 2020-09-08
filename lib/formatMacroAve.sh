#!/bin/bash

#This script formats the PARSEME shared task macro average evaluation results for display.
# Parameter:
#  $1 = results directory path
#	It is supposed to contain one folder per system; with the .closed or .open extension.
#	Each system folder contains one folder per language, and one test.system.cupt file in it.
# $2 = TRAIN or TRAINDEV -- results on unseen wrt. train (TRAIN) or wrt. train+dev (TRAINDEV)
# $3... = language codes
# A list of language codes covered
# As a result, files named macro-ave-<PhenomenaLeft>_<PhenomenaRight>.{open,closed}.txt are 
# created in $1, containing ranked global average results per phenomenon pair (e.g. Unseen-in-train 
# vs Seen-in-train) of all systems for each track.

source ../../lib/parseme_st_data_dev_path.bash #Define the PARSEME_SHAREDTASK_DATA_DEV variable
LANGUAGES=${@:3}
MACRO_AVE="$PARSEME_SHAREDTASK_DATA_DEV/bin/average_of_evaluations.py" #Script for calculating macro-averages

# JW 09.07.2020: pairs of phenomena to report in the same table
PHENOMENA_LEFT=(Discontinuous Unseen-in-train Variant-of-train Single-token)
PHENOMENA_RIGHT=(Continuous Seen-in-train Identical-to-train Multi-token)

##############################################################################
# Format the global average results for a given system
# Parameter:
#  $1 = path to the system directory
#  $2 = suffix "" or "-traindev"
#
# The formatted results are printed on standard output in one line:
#   language system track
#   ave-P-mwe ave-R-mwe ave-F-mwe ave-P-token ave-R-token ave-F-token
#   ave-unseen-P-mwe ave-unseen-R-mwe ave-unseen-F-mwe
#   ave-seen-P-mwe ave-seen-R-mwe ave-seen-F-mwe
#   ave-variant-P-mwe ave-variant-R-mwe ave-variant-F-mwe
#   ave-identical-P-mwe ave-identical-R-mwe ave-identical-F-mwe
#   ave-cont-P-mwe ave-cont-R-mwe ave-cont-F-mwe
#   ave-disc-P-mwe ave-disc-R-mwe ave-disc-F-mwe
#   ave-multitoken-P-mwe ave-multitoken-R-mwe ave-multitoken-F-mwe
#   ave-onetoken-P-mwe ave-onetoken-R-mwe ave-onetoken-F-mwe
# where X-mwe is a MWE-based result. Token-based results are not calculated.
getResultsSys() {
	SYS_PATH=$1
	TRAINDEV=$2
	SDIR=`echo $SYS_PATH | sed 's/.*\///g'` #get the system directory name
	SNAME=${SDIR%.*}  #Get the system name (directory prefix without .open or .closed)
	STRACK=${SDIR#*.} #Get the track (directory suffix: open or closed)
	DUMMIES=""
	DUMMIESNOSINGLE=""
	
	submitted=0
	total=0
	for lang in ${LANGUAGES[*]}; do
	  if [ ! -f ${SYS_PATH}/${lang}/results${TRAINDEV}.txt ]; then
		DUMMIES="$DUMMIES $SYS_PATH/../dummy/$lang/results${TRAINDEV}.txt"
		DUMMIESNOSINGLE="$DUMMIESNOSINGLE $SYS_PATH/../dummy/$lang/results${TRAINDEV}.txt.nosingle"
	  else
		(( submitted++ ))
	  fi
	  (( total++ ))
	done

	# Ugly workaround to ignore languages that do not have single-token VMWEs
	for a in $SYS_PATH/*/results${TRAINDEV}.txt $DUMMIES; do
	  sed -e '/Single-token.*R=[0-9]*\/0=/d' -e '/Single-token.*gold=0\//d' $a > $a.nosingle
	done

	#Get the macro-average for the system for all languages
	$MACRO_AVE --operation avg $SYS_PATH/*/results${TRAINDEV}.txt.nosingle $DUMMIESNOSINGLE > $SYS_PATH/ave-results.txt

	#General macro-averages
	AVE_P_MWE=`cat $SYS_PATH/ave-results.txt | grep '* MWE-based' | cut -d' ' -f3 | cut -d= -f2 | awk '{print $0*100}'`
	AVE_R_MWE=`cat $SYS_PATH/ave-results.txt | grep '* MWE-based' | cut -d' ' -f4 | cut -d= -f2 | awk '{print $0*100}'`
	AVE_F_MWE=`cat $SYS_PATH/ave-results.txt | grep '* MWE-based' | cut -d' ' -f5 | cut -d= -f2 | awk '{print $0*100}'`
	AVE_P_TOKEN=`cat $SYS_PATH/ave-results.txt | grep '* Tok-based' | cut -d' ' -f3 | cut -d= -f2 | awk '{print $0*100}'`
	AVE_R_TOKEN=`cat $SYS_PATH/ave-results.txt | grep '* Tok-based' | cut -d' ' -f4 | cut -d= -f2 | awk '{print $0*100}'`
	AVE_F_TOKEN=`cat $SYS_PATH/ave-results.txt | grep '* Tok-based' | cut -d' ' -f5 | cut -d= -f2 | awk '{print $0*100}'`
	# JW 08.07.2020: Add unseen results
	AVE_P_UNSEEN=`grep Unseen.*F= $SYS_PATH/ave-results.txt | cut -d ' ' -f4 | cut -d= -f2 | awk '{print $0 * 100}'`
	AVE_R_UNSEEN=`grep Unseen.*F= $SYS_PATH/ave-results.txt | cut -d ' ' -f5 | cut -d= -f2 | awk '{print $0 * 100}'`
	AVE_F_UNSEEN=`grep Unseen.*F= $SYS_PATH/ave-results.txt | cut -d ' ' -f6 | cut -d= -f2 | awk '{print $0 * 100}'`

	echo "$SNAME $STRACK $AVE_P_MWE $AVE_R_MWE $AVE_F_MWE $AVE_P_TOKEN $AVE_R_TOKEN $AVE_F_TOKEN $AVE_P_UNSEEN $AVE_R_UNSEEN $AVE_F_UNSEEN $submitted/$total" >> $RESULTS_DIR/macro-ave.${STRACK}.txt

	# JW 08.07.2020: Separate MWE-based and Token-based macro-averages
	echo "$SNAME $STRACK $AVE_P_MWE $AVE_R_MWE $AVE_F_MWE $submitted/$total" >> $RESULTS_DIR/macro-ave-MWE.${STRACK}.txt
	echo "$SNAME $STRACK $AVE_P_TOKEN $AVE_R_TOKEN $AVE_F_TOKEN $submitted/$total" >> $RESULTS_DIR/macro-ave-Token.${STRACK}.txt

	for i in "${!PHENOMENA_LEFT[@]}"; do
	  PHL=${PHENOMENA_LEFT[$i]}
	  PHR=${PHENOMENA_RIGHT[$i]}

	  L_AVE_P_MWE=`cat $SYS_PATH/ave-results.txt | grep "* $PHL: MWE-based" | cut -d' ' -f4 | cut -d= -f2 | awk '{print $0*100}'`
	  L_AVE_R_MWE=`cat $SYS_PATH/ave-results.txt | grep "* $PHL: MWE-based" | cut -d' ' -f5 | cut -d= -f2 | awk '{print $0*100}'`
	  L_AVE_F_MWE=`cat $SYS_PATH/ave-results.txt | grep "* $PHL: MWE-based" | cut -d' ' -f6 | cut -d= -f2  | awk '{print $0*100}'`
	  L_AVE_LANGS=`cat $SYS_PATH/ave-results.txt | grep "* $PHL: MWE-based" | cut -d' ' -f8 | sed 's%@(\([0-9]*\)/.*)%\1%g'`
	  L_SUB_LANGS=`cat $SYS_PATH/*/results${TRAINDEV}.txt | grep "* $PHL: MWE-based" | wc -l | awk '{print $1}'`

	  R_AVE_P_MWE=`cat $SYS_PATH/ave-results.txt | grep "* $PHR: MWE-based" | cut -d' ' -f4 | cut -d= -f2 | awk '{print $0*100}'`
	  R_AVE_R_MWE=`cat $SYS_PATH/ave-results.txt | grep "* $PHR: MWE-based" | cut -d' ' -f5 | cut -d= -f2 | awk '{print $0*100}'`
	  R_AVE_F_MWE=`cat $SYS_PATH/ave-results.txt | grep "* $PHR: MWE-based" | cut -d' ' -f6 | cut -d= -f2  | awk '{print $0*100}'`
	  R_AVE_LANGS=`cat $SYS_PATH/ave-results.txt | grep "* $PHR: MWE-based" | cut -d' ' -f8 | sed 's%@(\([0-9]*\)/.*)%\1%g'`
	  R_SUB_LANGS=`cat $SYS_PATH/*/results${TRAINDEV}.txt | grep "* $PHR: MWE-based" | wc -l | awk '{print $1}'`

	  L_AVE_LANGS=`cat $SYS_PATH/ave-results.txt | grep "* $PHL: MWE-based" | cut -d' ' -f8 | sed 's%@(\([0-9]*\)/.*)%\1%g'`
	  L_SUB_LANGS=`cat $SYS_PATH/*/results${TRAINDEV}.txt.nosingle | grep "* $PHL: MWE-based" | wc -l | awk '{print $1}'`

	  R_AVE_LANGS_TEST=`cat $SYS_PATH/ave-results.txt | grep "* $PHR: MWE-based" | cut -d' ' -f8 | sed 's%@(\([0-9]*\)/.*)%\1%g'`
	  R_SUB_LANGS_TEST=`cat $SYS_PATH/*/results${TRAINDEV}.txt | grep "* $PHR: MWE-based" | wc -l | awk '{print $1}'`

	  echo "$SNAME $STRACK $L_AVE_P_MWE $L_AVE_R_MWE $L_AVE_F_MWE $R_AVE_P_MWE $R_AVE_R_MWE $R_AVE_F_MWE $L_SUB_LANGS/$L_AVE_LANGS $R_SUB_LANGS/$R_AVE_LANGS" >> $RESULTS_DIR/macro-ave-${PHL}_${PHR}.${STRACK}.txt
	done

	# Ugly workaround to ignore languages that do not have single-token VMWEs
	for a in $SYS_PATH/*/results${TRAINDEV}.txt.nosingle $DUMMIESNOSINGLE; do
	  rm $a
	done

}

##############################################################################
# Make the macro-average ranking of the systems per track
# Parameters:
#  $1 = results directory path
#  $2 = suffix "" or "-traindev"
# Sorts the result files according to F-measure (both token-based and MWE-based)
makeRanking() {
	RESULTS_DIR=$1
	TRAINDEV=$2

	# JW 08.07.2020: Add unseen results
	#Rank general macro-averages
	echo "system track ave-P-mwe ave-R-mwe ave-F-mwe ave-P-token ave-R-token ave-F-token ave-P-unseen ave-R-unseen ave-F-unseen langs rank-unseen rank-MWE rank-token" > $RESULTS_DIR/macro-ave.ranked.txt

	# JW 08.07.2020: Separate MWE-based and Token-based macro-averages
	echo "system track ave-P-mwe ave-R-mwe ave-F-mwe rank" > $RESULTS_DIR/macro-ave-MWE.ranked.txt #Initiate the ranking file
	echo "system track ave-P-token ave-R-token ave-F-token rank" > $RESULTS_DIR/macro-ave-Token.ranked.txt #Initiate the ranking file

	for i in "${!PHENOMENA_LEFT[@]}"; do
	  PHL=${PHENOMENA_LEFT[$i]}
	  PHR=${PHENOMENA_RIGHT[$i]}
	  echo "system track l-ave-P-mwe l-ave-R-mwe l-ave-F-mwe r-ave-P-mwe r-ave-R-mwe r-ave-F-mwe l-langs r-langs l-rank r-rank" > $RESULTS_DIR/macro-ave-${PHL}_${PHR}.ranked.txt #Initiate the ranking file
	done

	for TRACK in closed open; do
	  #Rank macro-averages
	  cat $RESULTS_DIR/macro-ave.${TRACK}.txt |
		sort -s -nr --key=11 | gawk 'BEGIN{prev=-1}{if(prev != $11){r++} prev=$8; if ($11=="0") print $0, "n/a"; else print $0, r; }' |
		sort -s -nr --key=5 | gawk 'BEGIN{prev=-1}{if(prev != $5){r++} prev=$5; if ($5=="0") print $0, "n/a"; else print $0, r; }' |
		sort -s -nr --key=8 | gawk 'BEGIN{prev=-1}{if(prev != $8){r++} prev=$8; if ($8=="0") print $0, "n/a"; else print $0, r; }' |
		sort -s -nr --key=11 |
		cat >> $RESULTS_DIR/macro-ave.ranked.txt
	  rm $RESULTS_DIR/macro-ave.${TRACK}.txt

	  # JW 08.07.2020: Rank MWE-based and Token-based macro-averages separately
	  for TP in MWE Token; do
		cat $RESULTS_DIR/macro-ave-${TP}.${TRACK}.txt |
		  sort -s -nr --key=5 | gawk 'BEGIN{prev=-1}{if(prev != $5){r++} prev=$5; if ($5=="0") print $0, "n/a"; else print $0, r; }' |
		  cat >> $RESULTS_DIR/macro-ave-${TP}.ranked.txt
		rm $RESULTS_DIR/macro-ave-${TP}.${TRACK}.txt
	  done

	  #Rank per-phenomenon macro-averages
	  for i in "${!PHENOMENA_LEFT[@]}"; do
		PHL=${PHENOMENA_LEFT[$i]}
		PHR=${PHENOMENA_RIGHT[$i]}
		cat $RESULTS_DIR/macro-ave-${PHL}_${PHR}.${TRACK}.txt |
		  sort -s -nr --key=5 | gawk 'BEGIN{prev=-1}{if(prev != $5){r++} prev=$5; if ($5=="0") print $0, "n/a"; else print $0, r; }' |
		  sort -s -nr --key=8 | gawk 'BEGIN{prev=-1}{if(prev != $8){r++} prev=$8; if ($8=="0") print $0, "n/a"; else print $0, r; }' |
		  sort -s -nr --key=5 |
		  cat >> $RESULTS_DIR/macro-ave-${PHL}_${PHR}.ranked.txt
		rm $RESULTS_DIR/macro-ave-${PHL}_${PHR}.${TRACK}.txt
	  done
	done
}

##############################################################################

usage(){
	echo "usage: $1 results-dir train-or-traindev gold-data-dir"
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

echo -n "" > $RESULTS_DIR/macro-ave.open.txt #Initiate the global average results file
echo -n "" > $RESULTS_DIR/macro-ave.closed.txt #Initiate the global average results file
for i in "${!PHENOMENA_LEFT[@]}"; do
  PHL=${PHENOMENA_LEFT[$i]}
  PHR=${PHENOMENA_RIGHT[$i]}
  echo -n "" > $RESULTS_DIR/macro-ave-${PHL}_${PHR}.open.txt
  echo -n "" > $RESULTS_DIR/macro-ave-${PHL}_${PHR}.closed.txt
done

#For a given language, calculate the macro-avergaes for each system
for SYS_DIR in `ls $RESULTS_DIR | grep -E '(closed)|(open)$' | grep -v .txt`; do
	echo "Processing $SYS_DIR"
	#Run the evaluation for the given language and system
	getResultsSys $RESULTS_DIR/$SYS_DIR $TRAINDEV
done

#Make rankings
makeRanking $RESULTS_DIR $TRAINDEV

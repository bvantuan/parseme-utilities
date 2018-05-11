#!/bin/bash

#This script formats the PARSEME shared task macro average evaluation results for display.
# Parameter:
#  $1 = results directory path
#	It is supposed to contain one folder per system; with the .closed or .open extension.
#	Each system folder contains one folder per language, and one test.system.cupt file in it.
#
# As a result, files named macro-ave.closed.txt and macro-ave.open.txt are created in $1, containing ranked global average results of all systems for each track.
#
# Sample run:
# ./formatMacroAve.sh ~/shared-task/Gitlab/sharedtask-data-dev/1.1/system-results

source ../../lib/parseme_st_data_dev_path.bash #Define the PARSEME_SHAREDTASK_DATA_DEV variable
LANGUAGES=(BG DE EL EN ES EU FA FR HE HI HR HU IT LT PL PT RO SL TR)
#LANGUAGES=(AR BG DE EL EN ES EU FA FR HE HI HR HU IT LT PL PT RO SL TR)
PHENOMENA=(Continuous Discontinuous Multi-token Single-token Seen-in-train Unseen-in-train Variant-of-train Identical-to-train)
MACRO_AVE="$PARSEME_SHAREDTASK_DATA_DEV/bin/average_of_evaluations.py" #Script for calculating macro-averages

##############################################################################
# Format the global average results for a given system
# Parameter:
#  $1 = path to the system directory 
#
# The formatted results are printed on standard output in one line:
#   language system track 
#   ave-P-mwe ave-R-mwe ave-F-mwe ave-P-token ave-R-token ave-F-token
#   ave-cont-P-mwe ave-cont-R-mwe ave-cont-F-mwe
#   ave-disc-P-mwe ave-disc-R-mwe ave-disc-F-mwe
#   ave-multitoken-P-mwe ave-multitoken-R-mwe ave-multitoken-F-mwe
#   ave-onetoken-P-mwe ave-onetoken-R-mwe ave-onetoken-F-mwe
#   ave-seen-P-mwe ave-seen-R-mwe ave-seen-F-mwe
#   ave-unseen-P-mwe ave-unseen-R-mwe ave-unseen-F-mwe
#   ave-variant-P-mwe ave-variant-R-mwe ave-variant-F-mwe
#   ave-identical-P-mwe ave-identical-R-mwe ave-identical-F-mwe
# where X-mwe is a MWE-based result. Token-based results are not calculated.
getResultsSys() {

SYS_PATH=$1
SDIR=`echo $SYS_PATH | sed 's/.*\///g'` #get the system directory name
SNAME=${SDIR%.*}  #Get the system name (directory prefix without .open or .closed)
#echo "System name: $SNAME"
STRACK=${SDIR#*.} #Get the track (directory suffix: open or closed)
#echo "System track: $STRACK"

DUMMIES=""
submitted=0
total=0
for lang in ${LANGUAGES[*]}; do
  if [ ! -f ${SYS_PATH}/${lang}/results.txt ]; then
    DUMMIES="$DUMMIES $SYS_PATH/../dummy/$lang/results.txt"
  else
    (( submitted++ ))
  fi
  (( total++ ))
done

# Ugly workaround to ignore languages that do not have single-token VMWEs
for a in $SYS_PATH/*/results.txt $DUMMIES; do 
  sed -i -e '/Single-token.*R=[0-9]*\/0=/d' -e '/Single-token.*gold=0\//d' $a 
done

#Get the macro-average for the system for all languages
#echo "Average over" $SYS_PATH/*/results.txt $DUMMIES > /dev/stderr
$MACRO_AVE --operation avg $SYS_PATH/*/results.txt $DUMMIES > $SYS_PATH/ave-results.txt  
  
#General macro-averages
AVE_P_MWE=`cat $SYS_PATH/ave-results.txt | grep '* MWE-based' | cut -d' ' -f3 | cut -d= -f2 | awk '{print $0*100}'`
AVE_R_MWE=`cat $SYS_PATH/ave-results.txt | grep '* MWE-based' | cut -d' ' -f4 | cut -d= -f2 | awk '{print $0*100}'`
AVE_F_MWE=`cat $SYS_PATH/ave-results.txt | grep '* MWE-based' | cut -d' ' -f5 | cut -d= -f2 | awk '{print $0*100}'`
AVE_P_TOKEN=`cat $SYS_PATH/ave-results.txt | grep '* Tok-based' | cut -d' ' -f3 | cut -d= -f2 | awk '{print $0*100}'`
AVE_R_TOKEN=`cat $SYS_PATH/ave-results.txt | grep '* Tok-based' | cut -d' ' -f4 | cut -d= -f2 | awk '{print $0*100}'`
AVE_F_TOKEN=`cat $SYS_PATH/ave-results.txt | grep '* Tok-based' | cut -d' ' -f5 | cut -d= -f2 | awk '{print $0*100}'`
#AVE_LANGS=`cat $SYS_PATH/ave-results.txt | grep '* MWE-based' | cut -d' ' -f7 | sed 's/[)(@]//g'`
echo "$SNAME $STRACK $AVE_P_MWE $AVE_R_MWE $AVE_F_MWE $AVE_P_TOKEN $AVE_R_TOKEN $AVE_F_TOKEN $total/$submitted" >> $RESULTS_DIR/macro-ave.${STRACK}.txt

#Phenomenon-specific macro-averages
for PH in ${PHENOMENA[*]}; do
	AVE_P_MWE=`cat $SYS_PATH/ave-results.txt | grep "* $PH: MWE-based" | cut -d' ' -f4 | cut -d= -f2 | awk '{print $0*100}'`
	AVE_R_MWE=`cat $SYS_PATH/ave-results.txt | grep "* $PH: MWE-based" | cut -d' ' -f5 | cut -d= -f2 | awk '{print $0*100}'`
	AVE_F_MWE=`cat $SYS_PATH/ave-results.txt | grep "* $PH: MWE-based" | cut -d' ' -f6 | cut -d= -f2  | awk '{print $0*100}'`
  AVE_LANGS=`cat $SYS_PATH/ave-results.txt | grep "* $PH: MWE-based" | cut -d' ' -f8 | sed 's%@(\([0-9]*\)/.*)%\1%g'`
  SUB_LANGS=`cat $SYS_PATH/*/results.txt | grep "* $PH: MWE-based" | wc -l | awk '{print $1}'`
	echo "$SNAME $STRACK $AVE_P_MWE $AVE_R_MWE $AVE_F_MWE $SUB_LANGS/$AVE_LANGS" >> $RESULTS_DIR/macro-ave-${PH}.${STRACK}.txt
done

#rm results.txt
} 

##############################################################################
# Make the macro-average ranking of the systems per track
# Parameters: 
#  $1 = results directory path
# Sorts the result files according to F-measure (both token-based and MWE-based)
makeRanking() {
RESULTS_DIR=$1
#Rank general macro-averages
echo "system track ave-P-mwe ave-R-mwe ave-F-mwe ave-P-token ave-R-token ave-F-token rank-token rank-MWE" > $RESULTS_DIR/macro-ave.ranked.txt
for PH in ${PHENOMENA[*]}; do
		echo "system track ave-P-mwe ave-R-mwe ave-F-mwe rank" > $RESULTS_DIR/macro-ave-${PH}.ranked.txt #Initiate the ranking file
done
for TRACK in closed open; do
	cat $RESULTS_DIR/macro-ave.${TRACK}.txt | 
  sort -nr --key=5 | gawk 'BEGIN{prev=-1}{if(prev != $5){r++} prev=$5; if ($5=="0") print $0, "n/a"; else print $0, r; }' | 
  sort -nr --key=8 | gawk 'BEGIN{prev=-1}{if(prev != $8){r++} prev=$8; if ($8=="0") print $0, "n/a"; else print $0, r; }' |
  sort -nr --key=5 |
  cat  >> $RESULTS_DIR/macro-ave.ranked.txt	
	rm $RESULTS_DIR/macro-ave.${TRACK}.txt
	
	#Rank per-phenomenon macro-averages
	for PH in ${PHENOMENA[*]}; do		
		cat $RESULTS_DIR/macro-ave-${PH}.${TRACK}.txt | 
    sort -nr --key=5 | gawk 'BEGIN{prev=-1}{if(prev != $5){r++} prev=$5; if ($5=="0") print $0, "n/a"; else print $0, r; }' |
    cat >> $RESULTS_DIR/macro-ave-${PH}.ranked.txt	
		rm $RESULTS_DIR/macro-ave-${PH}.${TRACK}.txt
	done
done
}

##############################################################################
# Main script

#Check the number of parameters
if [ $# -ne 1 ]; then
	echo "usage: $0 results-dir"
	echo "   results-dir = directory of system results. It should contain one folder per system, with one folder per language, with a results.txt file in each."
	exit 1
fi

RESULTS_DIR=$1
echo -n "" > $RESULTS_DIR/macro-ave.open.txt #Initiate the global average results file
echo -n "" > $RESULTS_DIR/macro-ave.closed.txt #Initiate the global average results file
for PH in ${PHENOMENA[*]}; do
	echo -n "" > $RESULTS_DIR/macro-ave-${PH}.open.txt
	echo -n "" > $RESULTS_DIR/macro-ave-${PH}.closed.txt
done

#For a given language, calculate the macro-avergaes for each system
for SYS_DIR in `ls $RESULTS_DIR | grep -E '(closed)|(open)$' | grep -v .txt`; do
	echo "Processing $SYS_DIR"
	#Run the evaluation for the given language and system
	getResultsSys $RESULTS_DIR/$SYS_DIR
done

#Make rankings
makeRanking $RESULTS_DIR





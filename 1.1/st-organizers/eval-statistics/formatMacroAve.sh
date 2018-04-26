#!/bin/bash

#This script formats the PARSEME shared task macro average evaluation results for display.
# Parameter:
#  $1 = results directory path
#	It is supposed to contain one folder per system; with the .closed or .open extension.
#	Each system folder contains one folder per language, and one test.system.cupt file in it.
#
# As a result, files named global-ave.closed.txt and global-ave.open.txt are created in $1, containing ranked global average results of all systems for each track.
#
# Sample run:
# ./formatMacroAve.sh ~/shared-task/Gitlab/sharedtask-data-dev/1.1/system-results

source ../../lib/parseme_st_data_dev_path.bash #Define the PARSEME_SHAREDTASK_DATA_DEV variable
LANGUAGES=(AR BG DE EL EN ES EU FA FR HE HI HR HU IT LT PL PT RO SL TR)
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
#   ave-onetoken-P-mwe ave-onetoken-R-mwe ave-onetoken-F-mwe
#   ave-multitoken-P-mwe ave-multitoken-R-mwe ave-multitoken-F-mwe
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

#Get the macro-average for the system for all languages
MACRO_AVE $SYS_PATH/*/results.txt > results.txt

AVE_P_MWE=`cat results.txt | grep '* MWE-based' | cut -d' ' -f3 | cut -d= -f2`
AVE_R_MWE=`cat results.txt | grep '* MWE-based' | cut -d' ' -f4 | cut -d= -f2`
AVE_F_MWE=`cat results.txt | grep '* MWE-based' | cut -d' ' -f5 | cut -d= -f2`
AVE_P_TOKEN=`cat results.txt | grep '* Tok-based' | cut -d' ' -f3 | cut -d= -f2`
AVE_R_TOKEN=`cat results.txt | grep '* Tok-based' | cut -d' ' -f4 | cut -d= -f2`
AVE_F_TOKEN=`cat results.txt | grep '* Tok-based' | cut -d' ' -f5 | cut -d= -f2`

AVE_CONT_P_MWE=`cat results.txt | grep '* Continuous: MWE-based' | cut -d' ' -f4 | cut -d= -f2`
AVE_CONT_R_MWE=`cat results.txt | grep '* Continuous: MWE-based' | cut -d' ' -f5 | cut -d= -f2`
AVE_CONT_F_MWE=`cat results.txt | grep '* Continuous: MWE-based' | cut -d' ' -f6 | cut -d= -f2`
AVE_DISCONT_P_MWE=`cat results.txt | grep '* Discontinuous: MWE-based' | cut -d' ' -f4 | cut -d= -f2`
AVE_DISCONT_R_MWE=`cat results.txt | grep '* Discontinuous: MWE-based' | cut -d' ' -f5 | cut -d= -f2`
AVE_DISCONT_F_MWE=`cat results.txt | grep '* Discontinuous: MWE-based' | cut -d' ' -f6 | cut -d= -f2`

AVE_MULTITOKEN_P_MWE=`cat results.txt | grep '* Multi-token: MWE-based' | cut -d' ' -f4 | cut -d= -f2`
AVE_MULTITOKEN_R_MWE=`cat results.txt | grep '* Multi-token: MWE-based' | cut -d' ' -f5 | cut -d= -f2`
AVE_MULTITOKEN_F_MWE=`cat results.txt | grep '* Multi-token: MWE-based' | cut -d' ' -f6 | cut -d= -f2`
AVE_ONETOKEN_P_MWE=`cat results.txt | grep '* Single-token: MWE-based' | cut -d' ' -f4 | cut -d= -f2`
AVE_ONETOKEN_R_MWE=`cat results.txt | grep '* Single-token: MWE-based' | cut -d' ' -f5 | cut -d= -f2`
AVE_ONETOKEN_F_MWE=`cat results.txt | grep '* Single-token: MWE-based' | cut -d' ' -f6 | cut -d= -f2`

AVE_SEEN_P_MWE=`cat results.txt | grep '* Seen-in-train: MWE-based' | cut -d' ' -f4 | cut -d= -f2`
AVE_SEEN_R_MWE=`cat results.txt | grep '* Seen-in-train: MWE-based' | cut -d' ' -f5 | cut -d= -f2`
AVE_SEEN_F_MWE=`cat results.txt | grep '* Seen-in-train: MWE-based' | cut -d' ' -f6 | cut -d= -f2`
AVE_UNSEEN_P_MWE=`cat results.txt | grep '* Unseen-in-train: MWE-based' | cut -d' ' -f4 | cut -d= -f2`
AVE_UNSEEN_R_MWE=`cat results.txt | grep '* Unseen-in-train: MWE-based' | cut -d' ' -f5 | cut -d= -f2`
AVE_UNSEEN_F_MWE=`cat results.txt | grep '* Unseen-in-train: MWE-based' | cut -d' ' -f6 | cut -d= -f2`

AVE_VARIANT_P_MWE=`cat results.txt | grep '* Variant-of-train: MWE-based' | cut -d' ' -f4 | cut -d= -f2`
AVE_VARIANT_R_MWE=`cat results.txt | grep '* Variant-of-train: MWE-based' | cut -d' ' -f5 | cut -d= -f2`
AVE_VARIANT_F_MWE=`cat results.txt | grep '* Variant-of-train: MWE-based' | cut -d' ' -f6 | cut -d= -f2`
AVE_IDENT_P_MWE=`cat results.txt | grep '* Identical-to-train: MWE-based' | cut -d' ' -f4 | cut -d= -f2`
AVE_IDENT_R_MWE=`cat results.txt | grep '* Identical-to-train: MWE-based' | cut -d' ' -f5 | cut -d= -f2`
AVE_IDENT_F_MWE=`cat results.txt | grep '* Identical-to-train: MWE-based' | cut -d' ' -f6 | cut -d= -f2`

rm results.txt

echo -n "$LANG $SNAME $STRACK "
echo -n "$AVE_P_MWE $AVE_R_MWE $AVE_F_MWE $AVE_P_TOKEN $AVE_R_TOKEN $AVE_F_TOKEN "
echo -n "$AVE_CONT_P_MWE $AVE_CONT_R_MWE $AVE_CONT_F_MWE $AVE_DISCONT_P_MWE $AVE_DISCONT_R_MWE $AVE_DISCONT_F_MWE "
echo -n "$AVE_MULTITOKEN_P_MWE $AVE_MULTITOKEN_R_MWE $AVE_MULTITOKEN_F_MWE $AVE_ONETOKEN_P_MWE $AVE_ONETOKEN_R_MWE $AVE_ONETOKEN_F_MWE "
echo -n "$AVE_SEEN_P_MWE $AVE_SEEN_R_MWE $AVE_SEEN_F_MWE $AVE_UNSEEN_P_MWE $AVE_UNSEEN_R_MWE $AVE_UNSEEN_F_MWE "
echo -n "$AVE_VARIANT_P_MWE $AVE_VARIANT_R_MWE $AVE_VARIANT_F_MWE $AVE_IDENT_P_MWE $AVE_IDENT_R_MWE $AVE_IDENT_F_MWE"

} 

##############################################################################
# Main script

#Check the number of parameters
if [ $# -ne 1 ]; then
	echo "usage: $0 results-dir gold-data-dir"
	echo "   results-dir = directory of system results. It should contain one folder per system, with one folder per language, with a results.txt file in each."
	exit 1
fi

RESULTS_DIR=$1

#For a given language, calculate teh macro-avergaes for each system
for SYS_DIR in `ls $RESULTS_DIR | grep -E '(closed)|(open)$'`; do

	rm -f $RESULTS_DIR/${LANG}.open.txt #Initiate the global average results file

	#Run the evaluation for the given language and system
	res=`getResultsSys $RESULTS_DIR/$SYS_DIR`
	if [ "$res" != "" ]; then
		#Print to the result files for the language
		TRACK=`echo $res | cut -d' ' -f3`
		echo $res | cut -d' ' -f2-9 >> $RESULTS_DIR/global-ave.${TRACK}.txt
	fi
done

#Make rankings
makeRanking $RESULTS_DIR





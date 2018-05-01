#!/bin/bash

#This script formats the PARSEME shared task evaluation results per category for display.
# One file with NO ranking per language is created with the results per category.
# Parameter:
#  $1 = results directory path
#	It is supposed to contain one folder per system; with the .closed or .open extension.
#	Each system folder contains one folder per language, and one test.system.cupt file in it.
# As a result, a file named <LANG>.percat.txt is created for every language in $1, containing (unranked) results of all systems for this language.
#
# Sample call:
#  ./step4-formatEvalResults-cat.sh ~/shared-task/Gitlab/sharedtask-data-dev/1.1/system-results ~/shared-task/Gitlab/sharedtask-data-dev/1.1/preliminary-sharedtask-data/
#
# Author: Agata Savary

source ../../lib/parseme_st_data_dev_path.bash #Define the PARSEME_SHAREDTASK_DATA_DEV variable
LANGUAGES=(AR BG DE EL EN ES EU FA FR HE HI HR HU IT LT PL PT RO SL TR)
CATS=(IAV IRV LVC.full LVC.cause MVC VID VPC.full VPC.semi LS.ICV) #VMWE categories

##############################################################################
# Get the evaluation results for a given system and a given language
# Parameters:
#  $1 = language code (BG for Bulgarian, EL for Greek, etc.)
#  $2 = system directory 
# If the system submitted results for the given language, they are printed standard output in one line:
#   Language System Track P-lvc-full-mwe R-lvc-full-mwe ...
# X-mwe is a MWE-based result; X-token is a token-based result
# Otherwise nothing is printed.
getResultsLanSys() {

LANG=$1
SYS_PATH=$2

SDIR=`echo $SYS_PATH | sed 's/.*\///g'` #get the system directory name
SNAME=${SDIR%.*}  #Get the system name (directory prefix without .open or .closed)
#echo "System name: $SNAME"
STRACK=${SDIR#*.} #Get the track (directory suffix: open or closed)
#echo "System track: $STRACK"
PRED=$SYS_PATH/$LANG/test.system.cupt #Get the expected results file name
#ls -l $PRED

#Check if the system submitted results
if [ -f $PRED ]; then
	echo -n "$LANG $SNAME $STRACK "
	for CAT in ${CATS[*]}; do
		if [ $CAT != "LS.ICV" -o  $LANG == "IT" ]; then
			#echo $CAT
			#Check if the category is relevant for the language
			cat $SYS_PATH/$LANG/results.txt > results.txt
			P_MWE=`cat results.txt | grep "$CAT: MWE-based" | cut -d' ' -f4 | cut -d= -f 3`
			R_MWE=`cat results.txt | grep "$CAT: MWE-based" | cut -d' ' -f5 | cut -d= -f 3`
			F_MWE=`cat results.txt | grep "$CAT: MWE-based" | cut -d' ' -f6 | cut -d= -f 2`
			P_TOKEN=`cat results.txt | grep "$CAT: Tok-based" | cut -d' ' -f4 | cut -d= -f 3`
			R_TOKEN=`cat results.txt | grep "$CAT: Tok-based" | cut -d' ' -f5 | cut -d= -f 3`
			F_TOKEN=`cat results.txt | grep "$CAT: Tok-based" | cut -d' ' -f6 | cut -d= -f 2`
			if [ $P_MWE ]; then  
				echo -n "$P_MWE $R_MWE $F_MWE $P_TOKEN $R_TOKEN $F_TOKEN "
			else
				echo -n "n/a n/a n/a n/a n/a n/a "
			fi
			rm results.txt
		fi
	done
	echo ""
fi
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

#Run the evaluation for each language
for LANG in ${LANGUAGES[*]}; do

	echo "System Track P-lvc-full-mwe R-lvc-full-mwe" \
"P-iav-mwe R-iav-mwe F-iav-mwe P-iav-token R-iav-token F-iav-token" \
"P-irv-mwe R-irv-mwe F-irv-mwe P-irv-token R-irv-token F-ireflv-token" \
"P-lvc-cause-mwe R-lvc-cause-mwe F-lvc-cause-mwe P-lvc-cause-token R-lvc-cause-token F-lvc-cause-token" \
"F-lvc-full-mwe P-lvc-full-token R-lvc-full-token F-lvc-full-token" \ 
"P-mvc-mwe R-mvc-mwe F-mvc-mwe P-mvc-token R-mvc-token F-mvc-token" \
"P-vid-mwe R-vid-mwe F-vid-mwe P-vid-token R-vid-token F-vid-token" \
"P-vpc-full-mwe R-vpc-full-mwe F-vpc-full-mwe P-vpc-full-token R-vpc-full-token F-vpc-full-token" \
"P-vpc-semi-mwe R-vpc-semi-mwe F-vpc-semi-mwe P-vpc-semi-token R-vpc-semi-token F-vpc-semi-token" \
> $RESULTS_DIR/${LANG}.percat.txt

	#For a given language, evaluate each system
	for SYS_DIR in `ls $RESULTS_DIR | grep -E '(closed)|(open)$'`; do
		#Run the evaluation for the given language and system
		res=`getResultsLanSys $LANG $RESULTS_DIR/$SYS_DIR`
		if [ "$res" != "" ]; then
			#Print to the result files for the language
			echo $res | cut -d' ' -f2-100 >> $RESULTS_DIR/${LANG}.percat.txt
		fi
	done
done








#!/bin/bash

#This script formats the PARSEME shared task evaluation results per category for display.
# One file with NO ranking per language is created with the results per category.
# Parameter:
#  $1 = results directory path
#	It is supposed to contain one folder per system; with the .closed or .open extension.
#	Each system folder contains one folder per language, and one test.system.cupt file in it.
# $2... = language codes
# A list of language codes covered
# As a result, a file named <LANG>.percat.txt is created for every language in $1, containing (unranked) results of all systems for this language.
#
# Sample call:
#  ./formatEvalResults-cat.sh ~/shared-task/Gitlab/sharedtask-data-dev/1.1/system-results
#
# Author: Agata Savary

source ../../lib/parseme_st_data_dev_path.bash #Define the PARSEME_SHAREDTASK_DATA_DEV variable
#LANGUAGES=(AR BG DE EL EN ES EU FA FR HE HI HR HU IT LT PL PT RO SL TR)
#LANGUAGES=(BG DE EL EN ES EU FA FR HE HI HR HU IT LT PL PT RO SL TR)
LANGUAGES=${@:2}
CATS=(IAV IRV LVC.cause LVC.full MVC VID VPC.full VPC.semi LS.ICV) #VMWE categories

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
    #echo $CAT
    #Check if the category is relevant for the language
    cat $SYS_PATH/$LANG/results.txt > resultsCat.txt
    P_MWE=`cat resultsCat.txt | grep "$CAT: MWE-based" | cut -d' ' -f4 | cut -d= -f 3 | awk '{print $0 * 100}'`
    R_MWE=`cat resultsCat.txt | grep "$CAT: MWE-based" | cut -d' ' -f5 | cut -d= -f 3 | awk '{print $0 * 100}'`
    F_MWE=`cat resultsCat.txt | grep "$CAT: MWE-based" | cut -d' ' -f6 | cut -d= -f 2 | awk '{print $0 * 100}'`
    P_TOKEN=`cat resultsCat.txt | grep "$CAT: Tok-based" | cut -d' ' -f4 | cut -d= -f 3 | awk '{print $0 * 100}'`
    R_TOKEN=`cat resultsCat.txt | grep "$CAT: Tok-based" | cut -d' ' -f5 | cut -d= -f 3 | awk '{print $0 * 100}'`
    F_TOKEN=`cat resultsCat.txt | grep "$CAT: Tok-based" | cut -d' ' -f6 | cut -d= -f 2 | awk '{print $0 * 100}'`
    if [ $P_MWE ]; then
      echo -n "$P_MWE $R_MWE $F_MWE $P_TOKEN $R_TOKEN $F_TOKEN "
    else
      echo -n "n/a n/a n/a n/a n/a n/a "
    fi
    rm resultsCat.txt
	done
	echo ""
fi
}


##############################################################################
# Main script

#Check the number of parameters
if [ $# -lt 2 ]; then
	echo "usage: $0 results-dir gold-data-dir"
	echo "   results-dir = directory of system results. It should contain one folder per system, with one folder per language, with a results.txt file in each."
	echo "   lang1 lang2 ... = language codes of the languages covered."
	exit 1
fi

RESULTS_DIR=$1

#Run the evaluation for each language
for LANG in ${LANGUAGES[*]}; do
	echo "System Track P-IAV-mwe R-IAV-mwe F-IAV-mwe P-IAV-token R-IAV-token F-IAV-token" \
"P-IRV-mwe R-IRV-mwe F-IRV-mwe P-IRV-token R-IRV-token F-IRV-token" \
"P-LVC.cause-mwe R-LVC.cause-mwe F-LVC.cause-mwe P-LVC.cause-token R-LVC.cause-token F-LVC.cause-token" \
"P-LVC.full-mwe R-LVC.full-mwe F-LVC.full-mwe P-LVC.full-token R-LVC.full-token F-LVC.full-token" \
"P-MVC-mwe R-MVC-mwe F-MVC-mwe P-MVC-token R-MVC-token F-MVC-token" \
"P-VID-mwe R-VID-mwe F-VID-mwe P-VID-token R-VID-token F-VID-token" \
"P-VPC.full-mwe R-VPC.full-mwe F-VPC.full-mwe P-VPC.full-token R-VPC.full-token F-VPC.full-token" \
"P-VPC.semi-mwe R-VPC.semi-mwe F-VPC.semi-mwe P-VPC.semi-token R-VPC.semi-token F-VPC.semi-token" \
"P-LS.ICV-mwe R-LS.ICV-mwe F-LS.ICV-mwe P-LS.ICV-token R-LS.ICV-token F-LS.ICV-token" \
> $RESULTS_DIR/${LANG}.percat.txt.withna

	#For a given language, evaluate each system
	for SYS_DIR in `ls $RESULTS_DIR | grep -E '(closed)|(open)$'`; do
		#Run the evaluation for the given language and system
		res=`getResultsLanSys $LANG $RESULTS_DIR/$SYS_DIR`
		if [ "$res" != "" ]; then
			#Print to the result files for the language
      #echo $res
			echo $res | cut -d' ' -f2-100 >> $RESULTS_DIR/${LANG}.percat.txt.withna
		fi
	done

  # Remove all columns containing n/a
  nlines=`wc -l $RESULTS_DIR/${LANG}.percat.txt.withna | awk '{print $1}'`
  for n in `seq $nlines`; do
    cat $RESULTS_DIR/${LANG}.percat.txt.withna |
    head -n $n | tail -n 1 |
    sed 's/ /\n/g' > $RESULTS_DIR/${LANG}.percat.txt.col${n}
  done
  paste $RESULTS_DIR/${LANG}.percat.txt.col* |
  grep -v "n/a" |
  awk '{for (i=1;i<=NF;i++) {lines[i] = lines[i] $i " "; max=i} }\
       END{for (i=1;i<=max;i++){ print lines[i] }}' > $RESULTS_DIR/${LANG}.percat.txt
  rm $RESULTS_DIR/${LANG}.percat.txt.col*
  rm $RESULTS_DIR/${LANG}.percat.txt.withna
done

#!/bin/bash

#This script runs the PARSEME shared task evaluation script for all systems.
#Parameters:
# $1 = results directory path
#	It is supposed to contain one folder per system; with the .closed or .open extension.
#	Each system folder contains one folder per language, and one test.system.cupt file in it.
# $2 = gold data directory path
#	It is supposed to contain one folder per language.
#	Each of them should contain the test.cupt file with the gold version of the test data.
#
# As a result, a results.txt file, containing the ouput of the evaluation script, is added to every language directory of every system.
#Sample run:
# ./step1-runEval.sh ~/shared-task/Gitlab/sharedtask-data-dev/1.1/system-results ~/shared-task/Gitlab/sharedtask-data-dev/1.1/preliminary-sharedtask-data/
# Author: Agata Savary


source ../../lib/parseme_st_data_dev_path.bash #Define the PARSEME_SHAREDTASK_DATA_DEV variable
CHECK_CUPT="$PARSEME_SHAREDTASK_DATA_DEV/bin/validate_cupt.py" #Format validation script
EVALUATE="$PARSEME_SHAREDTASK_DATA_DEV/bin/evaluate.py"
echo "Using evaluation script: $EVALUATE"
#LANGUAGES=(AR BG DE EL EN ES EU FA FR HE HI HR HU IT LT PL PT RO SL TR)
LANGUAGES=(DE EL EU FR GA HE HI IT PL PT RO SV TR ZH)

export LC_ALL="en_US.UTF-8" #Needed to rank everything in correct numerical order

##############################################################################


#Check the number of parameters
if [ $# -ne 2 ]; then
	echo "usage: $0 results-dir gold-data-dir"
	echo "   results-dir = directory of system results. It should contain one folder per system, with one folder per language, with one test.system.cupt file in each."
	echo "   gold-data-dir = directory with the test gold data. It should contain one folder per language, with the test.cupt gold data a file in each."
	exit 1
fi

RESULTS_DIR=$1
GOLD_DIR=$2
#Run evaluation for each system
for SYS_DIR in `ls $RESULTS_DIR | grep -E '(closed)|(open)$'`; do
	#Run the evaluation for each language for which the system submitted results
	for LANG in ${LANGUAGES[*]}; do
		if [ -d $RESULTS_DIR/$SYS_DIR/$LANG ]; then
			TRAIN=$GOLD_DIR/$LANG/train.cupt #Get the train
			GOLD=$GOLD_DIR/$LANG/test.cupt # Get the gold file
			PRED=$RESULTS_DIR/$SYS_DIR/$LANG/test.system.cupt #Get the system's predictions

			#Run the evaluation
			if [ -f $RESULTS_DIR/$SYS_DIR/$LANG/results.txt ]; then
				rm -rf $RESULTS_DIR/$SYS_DIR/$LANG/results.txt;
			fi
			$EVALUATE --train $TRAIN --gold $GOLD --pred $PRED  > $RESULTS_DIR/$SYS_DIR/$LANG/results.txt
		fi
	done
done

# Create dummy result files for systems not submitting results for a given language
mkdir -p $RESULTS_DIR/dummy
for LANG in ${LANGUAGES[*]}; do
  mkdir -p $RESULTS_DIR/dummy/$LANG
	TRAIN=$GOLD_DIR/$LANG/train.cupt #Get the train
	GOLD=$GOLD_DIR/$LANG/test.cupt # Get the gold file
	sed 's/_$/*/g' $GOLD_DIR/$LANG/test.blind.cupt > $GOLD_DIR/$LANG/test.dummy.cupt
	PRED=$GOLD_DIR/$LANG/test.dummy.cupt #Empty predictions

	#Run the evaluation
	if [ -f $RESULTS_DIR/dummy/$LANG/results.txt ]; then rm -rf $RESULTS_DIR/dummy/$LANG/results.txt; fi
	$EVALUATE --train $TRAIN --gold $GOLD --pred $PRED  > $RESULTS_DIR/dummy/$LANG/results.txt
	rm $GOLD_DIR/$LANG/test.dummy.cupt
done

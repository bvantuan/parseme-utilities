#!/bin/bash

#For the given language, and the given number of unseen MWEs, find the ratio of unseen VMWEs in the test corpus (with respect to train)

#Arguments:
#  $1 = language code (e.g. RO, PL, ...)
#  $2 = number of unseen MWEs to be kept in the test corpus
#  $3 = directory with the ST 1.1 data 

#Sample run for one language:
# ./get-unseen-ratio.sh PL 300 ../../../sharedtask-data/1.1/

#Sample run for all languages
#declare -a LANG=("BG" "DE" "EL" "EU" "FR" "HE" "HR" "HU" "IT" "PL" "PT" "RO" "TR"); for l in "${LANG[@]}"; do ./get-unseen-ratio.sh $l 300 ../../../sharedtask-data/1.1/; done
 
#Check the number of parameters
if [ $# -ne 3 ]; then
	echo "Usage: $0 lang-code unseen st_data_dir"
	echo "   lang-code = language code (e.g. RO, PL, ...)"
	echo "   unseen = number of unseen MWEs to be kept in the test file"     
	echo "   st_data_dir = directory with the ST 1.1 data"     
	echo "For the given language, and the given number of unseen MWEs, )"
	echo "find the ratio of unseen VMWEs in the test corpus (with respect to train)."
	echo "Use the train/dev/test data from the previous ST edition."
	exit
fi

lang=$1
nbUnseen=$2
dataDir=$3
splitDir=split #Directory for temporary corpus splits

if [ ! -d $splitDir ]; then
	mkdir $splitDir
fi

#Get the optimal number of sentences in test for the given number of unseen MWEs
testSize=`python ./split_cupt.py estimate --unseen-mwes $nbUnseen -i $dataDir/$lang/train.cupt $dataDir/$lang/dev.cupt $dataDir/$lang/test.cupt -n 10 | grep -E '^Optimal' | cut -d':' -f2 | cut -d' ' -f2`

#Split the corpus to train and test so that the number of sentences in test and of unseen MWEs are given
#Get the precise number of unseen
finalUnseen=`python ./split_cupt.py split --unseen-mwes $nbUnseen --test-size $testSize -i $dataDir/$lang/train.cupt $3/$1/dev.cupt $dataDir/$lang/test.cupt --train-path $splitDir/$lang-train.cupt --test-path $splitDir/$lang-test.cupt -n 10| grep -E 'unseen MWEs in test:' | cut -d':' -f2 | cut -d' ' -f2`

#Get the ratio of unseen in this split
finalRatio=`python ../../../sharedtask-data/1.1/bin/evaluate.py --train $splitDir/$lang-train.cupt --gold $splitDir/$lang-test.cupt --pred $splitDir/$lang-test.cupt 2> /dev/null | grep -E '^* Unseen-in-train: MWE-proportion' | cut -d'=' -f3 | cut -d'%' -f1`

#Printing the statistics of the final split
echo "$lang -- unseen MWEs in test: $finalUnseen; ratio of unseen in test: $finalRatio%"





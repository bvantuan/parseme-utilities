#!/bin/bash

#This script formats the PARSEME shared task evaluation results for display.
# 3 types tables are created: 
#	* per language disregarding VMWE categories
#	* per language, including VMWE categories
#	* per system, including VMWE categories
#Parameters:
# $1 = results directory path
#	It is supposed to contain one folder per system; with the .closed or .open extension.
#	Each system forlder contains one folder per language, and one test.system.parsemetsv file in it.
# $2 = gold data directory path
#	It is supposed to contain one folder per language. 
#	Each of them should contain the parsemetgz/OUT/test.parsemetsv file with the gold version of the test data.
#

CHECK_PARSEMETSV="./checkParsemeTsvFormat.py"
EVALUATE="./evaluate.py"
LANGUAGES=(BG CS DE EL ES FA FR HE HU IT LT MT PL PT RO SL SV TR)

export LC_ALL="en_US.UTF-8" #Needed by evaluate.py

declare -A RESULTS

##############################################################################
# Get the evaluation results for a given system and a given language
# Parameters:
# $1 = gold data directory path
# $2 = language code (BG for Bulgarian, EL for Greek, etc.)
# $3 = system directory 
#If the system submitted results for the given language, they are printed standard output in one line:
#   language system track P-mwe R-mwe F-mwe P-token R-token F-token
#X-mwe is a MWE-based result; X-token is a token-based result
#Otherwise nothing is printed.
getResultsLanSys() {

#Path to the gold data for the language
GOLD=$1/$LANG/parsemetgz/OUT/test.parsemetsv 
#echo "Gold file: $GOLD"

SDIR=`echo $3 | sed 's/.*\///g'` #get the system directory name
SNAME=${SDIR%.*}  #Get the system name (directory prefix without .open or .closed)
#echo "System name: $SNAME"
STRACK=${SDIR#*.} #Get the track (directory suffix: open or closed)
#echo "System track: $STRACK"
SYS=$3/$LANG/test.system.parsemetsv #Get the expected results file name
#ls -l $SYS

#Check if the system submitted results
if [ -f $SYS ]; then
#echo "System $SNAME submitted results for $LANG: $SYS"
#	$EVALUATE $GOLD $SYS > results.txt
#	diff results.txt $3/$LANG/results.txt #Double-check the results.txt files
	cat $3/$LANG/results.txt > results.txt
	P_MWE=`cat results.txt | head -2 | tail -1 | cut -d= -f2 | cut -d' ' -f 2`
	R_MWE=`cat results.txt | head -3 | tail -1 | cut -d= -f2 | cut -d' ' -f 2`
	F_MWE=`cat results.txt | head -4 | tail -1 | cut -d= -f2 | cut -d' ' -f 2`
	P_TOKEN=`cat results.txt | head -7 | tail -1 | cut -d= -f2 | cut -d' ' -f 2`
	R_TOKEN=`cat results.txt | head -8 | tail -1 | cut -d= -f2 | cut -d' ' -f 2`
	F_TOKEN=`cat results.txt | head -9 | tail -1 | cut -d= -f2 | cut -d' ' -f 2`
	rm results.txt

#	RESULTS[system]=SNAME
#	MYMAP=( [foo]=bar [baz]=quux [corge]=grault )
#	declare -a RES_$SNAME=([name]=$SNAME [track]=$STRACK [token-based]=$P_TOKEN/$R_TOKEN/$F_TOKEN  [MWE-based]=$P_MWE/$R_MWE/$F_MWE)

	echo "$2 $SNAME $STRACK $P_MWE $R_MWE $F_MWE $P_TOKEN $R_TOKEN $F_TOKEN"
fi
} 
##############################################################################


##############################################################################
# Make the ranking of the systems per language and per track
# Parameters: 
#  $1 = results directory path
# Sorts the result files according to F-measure (both token-based and MWE-based)
makeRanking() {
for LANG in ${LANGUAGES[*]}; do
	echo "System Track P-token R-token F-token P-MWE R-MWE F-MWE Rank-token Rank-MWE" > $1/$LANG.ranked.txt #Initiate the ranking file
	for TRACK in `echo closed open`; do
#		echo "Processing $LANG.$TRACK.txt"
		if [ -f $1/$LANG.$TRACK.txt ]; then
			#Rank the systems according to 2 measures. If a system F-measure is 0, the ranking is not applicable
			cat $1/$LANG.$TRACK.txt | sort -nr --key=5 | gawk '{if ($5=="0.0000") print $0, "n/a"; else print $0, NR}' | sort -nr --key=8 | gawk '{if ($8=="0.0000") print $0, "n/a"; else print $0, NR}' >> $1/$LANG.ranked.txt
			rm -f $1/$LANG.$TRACK.txt
		fi
	done
done
}

##############################################################################


#Check the number of parameters
if [ $# -ne 2 ]; then
	echo "usage: $0 results-dir gold-data-dir"
	echo "   results-dir = directory of system results. It should contain one folder per system, with one folder per language, with one test.system.parsemetsv file in each."
	echo "   gold-data-dir = directory with the test gold data. It should contain one folder per language, with the parsemetgz/OUT/test.parsemetsv file in each."
	exit 1
fi


r=0 #Index of the results lines in the results table
echo "Language System Track P-token R-token F-token P-MWE R-MWE F-MWE Rank-token Rank-MWE" > $1/all-results.txt #Initiate the file for all results

#Run the evaluation for each language
for LANG in ${LANGUAGES[*]}; do
	#Initiate the results file for a language
	rm -f $1/${LANG}.open.txt
	rm -f $1/${LANG}.closed.txt

	#For a given language, evaluate each system
	for SDIR in `ls $1`; do
		#Run the evaluation for the given language and system
		res=""
		res=`getResultsLanSys $2 $LANG $1/$SDIR`
#		echo "${SDIR%.*} for $LANG: $res"
		if [ "$res" != "" ]; then
			echo $res >> $1/all-results.txt
			RESULTS[$r]=$res
			r=$[$r+1]
			#Print to the result files for the language
			TRACK=`echo $res | cut -d' ' -f3`
			echo $res | cut -d' ' -f2-9 >> $1/${LANG}.${TRACK}.txt
		fi
	done
done

#Print results to a file
#echo "" > all-results.txt
#i=0
#while [ $i -lt ${#RESULTS[@]} ]; do
#	echo ${RESULTS[$i]} >> all-results.txt
#	i=$[$i+1]
#done

#Make rankings
makeRanking $1








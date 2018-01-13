#!/bin/bash

#This script checks the consistency of the PARSEME shared task files meant for calculationgthe inter-annotator agreement
#Parameters:
# $1 = langauge code (BG for Bulgarian, EL for Greek, etc.)
# $2 = first of the 2 files containing the double annotations; naming convention: XX.double.1.parsemetsv (where XX is the langauge code)
# $3 = second of the 2 files containing the double annotations; naming convention: XX.double.2.parsemetsv (where XX is the langauge code)
# $4 = optional file containing the adjudicated version of the same file; naming convention: XX.double.gold.parsemetsv (where XX is the langauge code)
#
# Outputs a confirmation/message error

source ../../lib/parseme_st_data_dev_path.bash
CHECK_PARSEMETSV="$PARSEME_SHAREDTASK_DATA_DEV/1.0/preliminary-sharedtask-data/bin/checkParsemeTsvFormat.py"
EVALUATE="$PARSEME_SHAREDTASK_DATA_DEV/1.0/preliminary-sharedtask-data/bin/evaluate.py"

#Check the number of parameters
if [ $# -lt 3 ]; then
	echo "usage: $0 XX XX.double.1.parsemetsv XX.double.2.parsemetsv [XX.double.gold.parsemetsv]"
	echo "       (XX is the language code: BG for Bulgarian, EL for Greek, etc.)"
	exit 1
fi

#Checking the names of parameters
#Extract the language codes and extensions from both file names
#f1=${2#*/}   # remove prefix ending in "/" in $2
#f2=${3#*/}   # remove prefix ending in "/" in $3
f1=`echo $2 | sed 's/.*\///g'`
f2=`echo $3 | sed 's/.*\///g'`
#echo "f1 = $f1" 
#echo "f2 = $f2" 
lang1=${f1:0:2}
lang2=${f2:0:2}
#echo "lang1 = $lang1" 
#echo "lang2 = $lang2" 
extlen1=$[${#f1}-2]
extlen2=$[${#f2}-2]  
#echo "extlen1 = $extlen1" 
#echo "extlen2 = $extlen2" 
ext1=${f1:2:extlen1}
ext2=${f2:2:extlen2}
#echo "ext1 = $ext1" 
#echo "ext2 = $ext2" 

#Repeat the above for a gold file, if it is given
if [ $# == 4 ]; then 
	f3=`echo $4 | sed 's/.*\///g'`
	lang3=${f3:0:2}
	extlen3=$[${#f3}-2]
	ext3=${f3:2:extlen3}
fi

#Checking the consistency of the language codes in all parameters
echo "Checking the file names..."
if [ $lang1 != $1 ] || [ $lang2 != $1 ]; then
	echo "Check the language code in the files names"
	exit 2
fi 
if [ $# == 4 ]; then
	if [ $lang3 != $1 ]; then
		echo "Check the language code in the files names"
		exit 2
	fi
fi

#Checking the file name extensions
if [ $ext1 != ".double.1.parsemetsv" ] || [ $ext2 != ".double.2.parsemetsv" ]; then
	echo "Check the extensions of the parsemetsv files: $ext1 and $ext2."
	echo "The extensions should be \".double.1.parsemetsv\" and \".double.2.parsemetsv\""
	exit 3
fi
if [ $# == 4 ]; then
	if [ $ext3 != ".double.gold.parsemetsv" ]; then
		echo "Check the extension of the parsemetsv file: $ext3"
		echo "\".double.gold.parsemetsv\""
		exit 3
	fi
fi
echo "The file names look fine!"

#Checking the existence of the parameters
if [ ! -f $2 ]; then
	echo "File $2 does not exist."
	exit 4
fi
if [ ! -f $3 ]; then
	echo "File $3 does not exist."
	exit 4
fi
if [ $# == 4 ] && [ ! -f $4 ]; then
	echo "File $4 does not exist."
	exit 4
fi


#Checking the parsemetsv format
echo -e "\nChecking the format of both files..."
echo -n "$f1: "
$CHECK_PARSEMETSV $2
echo -n "$f2: "
$CHECK_PARSEMETSV $3
if [ $# == 4 ]; then
	echo -n "$f3: "
	$CHECK_PARSEMETSV $4
fi

#Checking the alignment of the parsemetsv files
echo -e "\nChecking the alignment of both files..."
cat $2 | grep -v -E '^#' | cut -f1-3 > tmp1
cat $3 | grep -v -E '^#' | cut -f1-3 > tmp2
dif=`diff tmp1 tmp2`
#echo "dif = $dif"
if [ "$dif" != "" ]; then 
	echo $dif
	echo "$f1 and $f2 are NOT aligned"
	exit 5
else
	echo "$f1 and $f2 are aligned"
fi
if [ $# == 4 ]; then
	cat $4 | grep -v -E '^#' | cut -f1-3 > tmp3
	dif1=`diff tmp1 tmp3`
	dif2=`diff tmp2 tmp3`
	if [ "$dif1" != "" ] || [ "$dif2" != "" ]; then 
		echo $dif1
		echo "$f3 is NOT aligned with $f1 or $f2"
		exit 4
	else
		echo $dif2
		echo "$f3 is aligned with $f1 and $f2"
	fi
fi
rm -f tmp1 tmp2 tmp3 

#Applying the evaluation script to both files
echo -e "\nApplying the evaluation script to $f1 et $f2..."
$EVALUATE $2 $3
if [ $# == 4 ]; then
	echo -e "\nApplying the evaluation script to $f1 et $f3..."
	$EVALUATE $2 $4
	echo -e "\nApplying the evaluation script to $f2 et $f3..."
	$EVALUATE $3 $4
fi
echo ""






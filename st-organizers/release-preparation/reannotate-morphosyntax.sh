#! /bin/bash
#This script updates the morphosyntactic annotation in a .cupt file with 
#the results obtained from the latest UDPipe version and model.
#Using this script makes sense if annotation to update was perfomed automatically 
#with a previous UDPipe version or model.
#Parameters:
#	$1 = language code
#	$2, $3, ... = a list of files or directories to reanotate; if $i is a directory, all files with a .cupt extension are reannotated
#Sample call:
#	#Re-annotating a single file
#	./reannotate-morphosyntax.sh BG ~/PARSEME/PARSEME-corpora/Gitlab/parseme_corpus_languages/parseme_corpus_bg/dev.cupt 2> UDPIPE-REANNOTATION/reannotate-log.txt
#
#	#Reannotating all .cupt files in a directory
#	./reannotate-morphosyntax.sh BG ~/PARSEME/PARSEME-corpora/Gitlab/parseme_corpus_languages/parseme_corpus_bg/ 
#
#The reannotated files and the log file go to the UDPIPE-REANNOTATION subdirectory  (to change this - replace the WORK_DIR constant)
#

#Current directory
HERE="$(cd "$(dirname "$0")" && pwd)"

#.cupt to .conllu converter
CUPT2CONLLU=$HERE/../to_conllup.py
TOCUPT=$HERE/../to_cupt.py
SPLITCONLLU=$HERE/split-conllu.py
#echo "CUPT2CONLLU=$CUPT2CONLLU"
#echo "TOCUPT=$TOCUPT"

#Maximum size of a .conllu file to process by the UDPipe API (in megabytes)
MAX_CONLLU_SIZE=4 

#Working directory for the newly annotated files
SUBDIR=UDPIPE-REANNOTATION
#Log file
LOG=reannotate-log.txt

#Language codes and the prefixes of the names of the corresponding UDPipe models (if several models per language, the one with the best LAS for gold tokanization is taken)
#See here: https://ufal.mff.cuni.cz/udpipe/2/models
declare -A LANGS=( [AR]=arabic [BG]=bulgarian [CS]=czech-pdt [DE]=german-hdt [EL]=greek-gdt [EN]=english-atis [ES]=spanish-ancora [EU]=basque [FA]=persian-perdt [FR]=french-sequoia [HE]=hebrew-iahltwiki  [HI]=hindi-hdtb [HR]=croatian [HU]=hungarian [IT]=italian-partut [LT]=lithuanian-alksnis [MT]=maltese-mudt [PL]=polish-lfg [PT]=portuguese [RO]=romanian-simoner [SL]=slovenian-ssj [SV]=swedish-talbanken [TR]=turkish-tourism [ZH]=chinese-gsd)

#Language of the data
LANG=""

set -o nounset    # Using "$UNDEF" var raises error
set -o errexit    # Exit on error, do not continue quietly

########################################
usage() {
    echo "Usage: $(basename "$0") <language-code> <input-file-01> [<input-file-02> ...]"
    echo "	Updates the morphosyntactic annotation in a .cupt file with the results obtained from the latest UDPipe version and model"
    echo "	Parameters: "
    echo "		<language-code> = 2-letter iso code of the language (AR, BG, CS, etc.)"
    echo "	Any existing information other than tokenisation and MWE annotation (columns 1, 2 and 11) will be overwritten."
    echo "	The resulting .cupt files are placed in the same directory as the input files, with extension .new.cupt."
}

########################################
fail() {
    echo "$(basename "$0"): $1"; exit 1
}

########################################
#Split a .conllu file if it exceeds a given size (see the UDPipe constraints in the REST API) 
#Parameter: $1 = path of the .cupt file

########################################
#Create the reannotation subdirectory if needed
#Parameter: $1 = a file or a directory to reannotate
#Return the path to the reannotation directory
prepare_reannot_dir() {
#Copy the files to a reannotation subdirectory
   if [ -d $1 ]; then
        reannot_dir=$1/$SUBDIR
   else
        reannot_dir=$(dirname $1)/$SUBDIR
   fi
   if [ ! -d $reannot_dir ]; then mkdir $reannot_dir; fi    #Create the reannotation directory if needed
   
   echo $reannot_dir
}

########################################
#Reannotate a single .cupt file
#Parameters: 
#     $1 = path of the .cupt file to reannotate
#     $2 = path of the reannotation directory, where the reannotated files are to be placed
reannotate() {
    #generating all intermediate file names
    file=`basename $1 .cupt`   # remove suffix starting with "_"
    old_conllu=$2/$file.old.conllu
    new_conllu=$2/$file.new.conllu
    new_cupt=$2/$file.new.cupt
    
    bold_echo "===> Started at: `date`"
    bold_echo "===> Generating: $new_cupt"
    
    #Transform .cupt to .conllu by deleting the 11th column
    ${CUPT2CONLLU} --debug --lang $LANG --keepranges --colnames ID FORM LEMMA UPOS XPOS FEATS HEAD DEPREL DEPS MISC --input $1 | tail -n +2 > $old_conllu
    
    #Split the file if too big
    ${SPLITCONLLU} $old_conllu $MAX_CONLLU_SIZE
   
    echo "" > $new_conllu  #Re-create an empty file

    fileID=1
    sub_old_conllu=$old_conllu.$fileID
    while [ -f $sub_old_conllu ]; do
        sub_new_conllu=$sub_old_conllu.reannot
        #Run UDPipi via a REST API
        curl -F data=@$sub_old_conllu -F model=$MODEL_PREF -F  tagger= -F parser= http://lindat.mff.cuni.cz/services/udpipe/api/process | PYTHONIOENCODING=utf-8 python -c "import sys,json; sys.stdout.write(json.load(sys.stdin)['result'])" > $sub_new_conllu
	#Uncomment if only HEAD and DEPREL is to be re-annotated
        #curl -F data=@$sub_old_conllu -F model=$MODEL_PREF -F  parser= http://lindat.mff.cuni.cz/services/udpipe/api/process | PYTHONIOENCODING=utf-8 python -c "import sys,json; sys.stdout.write(json.load(sys.stdin)['result'])" > $sub_new_conllu
        if [ $fileID -eq "1" ]; then
            cat $sub_new_conllu >> $new_conllu
        else
            tail -n +4 $sub_new_conllu >> $new_conllu
        fi
        rm -f $sub_old_conllu $sub_new_conllu
        fileID=$((fileID+1))
        sub_old_conllu=$old_conllu.$fileID
    done
    
    #Merge .conllu with MWE annotations
    ${TOCUPT} --lang $LANG --input $1 --conllu $new_conllu > $new_cupt	
    #Remove intermediate files
    rm -f $old_conllu $new_conllu

    bold_echo "===> File ready: $new_cupt"
    bold_echo "===> Finished at: `date`"
    echo "========================================================================================"
}

########################################

bold_echo() {
    (tput bold; echo "$@">&2; tput sgr0)
}

########################################
########################################


# Handle parameters
test "$#" -ne 2  && fail "expected language code and at least 1 input .cupt file or directory"

LANG="$1"
MODEL_PREF=${LANGS[$LANG]}
echo "Language: $LANG"
echo "Model-prefix: $MODEL_PREF"
shift

#Reannotate all files
for input in "$@"; do   

    #Prepare the reannotation directory
    REANNOT_DIR=$(prepare_reannot_dir $input)
    echo "Reannotated files go to $REANNOT_DIR"
    exec 2> $REANNOT_DIR/$LOG      #Redirecting standard error to a log file
    echo "Logs go to $REANNOT_DIR/$LOG"

    #If a directory, reannotate all .cupt files in it
    if [ -d $input ]; then
        for f in $input/*.cupt; do
            reannotate $f $REANNOT_DIR
        done
    else  
        reannotate $input $REANNOT_DIR
    fi
done

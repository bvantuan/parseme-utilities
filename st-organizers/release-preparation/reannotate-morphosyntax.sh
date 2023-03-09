#! /bin/bash
# This script updates the morphosyntactic annotation in a .cupt file with 
# the results obtained from the latest UDPipe model or corpus.

#Current directory
HERE="$(cd "$(dirname "$0")" && pwd)"

#.cupt to .conllu converter
CUPT2CONLLU=$HERE/../to_conllup.py
TOCUPT=$HERE/../to_cupt.py
SPLITCONLLU=$HERE/split-conllu.py

# validate the format .cupt
VALIDATE_CUPT=$HERE/validate_cupt.py
# validate the format .conllu
VALIDATE_CONLLU=$HERE/validate_conllu.py

#Maximum size of a .conllu file to process by the UDPipe API (in megabytes)
MAX_CONLLU_SIZE=4 

#Working directory for the newly annotated files
SUBDIR=REANNOTATION
#Log file
LOG=reannotate-log.txt

#Language codes and the prefixes of the names of the corresponding UDPipe models (if several models per language, the one with the best LAS for gold tokanization is taken)
#See here: https://ufal.mff.cuni.cz/udpipe/2/models
declare -A LANGS=( [AR]=arabic [BG]=bulgarian [CS]=czech-pdt [DE]=german-hdt [EL]=greek-gdt [EN]=english-atis [ES]=spanish-ancora [EU]=basque [FA]=persian-perdt [FR]=french-sequoia [HE]=hebrew-iahltwiki  [HI]=hindi-hdtb [HR]=croatian [HU]=hungarian [IT]=italian-partut [LT]=lithuanian-alksnis [MT]=maltese-mudt [PL]=polish-lfg [PT]=portuguese [RO]=romanian-simoner [SL]=slovenian-ssj [SV]=swedish-talbanken [TR]=turkish-tourism [ZH]=chinese-gsd)
declare -A VMWEs=( [LVC.full]='Light verb constructions in which the verb is semantically totally bleached' 
                    [LVC.cause]='Light verb constructions in which the verb adds a causative meaning to the noun' 
                    [VID]='Verbal idioms' 
                    [IRV]='Inherently reflexive verbs' 
                    [VPC.full]='fully non-compositional verb-particle constructions' 
                    [VPC.semi]='semi non-compositional verb-particle constructions' 
                    [MVC]='multi-verb constructions' 
                    [IAV]='inherently adpositional verbs')
# declare a constant array
declare -r INVALID_VMWEs=("NotMWE")

#Language of the data
LANG=""

set -o nounset    # Using "$UNDEF" var raises error
set -o errexit    # Exit on error, do not continue quietly

########################################
usage() {
    echo "Usage: $(basename "$0") [-h] [-m method] [-l language-code] [OPTION]... [FILE]..." 
    echo "Reannotate the morphosyntax in a .cupt file from framework Universal Dependencies (UD)(treebanks or latest UDPipe model)"
    echo "Any existing information other than tokenisation and MWE annotation (columns 1, 2 and 11) will be overwritten."
    echo "The resulting .cupt files are placed in the directory 'REANNOTATION' which is under the same directory as the input files, with extension .new.cupt."

    echo ""
    echo "Example: ./reannotate-morphosyntax.sh -m udpipe -l PL -s parseme1.cupt parseme2.cupt --tagger --parser"
    echo "         ./reannotate-morphosyntax.sh --method udtreebank -s parseme_test_en.cupt -t ud-treebanks-v2.11/UD_English-LinES/en_lines-ud-train.conllu -u http://hdl.handle.net/11234/1-4923 -p UD_English-LinES/en_lines-ud-train.conllu"
    echo "         ./reannotate-morphosyntax.sh --method udtreebank -s parseme_test_pl.cupt -t ud-treebanks-v2.11/UD_Polish-PDB/ -u http://hdl.handle.net/11234/1-4923 -r"

    echo ""
    echo "Parameters: "
    echo -e "\t -h, --help \t\t Display this help message"
    echo -e "\t -m, --method \t\t Method of reannotation (supported udtreebank and udpipe)"
    echo -e "\t -l, --language \t 2-letter iso code of the language (AR, BG, CS, etc.)"
    echo -e "\t -s, --source \t\t Files to reannotate"
    echo -e "\t -t, --treebank \t File .conllu or a directory of treebanks of Universal Dependencies (UD)"
    echo -e "\t -u, --uri \t\t The persistent URI of the original corpus"
    echo -e "\t -p, --path \t\t The path of the source file in the original corpus (used only if the parameter --treebank is a file)"
    echo -e "\t --tagger \t\t Reannotate columns LEMMA, UPOS, XPOS and FEATS in udpipe method (default:false)"
    echo -e "\t --parser \t\t Reannotate columns HEAD and DEPREL in udpipe method (default:false)"
    echo -e "\t -r, --release \t\t Correct invalid VMWE annotations (e.g. NotMWE to *) (default:false)"
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
    # $1 exists and is a directory
   if [ -d $1 ]; then
        reannot_dir=$1/$SUBDIR
    # $1 is a file
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
reannotate_udpipe() {
    #generating all intermediate file names
    file=`basename $1 .cupt`   # remove suffix starting with   "_"
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

        if $tagger && $parser; then
            #Run UDPipi via a REST API
            curl -F data=@$sub_old_conllu -F model=$MODEL_PREF -F  tagger= -F parser= http://lindat.mff.cuni.cz/services/udpipe/api/process | PYTHONIOENCODING=utf-8 python3 -c "import sys,json; sys.stdout.write(json.load(sys.stdin)['result'])" > $sub_new_conllu
        elif $tagger && ! $parser; then
            #Run UDPipi via a REST API
            curl -F data=@$sub_old_conllu -F model=$MODEL_PREF -F  tagger= http://lindat.mff.cuni.cz/services/udpipe/api/process | PYTHONIOENCODING=utf-8 python3 -c "import sys,json; sys.stdout.write(json.load(sys.stdin)['result'])" > $sub_new_conllu
        elif ! $tagger && $parser; then
            #Run UDPipi via a REST API
            curl -F data=@$sub_old_conllu -F model=$MODEL_PREF -F  parser= http://lindat.mff.cuni.cz/services/udpipe/api/process | PYTHONIOENCODING=utf-8 python3 -c "import sys,json; sys.stdout.write(json.load(sys.stdin)['result'])" > $sub_new_conllu
        else
            #Run UDPipi via a REST API
            curl -F data=@$sub_old_conllu -F model=$MODEL_PREF  http://lindat.mff.cuni.cz/services/udpipe/api/process | PYTHONIOENCODING=utf-8 python3 -c "import sys,json; sys.stdout.write(json.load(sys.stdin)['result'])" > $sub_new_conllu
        fi
    
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

    if $release; then
        bold_echo "===> Validating the new .cupt file for the release version"
        # validate the format .cupt
        ${VALIDATE_CUPT} --input $new_cupt
    fi
    
    bold_echo "===> Finished at: `date`"
    bold_echo "========================================================================================"
}


########################################
# Reannotate to the latest source treebanks' versions
# Parameters: 
#     $1 = file .cupt with columns to be replaced
#     $2 = latest source treebanks' version in format .conllu
#     $3 = the persistent URI of the original corpus
#     $4 = the path of the source file in the original corpus
reannotate_udtreebank() {
    corpus_uri=${3:-}
    file_path=${4:-}

    # validate the format .cupt
    # ${VALIDATE_CUPT} --input $1
    # # validate the format .conllu
    ${VALIDATE_CONLLU} $2

    # generating all intermediate file names
    file=`basename $1 .cupt`   # remove suffix starting with "_"
    # old annotaion (temporary file)
    old_cupt=$REANNOT_DIR/$file.old.cupt
    # new annotation file
    new_cupt=$REANNOT_DIR/$file.new.cupt

    bold_echo "===> Started at: `date`" 
    bold_echo "===> Generating: $new_cupt"

    # Re-create an empty file
    > $new_cupt
    # copy the old annotation to a temporary file to keep the file unchanged
    cp $1 $old_cupt

    # count the line number while reading
    declare -i count_line_number=1
    # The number of sentences is updated during the synchronisarion from UD treebank
    declare -i nb_sentences_updated=0
    # The number of sentences needs to corrected manually 
    declare -i nb_sentences_to_correct=0
    # The number of sentences is not changed
    declare -i nb_sentences_not_changed=0

    # Reading old annotaion (temporary file)
    while read -r line; do
        # If the line is a text (sentence)
        if grep -q -F "# text =" <<< "$line"; then
            # Extract the block of lines of annotation of the text (metadata and morphosyntax)
            old_blocktext_after=$(sed -n "$count_line_number,/^$/p" "$1")
            old_blocktext_before=$(head -n $count_line_number "$1" | tac | sed -n "2,/^$/p" | tac)
            old_blocktext_before=$(sed '/^$/d' <<< $old_blocktext_before)
            old_blocktext=$(echo -e "$old_blocktext_before\n$old_blocktext_after")

            # if release parameter is set
            if $release; then
                # new release block text (remove invalid vmwe tags)
                old_release_blocktext=""
                # new invalid vmwe tags including the index (1:NotMWE, add 1 to the invalid vmwe tags)
                new_invalid_vmwes=("${INVALID_VMWEs[@]}")
    
                # loop over the tokenization lines in the parseme sentence
                while read token_line; do
                    # If the line is a token line
                    if grep -q -v '^#' <<< "$token_line"; then
                        # vmwe tag in the line
                        vmwe_tag=$(cut -f11 <<< $token_line)
                        # vmwe indexed tag in the line
                        vmwe_tag_key=$(cut -d: -f1 <<< "$vmwe_tag")
                        # vmwe value tag in the line
                        vmwe_tag_value=$(cut -d: -f2 <<< "$vmwe_tag")
                        
                        # the line has a invalid vmwe tag
                        if [[ " ${new_invalid_vmwes[*]} " =~ " ${vmwe_tag_value} " ]]; then
                            # add indexed tag
                            new_invalid_vmwes+=($vmwe_tag_key)
                            # the new token line from replacing the invalid vmwe tag by *
                            release_token_line=$(echo "$token_line" | awk -v OFS='\t' -v replacement="*" '{ $11=replacement; print }')
                            # add the new token line
                            old_release_blocktext=$(echo -e "$old_release_blocktext\n$release_token_line")
                        # the line has a valid vmwe tag
                        else
                            # the token line is kept
                            old_release_blocktext=$(echo -e "$old_release_blocktext\n$token_line")
                        fi
                    # If the line is not a token line
                    else
                        # the token line is kept
                        old_release_blocktext=$(echo -e "$old_release_blocktext\n$token_line")
                    fi
                done <<< "$old_blocktext"

                # remove new lines
                old_release_blocktext=$(sed '/^$/d' <<< $old_release_blocktext)
                # block text is replaced
                old_blocktext=$old_release_blocktext
            fi

            # Metadata of the text
            old_metadata_text=$(grep '^#' <<< $old_blocktext)
            # Line starting with # source_sent_id =
            old_metadata_source_sent_id=$(grep '# source_sent_id =' <<< $old_metadata_text)
            # morphosyntax of the text
            old_morphosyntax_text=$(grep -v '^#' <<< $old_blocktext)
            # Old MWE annotation
            old_MWE_annotation=$(cut -f11 <<< $old_morphosyntax_text)

            # Find the line number of the first occurrence of the sentence in the latest source treebanks' version
            line_number=$(grep -n -Fx "$line" "$2" | head -1 | cut -d: -f1)
            # If the sentence is not in the latest source treebanks' version
            if [ -z "$line_number" ]; then
                # Copy the old annotation into a new reannotated file
                echo -e "$old_blocktext" >> $new_cupt
                echo "" >> $new_cupt
                # The number of sentences that are not changed increases
                nb_sentences_not_changed=$((nb_sentences_not_changed+1))
            # If the sentence is in the latest source treebanks' version
            else
                echo "The sentence \"$line\" is founded in the UD treebank"

                # Extract the block of lines of new annotation of the text (metadata and morphosyntax in the UD)
                new_blocktext_after=$(sed -n "$line_number,/^$/p" "$2")
                new_blocktext_before=$(head -n $line_number "$2" | tac | sed -n "2,/^$/p" | tac)
                new_blocktext_before=$(sed '/^$/d' <<< $new_blocktext_before)
                new_blocktext=$(echo -e "$new_blocktext_before\n$new_blocktext_after")

                # Metadata of the text in the UD
                new_metadata_text=$(grep '^#' <<< $new_blocktext)
                # Sentence id of the text in the UD
                new_sentence_id=$(grep -n '# sent_id =' <<< $new_metadata_text | cut -d: -f2 | cut -d' ' -f4)
                # the newest morphosyntax in the UD
                new_morphosyntax_text=$(grep -v '^#' <<< $new_blocktext)

                # Tokenisation of old annotaion
                source_tokens=$(cut -f2 <<< $old_morphosyntax_text)
                # Tokenisation of the latest source treebanks' version
                destination_tokens=$(cut -f2 <<< $new_morphosyntax_text)

                # Replace the old identifier by the sentence identifier of the text sentence in the UD
                new_metadata_source_sent_id=$(echo "$old_metadata_source_sent_id" | awk -v replacement="$new_sentence_id" '{ $6=replacement; print }')
                # If the parameter uri exists
                if [ -n "$corpus_uri" ]; then
                    # Replace the old by the new uri
                    new_metadata_source_sent_id=$(echo "$new_metadata_source_sent_id" | awk -v replacement="$corpus_uri" '{ $4=replacement; print }')
                fi

                # If the parameter file path exists
                if [ -n "$file_path" ]; then
                    # Replace the old by the new path
                    new_metadata_source_sent_id=$(echo "$new_metadata_source_sent_id" | awk -v replacement="$file_path" '{ $5=replacement; print }')
                fi
                # Replace the old source_sent_id by the new one in the metadata
                new_metadata_text=$(echo -e "$old_metadata_text" | sed "/^# source_sent_id =/s/.*/$(echo "$new_metadata_source_sent_id" | sed 's/[\/&]/\\&/g')/")
                
                # Tokenisations are the same in both versions
                if [ "$source_tokens" = "$destination_tokens" ]; then
                    echo "Tokenisations are the same in both versions, the morphosyntax is updated automatically"
                    echo ""
                    # Metadata is copied 
                    echo -e "$new_metadata_text" >> $new_cupt
                    # MWE_annotation isn't changed, copy the new morphosyntax to new annotation file
                    paste <(echo -e "$new_morphosyntax_text") <(echo "$old_MWE_annotation") >> $new_cupt
                    echo "" >> $new_cupt
                    # The number of sentences that are updated increases
                    nb_sentences_updated=$((nb_sentences_updated+1))
                # The tokenizations are different in the two versions
                else
                    # associative arrays for id:token:vmwe tag 
                    declare -A id_source_token
                    declare -A id_source_MWE_annotation
                    declare -A id_destination_token
                    
                    # Three columns id, token form and MWE annotation in the old morphosyntax 
                    source_tokens_with_id_and_MWE_annotation=$(cut -f1,2,11 <<< $old_morphosyntax_text)
                    # loop through each line in the columns variable
                    while read -r id token MWE_annotation; do
                        # add the id-token pair to the associative array
                        id_source_token[$id]=$token
                        # add the id-MWE_annotation pair to another associative array
                        id_source_MWE_annotation[$id]=$MWE_annotation
                    done <<< "$source_tokens_with_id_and_MWE_annotation"

                    # Two columns id, token form in the new morphosyntax 
                    destination_tokens_with_id=$(cut -f1,2 <<< $new_morphosyntax_text)
                    # loop through each line in the columns variable
                    while read -r id token; do
                        # echo "id: $id   token: $token"
                        # add the id-token pair to the associative array
                        id_destination_token["$id"]="$token"
                        # echo "with id $id, we have ${id_destination_token[$id]}"
                    done <<< "$destination_tokens_with_id"

                    # boolean variable indicate id the changed tokens are in a MWE
                    are_changed_tokens_in_a_MWE=false
                    source_id=1
                    destination_id=1
                    # all changed token ids in parseme sentence
                    source_changed_tokens=()
                    # changed token ids in a MWE
                    source_changed_tokens_in_MWE=()
                    # all changed token ids in ud sentence
                    destination_changed_tokens=()
                    # new MWE annotation for the changed tokenization
                    declare -A new_MWE_annotation

                    # Compare two tokenizations in the while loop
                    while [[ ! $source_id -gt ${#id_source_token[@]} ]] && [[ ! $destination_id -gt ${#id_destination_token[@]} ]]; do
                        # MWE annotation is the same 
                        new_MWE_annotation[$source_id]=${id_source_MWE_annotation[$source_id]}
                        # If the tokens are the same
                        if [[ "${id_source_token[$source_id]}" == "${id_destination_token[$destination_id]}" ]]; then
                            # Next token
                            source_id=$((source_id+1))
                            destination_id=$((destination_id+1))
                        # If the tokens are not the same
                        else
                            # find the changed token id in the parseme sentence
                            source_changed_tokens+=($source_id)
                            # find the changed token id in the ud sentence
                            destination_changed_tokens+=($destination_id)
                            # If the changed token is in a MWE
                            if [[ ! "${id_source_MWE_annotation[$source_id]}" == "*" ]]; then
                                # find the changed token id in a MWE
                                are_changed_tokens_in_a_MWE=true
                                source_changed_tokens_in_MWE+=($source_id)
                            fi

                            # compare the lengths of two tokens : if it is a division
                            if [[ "${#id_source_token[$source_id]}" -gt "${#id_destination_token[$destination_id]}" ]]; then
                                # the remaining token
                                remaining_token="${id_source_token[$source_id]/${id_destination_token[$destination_id]}}"
                                temp_id=$((destination_id+1))
                                # loop from next token to the end token in the ud sentence
                                for id in $(seq $temp_id ${#id_destination_token[@]}); do
                                    # find the changed token id in the ud sentence
                                    destination_changed_tokens+=($id)
                                    # MWE annotation is the same for the cas of division
                                    # new_MWE_annotation+="${id_source_MWE_annotation[$source_id]}\n"
                                    new_MWE_annotation[$id]=${id_source_MWE_annotation[$source_id]}
                                    # if the next token in ud sentence is the remaining token
                                    if [[ "$remaining_token" == "${id_destination_token[$id]}" ]]; then
                                        remaining_token="${remaining_token/${id_destination_token[$id]}}"
                                        # Next token for comparaison
                                        source_id=$((source_id+1))
                                        destination_id=$((id+1))
                                        break
                                    # if the next token in ud sentence is not the remaining token
                                    else
                                        # the new remaining token
                                        remaining_token="${remaining_token/${id_destination_token[$id]}}"
                                    fi
                                    
                                done
                                
                                # Can't not find the remaining token
                                if [[ ! -z $remaining_token ]]; then
                                    echo "Something went wrong during the search of changed tokens"
                                    exit 1
                                fi
                            # compare the lengths of two tokens : if it is an union
                            else
                                # the remaining token
                                remaining_token="${id_destination_token[$destination_id]/${id_source_token[$source_id]}}"
                                temp_id=$((source_id+1))
                                # loop from next token to the end token in the parseme sentence
                                for id in $(seq $temp_id ${#id_source_token[@]}); do
                                    # find the changed token id in the parseme sentence
                                    source_changed_tokens+=($id)
                                    # If the changed token is in a MWE
                                    if [[ ! "${id_source_MWE_annotation[$id]}" == "*" ]]; then
                                        # find the changed token id in a MWE
                                        are_changed_tokens_in_a_MWE=true
                                        source_changed_tokens_in_MWE+=($id)
                                    fi
                                    
                                    # if the next token in ud sentence is the remaining token
                                    if [[ "$remaining_token" == "${id_source_token[$id]}" ]]; then
                                        remaining_token="${remaining_token/${id_source_token[$id]}}"
                                        # Next token for comparaison
                                        source_id=$((id+1))
                                        destination_id=$((destination_id+1))
                                        break
                                    # if the next token in parseme sentence is not the remaining token
                                    else
                                        # the new remaining token
                                        remaining_token="${remaining_token/${id_source_token[$id]}}"
                                    fi
                                done

                                # Can't not find the remaining token
                                if [[ ! -z $remaining_token ]]; then
                                    echo "Something went wrong during the search of changed tokens"
                                    exit 1
                                fi
                                
                            fi
                        fi
                    done

                    # loop over the ids in the ud tokenization
                    for id in "${!id_destination_token[@]}"; do
                        # If the id is not found in the new MWE annotation
                        if [ ! -v new_MWE_annotation[$id] ]; then
                            # find the origin id in the variable
                            id1=$(cut -d- -f1 <<< "$id")
                            # If the origin id is found in the new MWE annotation
                            if [ -v new_MWE_annotation[$id1] ]; then
                                # add a MWE annotation for the id
                                new_MWE_annotation[$id]=${new_MWE_annotation[$id1]}
                            # If the origin id is not found in the new MWE annotation
                            else
                                # default value
                                new_MWE_annotation[$id]="*"
                            fi
                        fi
                    done

                    # new MWE annotation that is formatted in lines for the changed tokenization
                    new_MWE_annotation_in_lines=
                    # loop through each line in the columns variable
                    while read -r id token; do
                        # format the MWE annotation in line
                        new_MWE_annotation_in_lines+="${new_MWE_annotation[$id]}\n"
                    done <<< "$destination_tokens_with_id"

                    # the changed tokens are not in a MWE
                    if ! $are_changed_tokens_in_a_MWE; then
                        echo "Tokenization has changed for the latest source treebank' version ($file_path)"
                        echo "Here are the details:"
                        echo "$line"
                        echo ""
                        echo "Source PARSEME tokenization"

                        # loop over the tokenization lines in the parseme sentence
                        while read token_line; do
                            # token id
                            id_token=$(cut -f1 <<< $token_line)
                            # If it is a changed token
                            if [[ " ${source_changed_tokens[*]} " =~ " ${id_token} " ]]; then
                                # display in green and bold
                                echo "$(tput setaf 2)$(tput bold)${token_line}$(tput sgr0)"
                            # If it is not a changed token
                            else
                                # normal display
                                echo "$token_line"
                            fi
                        done <<< "$old_morphosyntax_text"

                        echo ""
                        echo "Source UD tokenization"
                        # loop over the tokenization lines in the ud sentence
                        while read token_line; do
                            # token id
                            id_token=$(cut -f1 <<< $token_line)
                            # If it is a changed token
                            if [[ " ${destination_changed_tokens[*]} " =~ " ${id_token} " ]]; then
                                # display in green and bold
                                echo "$(tput setaf 2)$(tput bold)${token_line}$(tput sgr0)"
                            # If it is not a changed token
                            else
                                # normal display
                                echo "$token_line"
                            fi
                        done <<< "$new_morphosyntax_text"
                        echo ""


                        # terminate the redirection of stderr
                        exec 2>&1

                        # Ask the annotator
                        while true; do
                            read -p "None of the changed tokens is in a MWE, Do you want to update the morphosyntax of the sentence? (y/n) " yn
                            case $yn in
                                [Yy]* ) answer=true; break;;
                                [Nn]* ) answer=false; break;;
                                * ) echo "Please answer yes or no.";;
                            esac
                        done <&1

                        # Redirecting standard error to a log file
                        exec 2>> $REANNOT_DIR/$LOG      

                        # The annotator answered no
                        if ! $answer; then
                            # Copy the sentence into a new reannotated file
                            echo -e "$old_blocktext" >> $new_cupt
                            echo "" >> $new_cupt
                            # The number of sentences that are not changed increases
                            nb_sentences_not_changed=$((nb_sentences_not_changed+1))
                            # go to the next sentence
                            echo "Continue to update the morphosyntax for the next sentence"
                        # The annotator answered yes
                        else
                            echo "OK, the morphosyntax is updated automatically"
                            echo ""

                            # Metadata is copied into a new reannotated file
                            echo -e "$new_metadata_text" >> $new_cupt
                            # remove the last newline character
                            new_MWE_annotation_in_lines=$(sed '/^$/d' <(echo -e "$new_MWE_annotation_in_lines"))
                            # copy the MWE_annotationto into the new annotation file
                            paste <(echo -e "$new_morphosyntax_text") <(echo -e "$new_MWE_annotation_in_lines") >> $new_cupt
                            echo "" >> $new_cupt
                            # The number of sentences that are updated increases
                            nb_sentences_updated=$((nb_sentences_updated+1))
                        fi
                    # the changed tokens are in a MWE
                    else
                        echo "The tokenisation in the .conllu sentence is different and it affects the MWE annotation, please go to the $REANNOT_DIR/$LOG for the details"
                        echo "Continue to update the morphosyntax for the next sentence"
                        echo ""
                    
                        bold_echo "========================================================================================"
                        bold_echo "===> In the sentence : $line"
                        # print the changed tokens are in a MWE
                        for id in "${source_changed_tokens_in_MWE[@]}"; do
                            bold_echo "===> The changed token ${id_source_token[$id]} with the id $id has tagged ${id_source_MWE_annotation[$id]} in MWE annotation"
                        done

                        # Copy the old morphosyntax into a new reannotated file
                        echo -e "$old_blocktext" >> $new_cupt
                        echo "" >> $new_cupt
                        # The number of sentences that need to be corrected increases
                        nb_sentences_to_correct=$((nb_sentences_to_correct+1))

                        bold_echo "===> Please correct manually the tokenization, the MWE annotation and the metadata(source_sent_id)" 
                        bold_echo "===> Continue to update the morphosyntax for the next sentence" 
                        bold_echo "========================================================================================"
                    fi

                    # delete the arrays
                    unset id_source_token
                    unset id_destination_token
                    unset id_source_MWE_annotation
                fi
            fi
        fi

        # Next line number
        count_line_number=$((count_line_number+1))

    done < "$old_cupt"	

    #Remove intermediate files
    rm -f $old_cupt

    bold_echo "========================================================================================"
    bold_echo "=================================Summary================================================"
    bold_echo "===> From the UD treebank $2"
    bold_echo "===> $nb_sentences_not_changed sentences are not changed"
    bold_echo "===> $nb_sentences_updated sentences are updated automatically"
    bold_echo "===> $nb_sentences_to_correct sentences need to be corrected"
    bold_echo "========================================================================================"

    bold_echo "===> File ready: $new_cupt" 

    if $release; then
        bold_echo "===> Validating the new .cupt file for the release version"
        # validate the format .cupt
        ${VALIDATE_CUPT} --input $new_cupt
    fi
    bold_echo "===> Finished at: `date`" 
    bold_echo "========================================================================================"
}


########################################

bold_echo() {
    (tput bold; echo "$@">&2; tput sgr0)
}

########################################
########################################

# Parse command-line options
# define the short and long options that the script will accept
OPTIONS=m:l:s:t:u:p:hr
LONGOPTIONS=help,tagger,parser,release,method:,language:,source:,treebank:,uri:,path:

# parse the command line arguments.
PARSED=$(getopt --options=$OPTIONS --longoptions=$LONGOPTIONS --name "$0" -- "$@")

# there was an error parsing the option
if [[ $? -ne 0 ]]; then
    exit 2
fi
# set the positional parameters to the parsed options and arguments
eval set -- "$PARSED"

# Declare parameter variables 
method_type=
language_code=
source_files=()
treebank_file=
corpus_uri=
file_path=
# set default values for boolean arguments
tagger=false
parser=false
release=false

# iterating over positional parameters with a for loop.
while true; do
    case "$1" in
        -m|--method)
            method_type="$2"
            shift 2
            ;;
        -l|--language)
            language_code="$2"
            shift 2
            ;;
        -s|--source)
            while [[ "$2" != -* && ! -z "$2" ]]; do
                source_files+=($2)
                shift 
            done
            shift
            ;;
        -t|--treebank)
            treebank_file=$2
            shift 2
            ;;
        -u|--uri)
            corpus_uri=$2
            shift 2
            ;;
        -p|--path)
            file_path=$2
            shift 2
            ;;
        --tagger)
            tagger=true
            shift
            ;;
        --parser)
            parser=true
            shift
            ;;
        -r|--release)
            release=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        --)
            shift
            break
            ;;
        *)
            echo "Invalid option: $1" >&2
            exit 1
            ;;
    esac
done

if [ ! $method_type = "udpipe" ] && ($tagger || $parser); then
    if $tagger; then
        # error
        echo "Expected tagger parameter only for udpipe method"
        exit 2
    fi

    if $parser; then
        # error
        echo "Expected parser parameter only for udpipe method"
        exit 2
    fi
fi

# If parameter method is set
if [ -n "$method_type" ]; then
    # If the method is udpipe
    if [ $method_type = "udpipe" ]; then
        # If parameters language and source files are set
        if [ -n "$language_code" ] && [ ! "${#source_files[@]}" -eq 0 ]; then
            LANG="$language_code"
            MODEL_PREF=${LANGS[$language_code]}
            echo "Language: $language_code"
            echo "Model-prefix: $MODEL_PREF"

            # Reannotate all source files
            for input in ${source_files[@]}; do   
                #Prepare the reannotation directory
                REANNOT_DIR=$(prepare_reannot_dir $input)
                echo "Reannotated files go to $REANNOT_DIR"
                exec 2> $REANNOT_DIR/$LOG      #Redirecting standard error to a log file
                echo "Logs go to $REANNOT_DIR/$LOG"

                # If a directory, reannotate all .cupt files in it
                if [ -d $input ]; then
                    for f in $input/*.cupt; do
                        reannotate_udpipe $f $REANNOT_DIR
                    done
                else  
                    reannotate_udpipe $input $REANNOT_DIR
                fi
            done
        # If parameters language and source files are not set
        else
            # error
            echo "Expected language code and at least 1 input .cupt file or directory for udpipe method"
            exit 2
        fi
    # If the method is udtreebank
    elif [ $method_type = "udtreebank" ]; then
        # If parameters source files, treebank and uri are set
        if [ ! "${#source_files[@]}" -eq 0 ] && [ -n "$treebank_file" ] && [ -n "$corpus_uri" ]; then
            # If parameter source files has only one file
            if [ ${#source_files[@]} -eq 1 ]; then
                # If parameter treebank is a file
                if [ ! -d $treebank_file ]; then
                    # If parameter path is set
                    if [ -n "$file_path" ]; then
                        #Prepare the reannotation directory
                        REANNOT_DIR=$(prepare_reannot_dir ${source_files[0]})
                        echo "Reannotated files go to $REANNOT_DIR"
                        exec 2> $REANNOT_DIR/$LOG      #Redirecting standard error to a log file
                        echo "Logs go to $REANNOT_DIR/$LOG"
                        echo ""

                        # Reannotate to the latest source treebanks' version
                        reannotate_udtreebank "${source_files[0]}" $treebank_file $corpus_uri $file_path
                    # If parameter path is not set
                    else
                        # error
                        echo "Expected the path of the source file in the original corpus if the treebank is not a directory"
                        exit 2
                    fi
                # If parameter treebank is a directory
                else
                    # If parameter path is set
                    if [ -n "$file_path" ]; then
                        # error
                        echo "Unexpected the path of the source file in the original corpus if the treebank is a directory"
                        exit 2
                    # If parameter path is not set
                    else
                        #Prepare the reannotation directory
                        REANNOT_DIR=$(prepare_reannot_dir ${source_files[0]})
                        echo "Reannotated files go to $REANNOT_DIR"
                        exec 2> $REANNOT_DIR/$LOG      #Redirecting standard error to a log file
                        echo "Logs go to $REANNOT_DIR/$LOG"
                        echo ""

                        # directory name of the source file
                        dir=$(dirname ${source_files[0]})
                        # Name of the source file
                        file_name=`basename ${source_files[0]} .cupt`   # remove suffix starting with "_"
                        # Temporary updated morphosyntax
                        source_temp_file=$dir/$file_name.temp.cupt
                        # Copy the old morphosyntax fule into temporary updated morphosyntax file
                        cp "${source_files[0]}" $source_temp_file
                        # New temporary updated morphosyntax
                        new_cupt=$(dirname ${source_files[0]})/$SUBDIR/$file_name.temp.new.cupt
                        
                        # Loop over all treebanks in the directory
                        for f in $treebank_file/*.conllu; do
                            # remove redundant / characters from treebank file path
                            f=$(readlink -m -f "$f")
                            # Get the last two names
                            file_path=$(echo $f | awk -F/ '{print $(NF-1)"/"$NF}')
                            # Reannotate to the latest source treebanks' version
                            reannotate_udtreebank $source_temp_file $f $corpus_uri $file_path
                            # Result of reannotation is copied into the temporary updated morphosyntax file to continue update the morphosyntax from next treebanks
                            cp $new_cupt $source_temp_file
                        done
                        
                        # Change the name of latest result file
                        mv $new_cupt $dir/$SUBDIR/$file_name.new.cupt
                        new_cupt=$dir/$SUBDIR/$file_name.new.cupt
                        # Remove Temporary updated morphosyntax file
                        rm -f $source_temp_file

                        bold_echo "===> File ready: $new_cupt" 
                        bold_echo "===> Finished at: `date`" 
                        echo "========================================================================================"
                    fi
                fi
            # If parameter source files has more than one file
            else
                # error
                echo "Expected only one input source file for udtreebank method"
                exit 2
            fi
        # If parameters source files, treebank and uri are not set
        else
            # error
            echo "Expected a source file, a treebank file or directory and a parameter --uri for udtreebank reannotation method"
            exit 2
        fi
    # If the method is neither udtreebank nor udpipe
    else
        echo "Only two method of synchronisation udpipe and udtreebank are available" >&2
        exit 2
    fi
# If parameter method is not set
else
    # error
    echo "Expected synchronisation method"
    exit 2
fi


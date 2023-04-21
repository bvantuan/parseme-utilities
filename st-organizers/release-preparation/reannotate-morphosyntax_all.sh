#! /bin/bash
# This script updates the morphosyntactic annotation in a .cupt file with 
# the results obtained from the latest UDPipe model or corpus.

set -o nounset    # Using "$UNDEF" var raises error

#Current directory
HERE="$(cd "$(dirname "$0")" && pwd)"
REANNOTATION_MORPHOSYNTAX=$HERE/reannotate-morphosyntax.sh

#Language codes and the prefixes of the names of the corresponding UDPipe models (if several models per language, the one with the best LAS for gold tokanization is taken)
#See here: https://ufal.mff.cuni.cz/udpipe/2/models
declare -A LANGS=( [AR]=arabic [BG]=bulgarian [CS]=czech-pdt [DE]=german-hdt [EL]=greek-gdt [EN]=english-atis [ES]=spanish-ancora [EU]=basque [FA]=persian-perdt [FR]=french-sequoia [HE]=hebrew-iahltwiki  [HI]=hindi-hdtb [HR]=croatian [HU]=hungarian [IT]=italian-partut [LT]=lithuanian-alksnis [MT]=maltese-mudt [PL]=polish-lfg [PT]=portuguese [RO]=romanian-simoner [SL]=slovenian-ssj [SV]=swedish-talbanken [TR]=turkish-tourism [ZH]=chinese-gsd)


########################################
usage() {
    echo -e "\t -h, --help \t\t Display this help message"
}


########################################
# Check if an element is in an array
# Parameters: 
#     $1 = an element
#     $2 = an array
function is_element_in_array() {
    element="$1"
    shift
    array=("$@")

    # Loop over all elements in the array
    for item in "${array[@]}"; do
        # use the sed command to remove the escape sequence
        item=$(echo "$item" | sed 's/\x1B\[1m\x1B(B\x1B\[m//g')
        # If an element is in an array
        if [ "$element" == "$item" ]; then
            return 0
        fi
    done

    return 1
}


########################################
########################################

# Parse command-line options
# define the short and long options that the script will accept
OPTIONS=c:h
LONGOPTIONS=help,config:

# parse the command line arguments.
PARSED=$(getopt --options=$OPTIONS --longoptions=$LONGOPTIONS --name "$0" -- "$@")

# there was an error parsing the option
if [[ $? -ne 0 ]]; then
    exit 2
fi
# set the positional parameters to the parsed options and arguments
eval set -- "$PARSED"

# Declare parameter variables 
config_file=

# iterating over positional parameters with a for loop.
while true; do
    case "$1" in
        -c|--config)
            config_file="$2"
            shift 2
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
            echo "Invalid option: $1"
            exit 1
            ;;
    esac
done


########################################
# Prompt the user for parameter inputs
# Parameters: None
function read_input() {
    # Prompt the user for a language input
    read -p "2-letter iso code of the language: [$language] " language_input
    if [ ! -n "$language_input" ]; then
        language_input="$language"
    fi
    # If it is an invalide language code
    if ! is_element_in_array "$language" "${!LANGS[@]}"; then
        # error
        echo "Invalid language code"
        exit 2
    fi

    # Prompt the user for a treebank input
    read -p "A file .conllu or a directory of treebanks of Universal Dependencies (UD): [$treebank] " treebank_input
    if [ ! -n "$treebank_input" ]; then
        treebank_input="$treebank"
    fi

    # Prompt the user for a uri input
    read -p "The persistent URI of the original UD corpus: [$uri] " uri_input
    if [ ! -n "$uri_input" ]; then
        uri_input="$uri"
    fi

    # Prompt the user for a language repository input
    read -p "The path of the language repository: [$language_repository] " language_repository_input
    if [ ! -n "$language_repository_input" ]; then
        language_repository_input="$language_repository"
    else
        if [ ! -d $language_repository_input ]; then
            # error
            echo "Expected a directory for the language repository"
            exit 2
        fi
    fi

    # Ask the annotator
    while true; do
        read -p "Display detailed processing information: [$verbose] " verbose_input
        if [ -n "$verbose_input" ]; then
            case $verbose_input in
                true ) verbose_input=true; break;;
                false ) verbose_input=false; break;;
                * ) echo "Please answer true or false.";;
            esac
        else
            verbose_input=$verbose
            break
        fi
    done <&1

    # If parameter treebank is a file
    if [ ! -d $treebank_input ]; then
        # If parameter treebank is a valid file
        if [ -f "$treebank_input" ]; then
            # Prompt the user for a path input
            read -p "The path of the source file in the original UD corpus: " path_input
            # If the path is empty
            if [ ! -n "$path_input" ]; then
                # error
                echo "Expected the path of the source file in the original UD corpus"
                exit 2
            fi
        # If parameter treebank is an invalid file
        else
            # error
            echo "File $treebank_input does not exist"
            exit 2
        fi
    fi

    KEY="source"
    # Read the array of dictionaries for the specified key using jq
    dicts_json=$(jq ".${KEY}?" "$config_file")

    # Convert the JSON array of dictionaries to a Bash array of dictionaries
    readarray -t dicts < <(echo "$dicts_json" | jq -c '.[]')

    # Iterate over the array of dictionaries and process each one
    for dict in "${dicts[@]}"; do
        # A corpus
        source_file=$(echo "$dict" | jq -r '.corpus')
        # Method
        method=$(echo "$dict" | jq -r '.method')

        # command line parameter
        source_files_parameters_in_line["$source_file"]="--source $language_repository_input/$source_file "
        source_files_parameters_in_line["$source_file"]+="--method $method "
        # add the value to the associative array
        source_files_parameters["$source_file|method"]="$method"
        
        # Udpipe method
        if [ "$method" == "udpipe" ]; then
            tagger=$(echo "$dict" | jq -r '.tagger')
            parser=$(echo "$dict" | jq -r '.parser')

            # Add the tagger parameter
            if $tagger; then
                source_files_parameters["$source_file|tagger"]="$tagger"
                # command line parameter
                source_files_parameters_in_line["$source_file"]+="--tagger "
            fi

            # Add the parser parameter
            if $parser; then
                source_files_parameters["$source_file|parser"]="$parser"
                # command line parameter
                source_files_parameters_in_line["$source_file"]+="--parser "
            fi
        fi

        # add the parseme corpus into the array
        source_files+=("$source_file")
    done
}


########################################
# Save the configuration file
# Parameters: None
function save_config() {
    # The script run was successful.
    if [ $? -eq 0 ]; then
        # Save user inputs to the config file
        updated_json=$(jq --arg language "$language_input" '.language = $language' "$config_file") 
        updated_json=$(jq --arg treebank "$treebank_input" '.treebank = $treebank' <<< "$updated_json")
        updated_json=$(jq --arg uri "$uri_input" '.uri = $uri' <<< "$updated_json") 
        updated_json=$(jq --arg language_repository "$language_repository_input" '.language_repository = $language_repository' <<< "$updated_json")
        # Add the boolean value to the JSON file using jq
        updated_json=$(jq --arg key "verbose" --argjson value "$verbose_input" '. + {($key): $value}' <<< "$updated_json")
        echo "$updated_json" | jq '.' > "$config_file"
    fi
}


# Read parameters from the JSON file using jq
language=$(jq -r '.language' "$config_file")
treebank=$(jq -r '.treebank' "$config_file")
uri=$(jq -r '.uri' "$config_file")
language_repository=$(jq -r '.language_repository' "$config_file")
verbose=$(jq -r '.verbose' "$config_file")

path_input=
# an array of parseme corpus
source_files=()
# Enable associative arrays
declare -A source_files_parameters_in_line
declare -A source_files_parameters

# Prompt the user for parameter inputs
read_input

# Define the list of choices
source_files+=("Quit")

echo ""
while true; do
    # Print the choices and ask the user to select one
    echo "Please choose a source parseme file for the morphosyntax reannotation:"
    select choice in "${source_files[@]}"; do
        if [ -z "$choice" ]; then
            echo "Invalid choice, please try again."
        elif [ "$choice" == "Quit" ]; then
            echo "Goodbye!"
            exit 0
        else
            break
        fi
    done

    echo "You chose: $choice"
    echo ""
    echo "========================================================================================"
    echo "===> Re-annotating the parseme corpus $choice"
    echo "========================================================================================"
    
    # udtreebank method
    if [ ${source_files_parameters[$choice"|method"]} == "udtreebank" ]; then
        # Run the script reannotate-morphosyntax.sh
        if [ -n "$path_input" ] && $verbose_input; then
            echo "${REANNOTATION_MORPHOSYNTAX} --lang $language_input --treebank $treebank_input --uri $uri_input --path $path_input ${source_files_parameters_in_line[$choice]} --verbose"
            ${REANNOTATION_MORPHOSYNTAX} --lang $language_input --treebank $treebank_input --uri $uri_input --path $path_input ${source_files_parameters_in_line[$choice]} --verbose
        elif [ -n "$path_input" ] && ! $verbose_input; then
            echo "${REANNOTATION_MORPHOSYNTAX} --lang $language_input --treebank $treebank_input --uri $uri_input --path $path_input ${source_files_parameters_in_line[$choice]}"
            ${REANNOTATION_MORPHOSYNTAX} --lang $language_input --treebank $treebank_input --uri $uri_input --path $path_input ${source_files_parameters_in_line[$choice]}
        elif [ ! -n "$path_input" ] && $verbose_input; then
            echo "${REANNOTATION_MORPHOSYNTAX} --lang $language_input --treebank $treebank_input --uri $uri_input ${source_files_parameters_in_line[$choice]} --verbose"
            ${REANNOTATION_MORPHOSYNTAX} --lang $language_input --treebank $treebank_input --uri $uri_input ${source_files_parameters_in_line[$choice]} --verbose
        else
            echo "${REANNOTATION_MORPHOSYNTAX} --lang $language_input --treebank $treebank_input --uri $uri_input ${source_files_parameters_in_line[$choice]}"
            ${REANNOTATION_MORPHOSYNTAX} --lang $language_input --treebank $treebank_input --uri $uri_input ${source_files_parameters_in_line[$choice]}
        fi
    # udpipe method
    elif [ ${source_files_parameters[$choice"|method"]} == "udpipe" ]; then
        # Run the script reannotate-morphosyntax.sh
        echo "${REANNOTATION_MORPHOSYNTAX} --lang $language_input ${source_files_parameters_in_line[$choice]}"
        ${REANNOTATION_MORPHOSYNTAX} --lang $language_input ${source_files_parameters_in_line[$choice]}
    else
        # error
        echo "Only two method of synchronisation udpipe and udtreebank are available"
        exit 2
    fi
    echo ""

    # Save the configuration file
    save_config
done


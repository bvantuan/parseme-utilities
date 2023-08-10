#! /bin/bash
# This script updates the morphosyntactic annotation in a .cupt file with 
# the results obtained from the latest UDPipe model or corpus.

set -o nounset    # Using "$UNDEF" var raises error

#Current directory
HERE="$(cd "$(dirname "$0")" && pwd)"
REANNOTATION_MORPHOSYNTAX=$HERE/reannotate-morphosyntax.sh

#Language codes and the prefixes of the names of the corresponding UDPipe models (if several models per language, the one with the best LAS for gold tokanization is taken)
#See here: https://ufal.mff.cuni.cz/udpipe/2/models
declare -A LANGS=( [AR]=arabic [BG]=bulgarian [CS]=czech-pdt [DE]=german-hdt [EL]=greek-gdt [EN]=english-atis [ES]=spanish-ancora [EU]=basque [FA]=persian-perdt [FR]=french-sequoia [HE]=hebrew-iahltwiki  [HI]=hindi-hdtb [HR]=croatian [HU]=hungarian [IT]=italian-partut [LT]=lithuanian-alksnis [MT]=maltese-mudt [PL]=polish-lfg [PT]=portuguese [RO]=romanian-rrt [SL]=slovenian-ssj [SV]=swedish-talbanken [TR]=turkish-tourism [ZH]=chinese-gsd)


########################################
usage() {
    echo "Usage: $(basename "$0") [-h] [-c config]" 
    echo "Reannotate the morphosyntax in all the .cupt files of a language from framework Universal Dependencies (UD)(treebanks or latest UDPipe model)"
    echo "Any existing information other than tokenisation and MWE annotation (columns 1, 2 and 11) will be overwritten."
    echo "The resulting .cupt files are placed in the directory 'REANNOTATION' which is under the same directory as the input files, with extension .new.cupt."

    echo ""
    echo "Example: ./reannotate-morphosyntax-from-config.sh -c configs/config_PL.json"

    echo ""
    echo "Parameters: "
    echo -e "\t -h, --help \t\t Display this help message"
    echo -e "\t -c, --config \t\t A configuration file containing all the parameters needed for the reannotation"
}


########################################
fail() {
    echo "Error: $1"
    exit 1
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
            fail "Invalid option: $1"
            ;;
    esac
done

# A configuration file is required
if [ ! -n "$config_file" ]; then
    fail "A configuration file is required using option '-c'!"
else
    if [ ! -f "$config_file" ]; then
        fail "The configuration file doesn't exist!"
    fi
fi

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
        fail "Invalid language code"
    fi

    # Prompt the user for a language repository input
    read -p "The path of the language repository: [$language_repository] " language_repository_input
    if [ ! -n "$language_repository_input" ]; then
        language_repository_input="$language_repository"
    else
        if [ ! -d $language_repository_input ]; then
            # error
            fail "Expected a directory for the language repository"
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
        source_files_parameters_in_line["$source_file"]="--source $language_repository_input/$source_file --method $method "
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
        # UDtreebank method
        elif [ "$method" == "udtreebank" ]; then
            # arrays of treebanks
            readarray -t treebanks < <(echo "$dict" | jq -r '.treebank' | jq -cr '.[]')
            # arrays of uris
            readarray -t corpus_uris < <(echo "$dict" | jq -r '.uri' | jq -cr '.[]')
            source_files_parameters["$source_file|treebanks"]="${treebanks[@]}"
            source_files_parameters["$source_file|uris"]="${corpus_uris[@]}"
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
        updated_json=$(jq --arg language_repository "$language_repository_input" '.language_repository = $language_repository' <<< "$updated_json")
        # Add the boolean value to the JSON file using jq
        updated_json=$(jq --arg key "verbose" --argjson value "$verbose_input" '. + {($key): $value}' <<< "$updated_json")
        echo "$updated_json" | jq '.' > "$config_file"
    fi
}


########################################
# Install the necessary packages
function install_packages() {
    # Check if the jq package is installed
    if ! command -v jq >/dev/null 2>&1; then
        echo "Installing jq package"
        sudo apt-get install jq
    fi
    echo "========================================================================================"
}

# Install the necessary packages
install_packages

# Read parameters from the JSON file using jq
language=$(jq -r '.language' "$config_file")
language_repository=$(jq -r '.language_repository' "$config_file")
verbose=$(jq -r '.verbose' "$config_file")

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

    # udtreebank method
    if [ ${source_files_parameters[$choice"|method"]} == "udtreebank" ]; then
        # Prompt the user for treebanks input
        echo "Directories of treebanks of Universal Dependencies (UD) synchronized with the $choice corpus: [${source_files_parameters[$source_file"|treebanks"]}] "
        read -a treebanks_input
        if [ "${#treebanks_input[@]}" -eq 0 ]; then
            read -a treebanks_input <<< ${source_files_parameters[$source_file"|treebanks"]}
        else
            for treebank in "${treebanks_input[@]}"; do
                if [ ! -d "$treebank" ]; then
                    # error
                    fail "Expected a directory for the treebank"
                fi
            done
        fi

        # Prompt the user for uris
        echo "The persistent URIs of the original UD treebanks: [${source_files_parameters[$source_file"|uris"]}] " 
        read -a uris_input
        if [ "${#uris_input[@]}" -eq 0 ]; then
            read -a uris_input <<< ${source_files_parameters[$source_file"|uris"]}
        fi
    fi

    echo "========================================================================================"
    echo "===> Re-annotating the parseme corpus $choice"
    echo "========================================================================================"
    
    # udtreebank method
    if [ ${source_files_parameters[$choice"|method"]} == "udtreebank" ]; then
        # Run the script reannotate-morphosyntax.sh
        if $verbose_input; then
            echo "${REANNOTATION_MORPHOSYNTAX} --language $language_input ${source_files_parameters_in_line[$choice]} --treebank ${treebanks_input[@]} --uri ${uris_input[@]}--verbose"
            ${REANNOTATION_MORPHOSYNTAX} --language $language_input ${source_files_parameters_in_line[$choice]} --treebank ${treebanks_input[@]} --uri ${uris_input[@]} --verbose
        else
            echo "${REANNOTATION_MORPHOSYNTAX} --language $language_input ${source_files_parameters_in_line[$choice]} --treebank ${treebanks_input[@]} --uri ${uris_input[@]}"
            ${REANNOTATION_MORPHOSYNTAX} --language $language_input ${source_files_parameters_in_line[$choice]} --treebank ${treebanks_input[@]} --uri ${uris_input[@]}
        fi
    # udpipe method
    elif [ ${source_files_parameters[$choice"|method"]} == "udpipe" ]; then
        # Run the script reannotate-morphosyntax.sh
        echo "${REANNOTATION_MORPHOSYNTAX} --language $language_input ${source_files_parameters_in_line[$choice]}"
        ${REANNOTATION_MORPHOSYNTAX} --language $language_input ${source_files_parameters_in_line[$choice]}
    else
        # error
        echo "Only two method of synchronisation udpipe and udtreebank are available"
        exit 2
    fi
    # Save the configuration file
    if [ $? == 0 ]; then
        save_config
    fi

    echo ""
done


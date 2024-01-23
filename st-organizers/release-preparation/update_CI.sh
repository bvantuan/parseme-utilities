#! /bin/bash
# This script updates the CI process within all PARSEME's language repositories


# set -o errexit    # Exit on error, do not continue quietly

#Current directory
HERE="$(cd "$(dirname "$0")" && pwd)"
# PARSEME language codes
LANGUAGES_CODE_FILE=$HERE/CI-CD/data/languages.code
# CI-CD folder
CI_CD_FOLDER=$HERE/CI-CD

# Initialize an empty array of language codes
languages=()

# Read each line of the file
while IFS= read -r line; do
    languages+=("$line")
done < "$LANGUAGES_CODE_FILE"

# For every language
for language in "${languages[@]}"; do
    # convert a language code to lowercase
    language_code=$(echo "$language" | tr '[:upper:]' '[:lower:]')
    # remove leading and trailing spaces
    language_code=$(echo "$language_code" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    echo "Language: $language"
    # clone the language repository
    git clone git@gitlab.com:parseme/parseme_corpus_$language_code.git
    cd parseme_corpus_$language_code
    # Switch to dev branch
    if ! git checkout dev; then
        git branch dev
        git checkout dev
    fi

    # create .CI-CD folder
    mkdir -p not_to_release/.CI-CD/
    # copy the latest CI to the folder
    cp -r $CI_CD_FOLDER/. not_to_release/.CI-CD/
    mv not_to_release/.CI-CD/.gitlab-ci.yml .
    # Commit and push changes
    git add not_to_release/.CI-CD/* .gitlab-ci.yml
    git commit -m "update CI"
    git push origin dev
    cd ..
    sudo rm -r parseme_corpus_$language_code
done
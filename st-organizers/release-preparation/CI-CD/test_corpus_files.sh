#! /bin/bash
# Verifies the presence of CUPT files, README.md, and not_to_release folder in a directory and ensures no other files are present.

exec </dev/null   # Don't hang if a script tries to read from stdin

HERE="$(cd "$(dirname "$0")" && pwd)"
DIR_CUPT=$HERE/../../
# Extract the part after the last underscore
LANGUAGE="${REPO_NAME##*_}"

# Change to the root directory
cd "$DIR_CUPT"

# Same as `echo`, but output in red
red_echo() {
    echo -e "\033[31;1m$@\033[0m"
}

# Same as `echo`, but output in green
green_echo() {
    echo -e "\033[32;1m$@\033[0m"
}

# Initialize counters
cupt_files_count=0
other_files_count=0

# Check for CUPT files and other files
for file in *; do
    if [[ $file == *.cupt ]]; then
        ((cupt_files_count++))
    elif [[ $file != "README.md" && $file != "not_to_release" ]]; then
        ((other_files_count++))
    fi
done

# Check for README.md and not_to_release
readme_exists=0
not_to_release_exists=0
[[ -e "README.md" ]] && readme_exists=1
[[ -d "not_to_release" ]] && not_to_release_exists=1


# Output results
if [[ $cupt_files_count -gt 0 && $readme_exists -eq 1 && $not_to_release_exists -eq 1 && $other_files_count -eq 0 ]]; then
    green_echo "========================================================================================"
    green_echo "All checks passed: CUPT files, README.md, and not_to_release folder are present with no other files."
    green_echo "========================================================================================"
else
    red_echo "========================================================================================"
    red_echo "Check failed."
    [[ $cupt_files_count -eq 0 ]] && red_echo "No CUPT files found."
    [[ $readme_exists -eq 0 ]] && red_echo "README.md not found."
    [[ $not_to_release_exists -eq 0 ]] && red_echo "not_to_release folder not found."
    [[ $other_files_count -ne 0 ]] && red_echo "There are other files or folders present."
    red_echo "========================================================================================"
    exit 1
fi

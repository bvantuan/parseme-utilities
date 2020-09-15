
# Shared task 1.2 system evaluation phase
-----------------------------------------

This directory contains scripts used to run the shared task system 
evaluation and publish the system results. In all commands and examples, 
`$EDITION` corresponds to the edition number of the shared task, e.g. 
`1.2`. In all commands and examples, `$DATADEV` corresponds to the 
location of the folder `sharedtask-data-dev` cloned in step 0. Before
starting, please **update the list of languages** in the variable 
`LANGUAGES` in the following scripts:
* `step1-runEval.sh`
* `step2-results2html.sh`
* `step3-results2html-cat.all.sh`
* `step4-macroave2html.sh`

--------------------------------------------------------------

## Step 0 - download and save results from SOFTCONF (manual)

1. Clone or pull the `sharedtask-data-dev` repository: 
   [https://gitlab.com/parseme/sharedtask-data-dev]
2. Create a folder `${DATADEV}/${EDITION}/system-results` 
   `${DATADEV}` is the location where you cloned the repository.
3. Create one folder per system with the system name so that each folder 
   ends with `.closed` or `.open` depending on the track.
4. Download the system results from SOFTCONF and uncompress them in the
   folder created above. Ensure that each system folder contains one 
   folder per language (for which the system competes) and a single file 
   named `test.system.cupt` in it.

--------------------------------------------------------------

## Step 1 - evaluate each system/language independently

This script will run the evaluation script for each system and each 
language, and save the outcome in the corresponding folder (in a 
`results.txt` and `results-traindev.txt` files). Please **update the 
list of languages** in the variable `LANGUAGES`:

```bash
./step1-runEval.sh ${DATADEV}/${EDITION}/system-results $DATADEV/$EDITION/preliminary-sharedtask-data/
```

The `results-traindev.txt` file contains the results using train+dev to
calculate the unseen F1 scores. This version is not the one reported in
the official scores, but it was calculated for the shared task paper
to ensure coherence with splitting strategy (300 unseen wrt. train+dev!)

TODO: In the future, modify th evaluation script so that it outputs Seen-in-traindev (rather than Seen-in-train), Unseen-in-traindev (rather than Unseen-in-train, Variant-of-traindev (rather than Variant-of-train) and Identical-to-traindev (rather than Identical-to-train) if the unseen VMWEs are defined with respect ti train+dev rather than train alone.

--------------------------------------------------------------

## Step 2 - create one ranking per language

Convert the global evaluation (for all categories in total) to HTML 
tables, one per language. Before running the script, please **update the 
list of languages** in the variable `LANGUAGES`. The resulting `.html` 
pages are printed into `results.html` and `results-traindev.html` files 
in `sharedtask-data-dev/$EDITION/system-results`:

```bash
./step2-results2html.sh ${DATADEV}/${EDITION}/system-results
```

--------------------------------------------------------------

## Step 3 - create category-specific rankings

Convert the (unranked) per-category evaluation results to HTML tables, 
one per language. The resulting `.html` page is printed into the 
`results-cat.html` file in `sharedtask-data-dev/$EDITION/system-results`:

```bash
./step3-results2html-cat.all.sh ${DATADEV}/${EDITION}/system-results
```

--------------------------------------------------------------

## Step 4 - calculate and format the macro-averages

Convert the macro-average results to HTML tables. The resulting .html 
pages are printed into the `macro-ave.html` and `macro-ave-traindev.html` 
files in `sharedtask-data-dev/$EDITION/system-results`:

```bash
./step4-macroave2html.sh ${DATADEV}/${EDITION}/system-results 
```

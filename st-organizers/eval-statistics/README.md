This directory contains scripts used to run the shared task system evaluation and publish the system results.

Perform the following steps:

--------------------------------------------------------------

## Step 0

Manually save the system results in the `sharedtask-data-dev/$EDITION/system-results` folder so that:
- `$EDITION` corresponds to the edition of the shared task, e.g. `1.2`
- there is one folder per system, with the `.closed` or `.open` extension
- each system folder contains one folder per language (for which the system competes), and a single file named `test.system.cupt` in it

--------------------------------------------------------------

## Step 1 - evaluate each system/language independently

This script will run the evaluation script for each system and each language, and save the outcome in the corresponding folder (in a `results.txt` file). please **update the list of languages** in the variable `LANGUAGES`:

```bash
./step1-runEval.sh ~/shared-task/Gitlab/sharedtask-data-dev/$EDITION/system-results ~/shared-task/Gitlab/sharedtask-data-dev/$EDITION/preliminary-sharedtask-data/
```

--------------------------------------------------------------

## Step 2 - create one ranking per language

Convert the global evaluation (for all categories in total) to HTML tables, one per language. Before running the script, please **update the list of languages** in the variable `LANGUAGES`. The resulting `.html` page is printed into the `results.html` file in `sharedtask-data-dev/$EDITION/system-results`:

```bash
./step2-results2html.sh ~/shared-task/Gitlab/sharedtask-data-dev/$EDITION/system-results
```

--------------------------------------------------------------

## Step 3 - create category-specific rankings

Convert the (unranked) per-category evaluation results to HTML tables, one per language. The resulting `.html` page is printed into the `results-cat.html` file in `sharedtask-data-dev/$EDITION/system-results`:

```bash
./step3-results2html-cat.all.sh ~/shared-task/Gitlab/sharedtask-data-dev/$EDITION/system-results
```

--------------------------------------------------------------

## Step 4

Convert the macro-average results to HTML tables. The resulting .html page is printed into the macro-ave.html file in sharedtask-data-dev/$EDITION/system-results:

./step4-macroave2html.sh ~/shared-task/Gitlab/sharedtask-data-dev/$EDITION/system-results

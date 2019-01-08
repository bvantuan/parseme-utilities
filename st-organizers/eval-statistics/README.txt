This directory contains scripts used to run the shared task system evaluation and publish the system results.

Perform the following steps:

=====
Step 0

Manually save the system results in the sharedtask-data-dev/1.1/system-results folder so that:
- there is one folder per system, with the .closed or .open extension
- each system folder contains one folder per language (for which the system competes), and one test.system.cupt file in it

=====
Step 1

Run the evaluation script for each system and each language and save the outcome in the corresponding folder (in a results.txt file):

./step1-runEval.sh ~/shared-task/Gitlab/sharedtask-data-dev/1.1/system-results ~/shared-task/Gitlab/sharedtask-data-dev/1.1/preliminary-sharedtask-data/

=====
Step 2

Convert the global evaluation (for all categories in total) to HTML tables, one per language. The resulting .html page is printed into the results.html file in sharedtask-data-dev/1.1/system-results:

./step2-results2html.sh ~/shared-task/Gitlab/sharedtask-data-dev/1.1/system-results 

=====
Step 3

Convert the (unranked) per-category evaluation results to HTML tables, one per language. The resulting .html page is printed into the results-cat.html file in sharedtask-data-dev/1.1/system-results:

./step3-results2html-cat.all.sh ~/shared-task/Gitlab/sharedtask-data-dev/1.1/system-results

=====
Step 4

Convert the macro-average results to HTML tables. The resulting .html page is printed into the macro-ave.html file in sharedtask-data-dev/1.1/system-results:

./step4-macroave2html.sh ~/shared-task/Gitlab/sharedtask-data-dev/1.1/system-results


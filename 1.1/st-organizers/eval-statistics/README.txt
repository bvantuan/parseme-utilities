This directory contains scripts used to run the shared task system evaluation and publish the system results.

Perform teh following steps:

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

Rank and format the global evaluation (for all categories in total). If different systems run for a given language in both tracks, the rankings are done separately.
As a result, a file named <LANG>.ranked.txt is created for every language in $1, containing ranked results of all systems for this language:

./step2-formatEvalResults.sh ~/shared-task/Gitlab/sharedtask-data-dev/1.1/system-results ~/shared-task/Gitlab/sharedtask-data-dev/1.1/preliminary-sharedtask-data/

=====
Step 3

Convert the global evaluation (for all categories in total) to HTML tables, one per language. The resulting .html page is printed into the results.html file in sharedtask-data-dev/1.1/system-results:

./step3-results2html.all.sh ~/shared-task/Gitlab/sharedtask-data-dev/1.1/system-results

=====
Step 4

Format the (unranked) per-category evaluation results.
As a result, a file named <LANG>.percat.txt is created for every language in $1, containing (unranked) results of all systems for this language:

./step4-formatEvalResults-cat.sh ~/shared-task/Gitlab/sharedtask-data-dev/1.1/system-results ~/shared-task/Gitlab/sharedtask-data-dev/1.1/preliminary-sharedtask-data/

=====
Step 5

Convert the (unranked) per-category evaluation results to HTML tables, one per language. The resulting .html page is printed into the results-cat.html file in sharedtask-data-dev/1.1/system-results:

./step5-results2html-cat.all.sh ~/shared-task/Gitlab/sharedtask-data-dev/1.1/system-results



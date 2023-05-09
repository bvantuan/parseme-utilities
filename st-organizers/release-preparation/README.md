This directory contains scripts used to prepare the PARSEME corpora releases in versions 1.1 and 1.2.

* `splitTrainTestDev-1.1.py` splits the whole corpus into TRAIN/DEV/TEST subcorpora depending on its size, in terms of annotated VMWEs (this split method was not used for the **1.2 edition**, see [this method](../splitting) instead): 
  * less than 550 VMWEs: 10% of the VMWEs for TEST; 90% for TRAIN; no DEV is created
  * at least 550 but less than 1500 VMWEs: 500 VMWEs for TEST; the rest for TRAIN; no DEV is created
  * at least 1500 but less than 5000 VMWEs: 500 VMWEs for TEST and DEV (each); the rest for TRAIN
  * at least 5000 VMWEs: 10% of VMWEs for TEST and DEV (each); 80% for TRAIN
  
* `calcSubcorpusJson.py` can be used with `splitTrainTestDev-1.1.py` to define subcorpora that should be taken into account when splitting, so that train, dev and test have balanced amounts of data from each subcorpus.
  
* `make_summary_table.sh` creates the tables used on the shared task website and papers in TXT, HTML or LATEX. It goes through the sharedtask-data-dev repository and, for each language, calculate the stats (nb. of sentences, VMWEs, per category...)

* `gen_blind.sh` generates a blind CUPT file by removing all annotations in the 11th column of test.cupt files in the sharedtask-data-dev files.

* `prepare_languages-XX.sh` where XX is the version of the shared task. Runs scripts to calculate statistics and create blind test sets for all languages.

* `correct-multiword-tokens.py` removes any MWE annotation from multiword tokens (ranges), propagate it onto the corresponding words that are part of the multiword token.

* `add_unseen_stats.sh` adds statistics about unseen MWEs to the stats files when present in the log files.

* `reannotate-morphosyntax.sh` reannotates the morphosyntax in a .cupt file from framework Universal Dependencies (UD)(treebanks or latest UDPipe model). Any existing information other than tokenisation and MWE annotation (columns 1, 2 and 11) will be overwritten. The resulting .cupt files are placed in the directory 'REANNOTATION' which is under the same directory as the input files, with extension .new.cupt.

* `reannotate-morphosyntax-from-config.sh` is the same functionality as the script `reannotate-morphosyntax.sh`, but more user-friendly as all parameters are placed in a configuration file.

* `parseme_validate.py` is a CUPT validation script. The validation tests are organized to three levels.
  * Level 1: Test only the CUPT backbone: order of lines, newline encoding, core tests that check the file integrity.
  * Level 2: PARSEME and UD contents.
  * Level 3: PARSEME releases: NotMWE tag excluded, more constraints on metadata.


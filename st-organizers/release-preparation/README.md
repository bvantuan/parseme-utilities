This directory contains scripts unsed to prepare the PARSEME corpora releases in versions 1.1 and 1.2.

* `splitTrainTestDev.py` splits the whole corpus into TRAIN/DEV/TEST subcorpora depending on the size of the total corpus
  * if less than 550 VMWEs are annotated, TEST will contain 10% of the corpus (randomly selected), TRAIN the remaining 90% and no DEV is created
  * if at least 550 VMWEs but less than 1500 VMWEs are annotated, TEST will contain 500 VMWEs, TRAIN the remaining part, and no DEV is created
  * if at least 1500 VMWEs but less than 5000 VMWEs are annotated, TEST and DEV will contain 500 VMWEs each, and TRAIN the remaining part
  * otherwise (at least 5000 VMWEs are annotated), TEST and DEV will contain 10% of VMWEs each, and TRAIN the ramaining 20%

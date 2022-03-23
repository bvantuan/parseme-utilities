This directory contains scripts used to prepare the PARSEME corpora releases in versions 1.1 and 1.2.

* `splitTrainTestDev.py` splits the whole corpus into TRAIN/DEV/TEST subcorpora depending on its size, in terms of annotated VMWEs (this split method was not used for the **1.2 edition**, see [this method](../splitting) instead*): 
  * less than 550 VMWEs: 10% of the VMWEs for TEST; 90% for TRAIN; no DEV is created
  * at least 550 but less than 1500 VMWEs: 500 VMWEs for TEST; the rest for TRAIN; no DEV is created
  * at least 1500 but less than 5000 VMWEs: 500 VMWEs for TEST and DEV (each); the rest for TRAIN
  * at least 5000 VMWEs: 10% of VMWEs for TEST and DEV (each); 80% for TRAIN

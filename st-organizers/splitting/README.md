# Prerequisites

* Python in version 3.6 or higher
* The Python [CUPT parsing library][cupt-parser], version `0.1.1` or higher (follow the link for installation instructions)

# Usage

### Script

To perform splitting for several/all languages:
```
utilities/st-organizers/splitting$ ./scripts/run_split_1.2.sh <file-with-langs> <origininal-corpora> <preliminary-sharedtask-data>
```
where `<file-with-langs>` is a file with lower-case language codes, one per line, e.g.:
```
fr
de
pl
zh
el
...
```
`<original-corpora>` is a path to the directory with the gitlab repositories (`parseme_corpus_fr`, `parseme_corpus_de`, etc.), and `<preliminary-sharedtask-data>` is a path to the `sharedtask-data-dev/1.2/preliminary-sharedtask-data` directory of the `sharedtask-data-dev` repository.

The `run_split_1.2.sh` script uses `split_cupt.py` described [below](#splitting) to perform splitting for the individual languages.

### Splitting

Use the following command to split the dataset into `train.cupt`, `dev.cupt`,
and `test.cupt`, with the target number of unseen MWEs in the development part
(e.g. `100`) and the test part (e.g.  `300`):
```
./split_cupt.py split --unseen-dev 100 --unseen-test 300 -i file1.cupt file2.cupt ... --train-path train.cupt --dev-path dev.cupt --test-path test.cupt -n 50
```
The `-n` option determines the number of random splits performed on the input
dataset.  The split with the numbers of unseen MWEs closest to the target
values (here: `100` and `300` in `dev` and `test`, respectively) is saved in
the files following `--train-path`, `--dev-path`, and `--test-path`.

**NOTE**: the `--alt` option determines how the number of unseen MWEs in `test` is calculated:
* Without `--alt`, it is calculated w.r.t. `train` only.
* With `--alt`, it is calculated w.r.t. both `train` and `dev`.

### Estimation

To estimate the number of sentences which should be put in the test set so as
to obtain the target number (e.g., `300`) of unseen MWEs:
```
./split_cupt.py estimate --unseen-mwes 300 -i file1.cupt file2.cupt ...
```
where `file1.cupt`, `file2.cupt`, ... are the input CUPT files.

Let the size of a set be it's number of sentences. 
The tool performs a binary search (within the sequence `1`..`M-1`, where `M` is the size of the entire dataset) for the appropriate size of the test set.  In each step, for
the given test set size, the input dataset (all files following `-i`) is randomly split into a train set and
a test set a given number of times (`10` by default, you can increase it using `-n` to get more reliable results) and
the average number of unseen MWEs (as well as average unseen/seen ratio) in the test set is determined.


<!---
##### Unseen/seen ratio

You can additionally use the `unseen-ratio` option to specify the target unseen/seen MWE ratio in the test part.  In this case, the tool will search for a split which is close to having the specified number of unseen MWEs and the specified unseen/seen ratio at the same time.
```
./split_cupt.py split -unseen-mwes 300 -unseen-ratio 0.5 -test-size 1000 -i file1.cupt file2.cupt ... -train-path train.cupt -test-path test.cupt -n 100
```
Note however that specifying the values of `-unseen-ratio` and `-test-size` significantly different from those reported by the [esimation mode](#esimation) will likely not work very well, since both the no. of unseen MWEs and the unseen/seen ratio are largely determined by the size of the test set (at least in our case, where we do all the splits randomly).
-->

### Validation

Use the [evaluation script][parseme-eval-1.1] from the PARSEME Shared Task 1.1
to check if the number of unseen MWEs in the test set is correct.


[cupt-parser]: https://gitlab.com/parseme/cupt-parser#python-cupt-parser "Python CUPT parser"
[parseme-eval-1.1]: https://gitlab.com/parseme/sharedtask-data/blob/master/1.1/bin/evaluate.py "PARSEME ST-1.1 evaluation script"

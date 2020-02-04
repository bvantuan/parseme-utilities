# Prerequisities

## CUPT Parser

Before using the tool, install the Python [CUPT parsing library][cupt-parser].

# Usage

## Estimation

To estimate the number of sentences which should be put in the test set so as
to obtain the target number (e.g., `300`) of unseen MWEs:
```
./split_cupt.py estimate --unknown-mwes 300 -i file1.cupt file2.cupt ...
```
where `file1.cupt`, `file2.cupt`, ... are the input CUPT files.

The tool performs binary search for the appropriate size of the test set.  For
a given test set size, the input dataset is randomly split into train set and
test set a given number of times (`10` by default, use `-n` to change it) and
the average number of unseen MWEs in the test set is determined.

## Splitting

Once the target size of the test set is estimated (e.g., `1000` sentences), you
can use the following command to split the dataset into `train.cupt` and
`test.cupt` with the target number of unseen MWEs (e.g., `300`) in the test
part:
```
./split_cupt.py split --unknown-mwes 300 --test-size 1000 -i file1.cupt file2.cupt ... --train-path train.cupt --test-path test.cupt -n 100
```
Again, the `-n` option determines the number of random splits performed on the
input datset.  The split with the number of unseen MWEs closest to the target
number (here: `300`) is kept in the end.

## Validation

Use the [evaluation script][parseme-eval-1.1] from the PARSEME Shared Task 1.1
to check if the number of unseen MWEs in the test set is correct.


[parseme-eval-1.1]: https://gitlab.com/parseme/sharedtask-data/blob/master/1.1/bin/evaluate.py "PARSEME ST-1.1 evaluation script"

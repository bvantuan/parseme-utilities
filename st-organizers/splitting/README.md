# Prerequisities

* Python in version 3.6 or higher
* The Python [CUPT parsing library][cupt-parser] (follow the link for installation instructions)

# Usage

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

### Splitting

Once the target size of the test set is estimated (e.g., `1000` sentences), you
can use the following command to split the dataset into `train.cupt` and
`test.cupt` with the target number of unseen MWEs (e.g., `300`) in the test
part:
```
./split_cupt.py split --unseen-mwes 300 --test-size 1000 -i file1.cupt file2.cupt ... --train-path train.cupt --test-path test.cupt -n 100
```
Again, the `-n` option determines the number of random splits performed on the
input datset.  The split with the number of unseen MWEs closest to the target
number (here: `300`) is saved in the files following `--train-path` and `--test-path`.

##### Unseen/seen ratio

You can additionally use the `unseen-ratio` option to specify the target unseen/seen MWE ratio in the test part.  In this case, the tool will search for a split which is close to having the specified number of unseen MWEs and the specified unseen/seen ratio at the same time.
```
./split_cupt.py split --unseen-mwes 300 --unseen-ratio 0.5 --test-size 1000 -i file1.cupt file2.cupt ... --train-path train.cupt --test-path test.cupt -n 100
```
Note however that specifying the values of `--unseen-ratio` and `--test-size` significantly different from those reported by the [esimation mode](#esimation) will likely not work very well, since both the no. of unseen MWEs and the unseen/seen ratio are largely determined by the size of the test set (at least in our case, where we do all the splits randomly).

<!---
**Number of unseen MWEs re-estimation**.  Use the `--over` option to re-estimate the target no. of unseen MWEs.  This is done by:
* Repeatedly splitting the dataset to train/test parts
* Keeping only the splits with the number of unseen MWEs exceeding the one provided on input with `unseen-mwes`
* Taking the average no. of unseen MWEs from thus obtained collection of train/test splits

After that, the newly estimated target number of unseen MWEs is adopted and the script proceeds as without the `--over` option.
-->

### Validation

Use the [evaluation script][parseme-eval-1.1] from the PARSEME Shared Task 1.1
to check if the number of unseen MWEs in the test set is correct.


[cupt-parser]: https://gitlab.com/parseme/cupt-parser#python-cupt-parser "Python CUPT parser"
[parseme-eval-1.1]: https://gitlab.com/parseme/sharedtask-data/blob/master/1.1/bin/evaluate.py "PARSEME ST-1.1 evaluation script"

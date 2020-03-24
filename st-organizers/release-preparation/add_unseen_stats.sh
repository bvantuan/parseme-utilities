#!/bin/sh

#Add the statistics about the number and ratio of unseen VMWEs from XX/logs/split-stats.log files to train-stats.md dev-stats.md and test-stats.md files
#Parameter:
# $1 = the directory containing the preliminary shared task data
#
# Sample call:
# ./add_unseen_stats.sh ~/shared-task/Gitlab/sharedtask-data-dev/preliminary-sharedtask-data/

if [ $# -ne 1 ]; then
  echo "Usage: "
  echo "  $0 PARSEME_PRELIMINARY_SHAREDTASK_DATA_DIR"
  exit -1
fi

for lang in `ls $1`; do
  unseen_in_dev=`grep 'Number of unseen MWEs in dev:' $1/$lang/logs/split-stats.log | cut -d' ' -f7`
  ratio_unseen_in_dev=`grep 'Unseen/all MWE ratio in dev:' $1/$lang/logs/split-stats.log | cut -d' ' -f6`
  unseen_in_test_wrt_train=`grep 'Number of unseen MWEs in test w.r.t train:' $1/$lang/logs/split-stats.log | cut -d' ' -f9`
  ratio_unseen_in_test_wrt_train=`grep 'Unseen/all MWE ratio in test w.r.t train:' $1/$lang/logs/split-stats.log | cut -d' ' -f8`
  unseen_in_test_wrt_train_dev=`grep 'Number of unseen MWEs in test w.r.t train+dev:' $1/$lang/logs/split-stats.log | cut -d' ' -f9`
  ratio_unseen_in_test_wrt_train_dev=`grep 'Unseen/all MWE ratio in test w.r.t train+dev:' $1/$lang/logs/split-stats.log | cut -d' ' -f8`
#  echo
#  echo "================="
#  echo $lang
#  echo "unseen_in_dev=$unseen_in_dev"
#  echo "ratio_unseen_in_dev=$ratio_unseen_in_dev"
#  echo "unseen_in_test_wrt_train=$unseen_in_test_wrt_train"
#  echo "ratio_unseen_in_test_wrt_train=$ratio_unseen_in_test_wrt_train"
#  echo "unseen_in_test_wrt_train_dev=$unseen_in_test_wrt_train_dev"
#  echo "ratio_unseen_in_test_wrt_train_dev=$ratio_unseen_in_test_wrt_train_dev"
  echo "Unseen w.r.t. train: $unseen_in_dev" >> $1/$lang/dev-stats.md
  echo "Ratio of unseen w.r.t. train: $ratio_unseen_in_dev" >> $1/$lang/dev-stats.md
  echo "Unseen w.r.t. train: $unseen_in_test_wrt_train" >> $1/$lang/test-stats.md
  echo "Ratio of unseen w.r.t. train: $ratio_unseen_in_test_wrt_train" >> $1/$lang/test-stats.md
  echo "Unseen w.r.t. train+dev: $unseen_in_test_wrt_train_dev" >> $1/$lang/test-stats.md
  echo "Ratio of unseen w.r.t. train+dev: $ratio_unseen_in_test_wrt_train_dev" >> $1/$lang/test-stats.md
done



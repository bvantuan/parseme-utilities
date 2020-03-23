__THIS_LIB_PATH="$(dirname "${BASH_SOURCE[0]}")"


if ! test "${PARSEME_SHAREDTASK_DATA_DEV+set}"; then
    __psdd="$__THIS_LIB_PATH/../../sharedtask-data-dev/1.2"
    echo $__psdd
    if test -d "$__psdd"; then
        export PARSEME_SHAREDTASK_DATA_DEV="$(cd "$__psdd"; pwd)"
        echo "WARNING: Environment variable PARSEME_SHAREDTASK_DATA_DEV not defined"  >&2
        echo ".......: Using $PARSEME_SHAREDTASK_DATA_DEV"  >&2
    else
        echo "ERROR: Environment variable PARSEME_SHAREDTASK_DATA_DEV not defined"  >&2
        echo ".....: Please explicitly set this variable with the path"  >&2
        echo ".....: to the parseme-sharedtask-data-dev repository"  >&2
        exit 1
    fi
fi

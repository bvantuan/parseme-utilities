__THIS_LIB_PATH="$(dirname "${BASH_SOURCE[0]}")"


if ! test "${PARSEME_RELEASE_DATA_DEV+set}"; then
    __psdd="$__THIS_LIB_PATH/../../release-data-dev/1.3"
    #echo $__psdd
    if test -d "$__psdd"; then
        export PARSEME_RELEASE_DATA_DEV="$(cd "$__psdd"; pwd)"
        echo "WARNING: Environment variable PARSEME_RELEASE_DATA_DEV not defined"  >&2
        echo ".......: Using $PARSEME_RELEASE_DATA_DEV"  >&2
    else
        echo "ERROR: Environment variable PARSEME_RELEASE_DATA_DEV not defined"  >&2
        echo ".....: Please explicitly set this variable with the path"  >&2
        echo ".....: to the parseme-release-data-dev repository"  >&2
        exit 1
    fi
fi

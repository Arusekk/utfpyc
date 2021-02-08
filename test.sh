#!/bin/sh

set -e

# test the script on itself
./utfpyc.py -f utfpyc.py utfpyc.pyc
# run the result again
python3 utfpyc.pyc -f utfpyc.py utfpyc2.pyc
cmp utfpyc.pyc utfpyc2.pyc

for script in test/*.py; do
    # compare the original script and self-compiled script results on tests
    ./utfpyc.py "$script" "${script%.py}.pyc"
    python3 utfpyc.pyc "$script" "${script%.py}.pyc.pyc"
    cmp "${script%.py}.pyc" "${script%.py}.pyc.pyc"
    # run the test
    python3 "$script" >"$script.out"
    python3 "${script%.py}.pyc" >"${script%.py}.pyc.out"
    cmp "$script.out" "${script%.py}.pyc.out"
done


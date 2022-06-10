#!/bin/sh

files="src/bluecat_bam/*.py tests/*.py samples/*.py *.py"
#echo "To update files with black, use:"
#echo "black $files"
#( set -x
#black --check --diff $files
echo "================= black ================"
black $files || exit 1
echo "================= pylint ================"
pylint $files || exit 1
echo "================= flake8 ================"
flake8 $files || exit 1
echo "================= bandit ================"
bandit -s B101 -r $files || exit 1
echo "================= pytest ================"
pytest || exit 1
#)
echo "done"

#!/bin/sh

files="src/bluecat_bam/*.py tests/*.py samples/*.py *.py"
#echo "To update files with black, use:"
#echo "black $files"
#( set -x
#black --check --diff $files
echo "================= black ================"
black $files || exit 1
echo "================= pylint ================"
pylint $files
echo "================= flake8 ================"
flake8 $files
echo "================= bandit ================"
bandit $files
echo "================= pytest ================"
pytest
#)

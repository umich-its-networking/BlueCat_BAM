#!/bin/sh

files="src/bluecat_bam/*.py tests/*.py samples/*.py *.py"
echo "To update files with black, use:"
echo "black $files"
( set -x
black --check --diff $files
pylint $files
flake8 $files
bandit $files
pytest
)

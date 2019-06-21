"""test_api_main"""  # pylint requires docstring
import pytest

from bluecat_bam.cli import main


def test_main_no_args():
    """test"""
    with pytest.raises(SystemExit):
        main()

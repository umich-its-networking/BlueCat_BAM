"""setup"""  # docstring required by pylint
import os
from setuptools import setup, find_packages

name = "bluecat_bam"

version_file_path = os.path.join(os.path.dirname(__file__), "src", name, "VERSION")
with open(version_file_path) as version_file:
    _version = version_file.read().strip()

setup(
    name=name,
    version=_version,
    package_dir={"": "src"},
    packages=find_packages("src"),
    include_package_data=True,
    zip_safe=False,
    setup_requires=["pytest-runner"],
    tests_require=["pytest", "pytest_mock", "requests_mock"],
    install_requires=["requests==2.21.0"],
    entry_points={"console_scripts": ["bam=bluecat_bam.cli:main"]},
)

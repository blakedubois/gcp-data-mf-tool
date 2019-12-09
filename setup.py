import codecs
import os
import sys

from setuptools import find_packages, setup


def read(rel_path):
    here = os.path.abspath(os.path.dirname(__file__))
    # intentionally *not* adding an encoding option to open, See:
    #   https://github.com/pypa/virtualenv/issues/201#issuecomment-3145690
    with codecs.open(os.path.join(here, rel_path), 'r') as fp:
        return fp.read()


def get_version(rel_path):
    for line in read(rel_path).splitlines():
        if line.startswith('__version__'):
            # __version__ = "0.9"
            delim = '"' if '"' in line else "'"
            return line.split(delim)[1]
    else:
        raise RuntimeError("Unable to find version string.")


with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="mfutil",
    version=get_version("mf/__init__.py"),
    description="The command line tool for manifest generation",
    long_description=long_description,
    license='MIT',
    author='Just the developers',
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=find_packages(exclude=['tests']),
    install_requires=[
        'google-cloud-storage==1.23.0',
        'jsonschema',
        'python-slugify'
    ],
    entry_points={
        "console_scripts": [
            "mfutil=mf.cli:main"
        ],
    },
    zip_safe=False,
    python_requires='>=3.6'
)

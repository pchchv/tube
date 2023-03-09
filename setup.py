#!/usr/bin/env python
"""This module contains setup instructions for utube."""
import os
import codecs
from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))

with codecs.open(os.path.join(here, "README.md"), encoding="utf-8") as fh:
    long_description = "\n" + fh.read()

with open(os.path.join(here, "utube", "version.py")) as fp:
    exec(fp.read())

setup(
    name="utube",
    version=__version__,  # noqa: F821
    author="Evgenii Pochechuev",
    author_email="ipchchv@gmail.com",
    packages=["utube", ],
    package_data={"": ["LICENSE"], },
    url="https://github.com/pchchv/utube",
    license="Apache-2.0 license",
    entry_points={
        "console_scripts": [
            "utube = utube.cli:main"], },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python",
        "Topic :: Internet",
        "Topic :: Multimedia :: Video",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Terminals",
        "Topic :: Utilities",
    ],
    description=("Python 3 library for downloading YouTube Videos."),
    include_package_data=True,
    long_description_content_type="text/markdown",
    long_description=long_description,
    zip_safe=True,
    python_requires=">=3.6",
    project_urls={
        "Bug Reports": "https://github.com/pchchv/utube/issues",
        "Read the Docs": "https://github.com/pchchv/utube/docs",
    },
    keywords=["youtube", "download", "video", "stream",],
)

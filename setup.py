#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2017 Adrian Perez <aperez@igalia.com>
#
# Distributed under terms of the GPLv3 license.

from setuptools import setup, find_packages
from os import path

def distrib_file(*relpath):
    try:
        return open(path.join(path.dirname(__file__), *relpath), "rU", \
                encoding="utf-8")
    except IOError:
        class DummyFile(object):
            read = lambda self: ""
        return DummyFile()


def get_version():
    for line in distrib_file("synpurge", "__init__.py"):
        if line.startswith("__version__"):
            line = line.split()
            if line[0] == "__version__":
                return line[2].strip()
    return None


def get_readme():
    return distrib_file("README.rst").read()


setup(
    name="synpurge",
    version=get_version(),
    description="Purges Matrix room history room using the HTTP API",
    long_description=get_readme(),
    author="Adrian Perez de Castro",
    author_email="aperez@igalia.com",
    url="https://github.com/aperezdc/synpurge",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "synpurge = synpurge.cli:cmd",
        ],
    },
    install_requires=[
        "requests>=2.10.0",
        "attrs>=16.0.0",
        "Delorean>=0.6.0",
        "argh>=0.25",
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.4",
        "Topic :: Communications :: Chat",
        "Topic :: Utilities",
    ])

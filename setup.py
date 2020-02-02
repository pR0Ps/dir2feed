#!/usr/bin/env python

from setuptools import setup

setup(
    name="dir2feed",
    version="0.0.1",
    description="Generates an Atom feed based on a directory structure",
    url="https://github.com/pR0Ps/dir2feed",
    license="MPLv2",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
    packages=["dir2feed"],
    install_requires=["feedgen>=0.9.0,<1.0.0"],
    entry_points={"console_scripts": ["dir2feed=dir2feed.__main__:main"]},
)

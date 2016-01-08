#!/usr/bin/python

import os

from distutils.core import setup, Distribution
from application import __info__ as package_info

Distribution.install_requires = None  # make distutils ignore this option that is used by setuptools when invoked from pip install


def find_packages(root):
    return [directory.replace(os.path.sep, '.') for directory, sub_dirs, files in os.walk(root) if '__init__.py' in files]


setup(
    name=package_info.__project__,
    version=package_info.__version__,

    description=package_info.__summary__,
    long_description=open('README').read(),
    license=package_info.__license__,
    url=package_info.__webpage__,

    author=package_info.__author__,
    author_email=package_info.__email__,

    platforms=["Platform Independent"],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules"
    ],

    packages=find_packages('application'),
    provides=['application'],
    requires=['zope.interface'],
    install_requires=['zope.interface']
)

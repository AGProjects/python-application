#!/usr/bin/python

from distutils.core import setup, Extension
from application import __version__

setup(name         = "python-application",
      version      = __version__,
      author       = "Dan Pascu",
      author_email = "dan@ag-projects.com",
      url          = "http://ag-projects.com/",
      download_url = "http://cheeseshop.python.org/pypi/python-application/%s" % __version__,
      description  = "Basic buliding blocks for python applications",
      long_description = open('README', 'r').read(),
      license      = "LGPL",
      platforms    = ["Platform Independent"],
      classifiers  = [
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules"
      ],
      packages     = ['application', 'application.configuration', 'application.debug', 'application.python'])

#!/usr/bin/python

from distutils.core import setup, Extension
from application import __version__

intro = """\
This package is a collection of modules that are useful when building python
applications. Their purpose is to eliminate the need to divert resources into
implementing the small tasks that every application needs to do in order to
run succesfully and focus on the application logic itself.

The modules that the application package provides are:

1. process       - UNIX process and signal management.
2. python        - python utility classes and functions.
3. configuration - a simple interface to handle configuration files.
4. log           - an extensible system logger for console and syslog.
5. debug         - memory troubleshooting and execution timing.
6. util          - miscelaneous application related utilities.
"""

setup(name         = "python-application",
      version      = __version__,
      author       = "Dan Pascu",
      author_email = "dan@ag-projects.com",
      url          = "http://ag-projects.com/",
      download_url = "http://cheeseshop.python.org/pypi/python-application/%s" % __version__,
      description  = "Basic buliding blocks for python applications",
      long_description = intro,
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

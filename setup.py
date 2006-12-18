#!/usr/bin/python

import sys
from distutils.core import setup, Extension


setup(name         = "python-application",
      version      = "1.0.0",
      description  = "Basic buliding blocks for python applications",
      author       = "Dan Pascu",
      author_email = "dan@ag-projects.com",
      license      = "GPL",
      packages     = ['application', 'application.configuration',
                      'application.debug'])

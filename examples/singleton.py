#!/usr/bin/python

from application.python.util import Singleton

class Unique(object):
    """This class has only one instance"""
    __metaclass__ = Singleton

o1 = Unique()
o2 = Unique()

print "o1 is o2:",  o1 is o2


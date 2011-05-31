#!/usr/bin/python

from application.python.types import Singleton

class Unique(object):
    """This class has only one instance"""
    __metaclass__ = Singleton

class CustomUnique(object):
    """This class has one instance per __init__ arguments combination"""
    __metaclass__ = Singleton

    def __init__(self, name='default', value=1):
        self.name = name
        self.value = value


o1 = Unique()
o2 = Unique()

print "o1 is o2 (expect True):", o1 is o2

co1 = CustomUnique()
co2 = CustomUnique()
co3 = CustomUnique(name='myname')
co4 = CustomUnique(name='myname')
co5 = CustomUnique(name='myname', value=2)
co6 = CustomUnique(name='myothername')

print "co1 is co2 (expect True):", co1 is co2
print "co3 is co4 (expect True):", co3 is co4
print "co1 is co3 (expect False):", co1 is co3
print "co4 is co5 (expect False):", co4 is co5
print "co4 is co6 (expect False):", co4 is co6


# Copyright (C) 2004-2006 Dan Pascu <dan@ag-projects.com>
#

"""A few useful variables, functions and classes"""


__all__ = ['thisHostIP', 'unlink', 'Singleton', 'Null']

##
## System variables
##

import socket
try:    thisHostIP = socket.gethostbyname(socket.getfqdn())
except: thisHostIP = None
del socket

##
## Functions
##

def unlink(path):
    """Remove a file ignoring errors"""
    from os import unlink as os_unlink
    try:    os_unlink(path)
    except: pass


##
## Classes
##

class Singleton(type):
    """Metaclass for making singletons"""
    def __init__(cls, name, bases, dic):
        super(Singleton, cls).__init__(name, bases, dic)
        cls.instance = None
    def __call__(cls, *args, **kw):
        if cls.instance is None:
            cls.instance = super(Singleton, cls).__call__(*args, **kw)
        return cls.instance


class Null(object):
    """Instances of this class always and reliably "do nothing" :P"""
    def __init__(self, *args, **kwargs): pass
    def __call__(self, *args, **kwargs): return self
    def __repr__(self): return self.__class__.__name__
    def __nonzero__(self): return 0
    def __eq__(self, other): return isinstance(other, self.__class__)
    def __ne__(self, other): return not isinstance(other, self.__class__)
    def __getattr__(self, name): return self
    def __setattr__(self, name, value): return self
    def __delattr__(self, name): return self
    __str__ = __repr__



# Copyright (C) 2006-2007 Dan Pascu. See LICENSE for details.
#

"""Miscelaneous utility functions and classes"""


__all__ = ['Singleton', 'Null']


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
    """Instances of this class always and reliably "do nothing"."""
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



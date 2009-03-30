# Copyright (C) 2006-2009 Dan Pascu. See LICENSE for details.
#

"""Miscellaneous utility functions and classes"""

__all__ = ['Singleton', 'Null']

from new import instancemethod
from application.python.decorator import preserve_signature

class Singleton(type):
    """Metaclass for making singletons"""
    def __init__(cls, name, bases, dic):
        from types import UnboundMethodType
        if type(cls.__init__) is UnboundMethodType:
            initializer = cls.__init__
        elif type(cls.__new__) is UnboundMethodType:
            initializer = cls.__new__
        else:
            def initializer(self, *args, **kw): pass
        @preserve_signature(initializer)
        def instance_creator(cls, *args, **kwargs):
            key = (args, tuple(sorted(kwargs.iteritems())))
            try:
                hash(key)
            except TypeError:
                raise TypeError("cannot have singletons for classes with unhashable arguments")
            if key not in cls._instances:
                cls._instances[key] = super(Singleton, cls).__call__(*args, **kwargs)
            return cls._instances[key]
        super(Singleton, cls).__init__(name, bases, dic)
        cls._instances = {}
        cls._instance_creator = instancemethod(instance_creator, cls, type(cls))
    def __call__(cls, *args, **kw):
        return cls._instance_creator(*args, **kw)

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


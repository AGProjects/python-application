# Copyright (C) 2009 AG Projects. See LICENSE for details.
#

"""Miscellaneous utility descriptors"""

__all__ = ['ThreadLocal']

from threading import local

class ThreadLocal(object):
    """Descriptor that allows objects to have thread specific attributes"""
    thread_local = local()
    def __init__(self, type, *args, **kw):
        self.type = type
        self.args = args
        self.kw = kw
    def __get__(self, obj, objtype):
        if obj is None:
            return self
        try:
            return self.thread_local.__dict__[(id(obj), id(self))]
        except KeyError:
            instance = self.type(*self.args, **self.kw)
            self.thread_local.__dict__[(id(obj), id(self))] = instance
            return instance
    def __set__(self, obj, value):
        self.thread_local.__dict__[(id(obj), id(self))] = value
    def __delete__(self, obj):
        raise AttributeError("attribute cannot be deleted")


# Copyright (C) 2009-2012 AG Projects. See LICENSE for details.
#

"""Miscellaneous utility descriptors"""

from threading import local
from application.python.weakref import weakobjectid, weakobjectmap


__all__ = ['ThreadLocal', 'WriteOnceAttribute', 'classproperty', 'isdescriptor']


class discarder(object):
    def __init__(self, mapping):
        self.mapping = mapping

    def __call__(self, wr):
        del self.mapping[wr.id]


class ThreadLocal(object):
    """Descriptor that allows objects to have thread specific attributes"""

    def __init__(self, type, *args, **kw):
        self.thread_local = local()
        self.type = type
        self.args = args
        self.kw = kw

    def __get__(self, obj, owner):
        if obj is None:
            return self
        try:
            return self.thread_local.__dict__[id(obj)]
        except KeyError:
            self.thread_local.__dict__[weakobjectid(obj, discarder(self.thread_local.__dict__))] = instance = self.type(*self.args, **self.kw)
            return instance

    def __set__(self, obj, value):
        self.thread_local.__dict__[weakobjectid(obj, discarder(self.thread_local.__dict__))] = value

    def __delete__(self, obj):
        raise AttributeError("attribute cannot be deleted")


class WriteOnceAttribute(object):
    """
    Descriptor that allows objects to have write once attributes.

    It should be noted that the descriptor only enforces this when directly
    accessing the object's attribute. It is still possible to modify/delete
    such an attribute by messing around with the descriptor's internal data.
    """

    def __init__(self):
        self.values = weakobjectmap()

    def __get__(self, obj, type):
        if obj is None:
            return self
        try:
            return self.values[obj]
        except KeyError:
            raise AttributeError("attribute is not set")

    def __set__(self, obj, value):
        if obj in self.values:
            raise AttributeError("attribute is read-only")
        self.values[obj] = value

    def __delete__(self, obj):
        raise AttributeError("attribute cannot be deleted")


def classproperty(function):
    """A class level read only property"""
    class Descriptor(object):
        def __get__(self, obj, type):
            return function(type)

        def __set__(self, obj, value):
            raise AttributeError("read-only attribute cannot be set")

        def __delete__(self, obj):
            raise AttributeError("read-only attribute cannot be deleted")
    return Descriptor()


def isdescriptor(object):
    """Test if `object' is a descriptor"""
    return bool({'__get__', '__set__', '__delete__'}.intersection(dir(object)))



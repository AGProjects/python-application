# Copyright (C) 2009-2011 AG Projects. See LICENSE for details.
#

"""Miscellaneous utility descriptors"""

__all__ = ['ThreadLocal', 'WriteOnceAttribute', 'classproperty', 'isdescriptor']

import weakref
from threading import local


class discarder(object):
    def __init__(self, mapping):
        self.mapping = mapping
    def __call__(self, wr):
        del self.mapping[wr.id]

class objectref(weakref.ref):
    __slots__ = ("id",)
    def __init__(self, object, discard_callback):
        super(objectref, self).__init__(object, discard_callback)
        self.id = id(object)

class objectid(long):
    def __new__(cls, object, discard_callback):
        instance = long.__new__(cls, id(object))
        instance.ref = objectref(object, discard_callback)
        return instance


class ThreadLocal(object):
    """Descriptor that allows objects to have thread specific attributes"""
    def __init__(self, type, *args, **kw):
        self.thread_local = local()
        self.type = type
        self.args = args
        self.kw = kw
    def __get__(self, obj, objtype):
        if obj is None:
            return self
        try:
            return self.thread_local.__dict__[id(obj)]
        except KeyError:
            self.thread_local.__dict__[objectid(obj, discarder(self.thread_local.__dict__))] = instance = self.type(*self.args, **self.kw)
            return instance
    def __set__(self, obj, value):
        self.thread_local.__dict__[objectid(obj, discarder(self.thread_local.__dict__))] = value
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
        self.values = {}
    def __get__(self, obj, type):
        if obj is None:
            return self
        try:
            return self.values[id(obj)][0]
        except KeyError:
            raise AttributeError("attribute is not set")
    def __set__(self, obj, value):
        obj_id = id(obj)
        if obj_id in self.values:
            raise AttributeError("attribute is read-only")
        self.values[obj_id] = (value, weakref.ref(obj, lambda weak_ref: self.values.pop(obj_id)))
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
    return bool(set(('__get__', '__set__', '__delete__')).intersection(dir(object)))



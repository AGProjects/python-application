# Copyright (C) 2009 AG Projects. See LICENSE for details.
#

"""Miscellaneous utility descriptors"""

__all__ = ['ThreadLocal']

import weakref
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
        obj_id = id(obj)
        self_id = id(self)
        try:
            return self.thread_local.__dict__[(obj_id, self_id)][0]
        except KeyError:
            instance = self.type(*self.args, **self.kw)
            thread_dict = self.thread_local.__dict__
            ref = weakref.ref(obj, lambda weak_ref: thread_dict.pop((obj_id, self_id)))
            thread_dict[(obj_id, self_id)] = (instance, ref)
            return instance
    def __set__(self, obj, value):
        obj_id = id(obj)
        self_id = id(self)
        thread_dict = self.thread_local.__dict__
        if (obj_id, self_id) in thread_dict:
            ref = thread_dict[(obj_id, self_id)][1]
        else:
            ref = weakref.ref(obj, lambda weak_ref: thread_dict.pop((obj_id, self_id)))
        thread_dict[(obj_id, self_id)] = (value, ref)
    def __delete__(self, obj):
        raise AttributeError("attribute cannot be deleted")


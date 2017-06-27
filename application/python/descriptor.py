
"""Miscellaneous utility descriptors"""

from threading import local
from application.python.weakref import weakobjectid, weakobjectmap


__all__ = 'ThreadLocal', 'WriteOnceAttribute', 'classproperty', 'isdescriptor'


# noinspection PyPep8Naming
class discarder(object):
    def __init__(self, mapping):
        self.mapping = mapping

    def __call__(self, wr):
        del self.mapping[wr.id]


class ThreadLocal(object):
    """Descriptor that allows objects to have thread specific attributes"""

    # noinspection PyShadowingBuiltins
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
        raise AttributeError('attribute cannot be deleted')


class WriteOnceAttribute(object):
    """
    Descriptor that allows objects to have write once attributes.

    It should be noted that the descriptor only enforces this when directly
    accessing the object's attribute. It is still possible to modify/delete
    such an attribute by messing around with the descriptor's internal data.
    """

    def __init__(self):
        self.values = weakobjectmap()

    def __get__(self, instance, owner):
        if instance is None:
            return self
        try:
            return self.values[instance]
        except KeyError:
            raise AttributeError('attribute is not set')

    def __set__(self, instance, value):
        if instance in self.values:
            raise AttributeError('attribute is read-only')
        self.values[instance] = value

    def __delete__(self, obj):
        raise AttributeError('attribute cannot be deleted')


def classproperty(func):
    """A class level read only property"""
    class Descriptor(object):
        def __get__(self, instance, owner):
            return func(owner)

        def __set__(self, instance, value):
            raise AttributeError('read-only attribute cannot be set')

        def __delete__(self, obj):
            raise AttributeError('read-only attribute cannot be deleted')
    return Descriptor()


# noinspection PyShadowingBuiltins
def isdescriptor(object):
    """Test if `object' is a descriptor"""
    return bool({'__get__', '__set__', '__delete__'}.intersection(dir(object)))

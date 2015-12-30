# Copyright (C) 2011-2012 Dan Pascu. See LICENSE for details.
#

from __future__ import absolute_import

import weakref

from collections import MutableMapping
from copy import deepcopy


__all__ = ["weakobjectmap"]


class objectref(weakref.ref):
    __slots__ = "id"

    def __init__(self, object, discard_callback):
        super(objectref, self).__init__(object, discard_callback)
        self.id = id(object)


class weakobjectid(long):
    def __new__(cls, object, discard_callback):
        instance = long.__new__(cls, id(object))
        instance.ref = objectref(object, discard_callback)
        return instance


class objectid(long):
    def __new__(cls, object):
        instance = long.__new__(cls, id(object))
        instance.object = object
        return instance


# The wekaobjectmap class offers the same functionality as WeakKeyDictionary
# from the standard python weakref module, with a few notable improvements:
#
#  - it works even with objects (keys) that are not hashable
#  - subclasses can implement __missing__ to define defaultdict like behavior
#  - it is faster as it directly subclasses dict instead of using a UserDict
#  - it is thread safe, as all it's operations are atomic, in the sense that
#    they are the dict's methods executing in C while being protected by the
#    GIL
#  - iterating it as well as the iterating methods (iterkeys, itervalues
#    and iteritems) are safe from changes to the mapping while iterating
#  - it provides a __repr__ implementation that makes it display similar
#    to a dict which provides an easy way to inspect it
#

class weakobjectmap(MutableMapping):
    """Mapping between objects and data, that keeps weak object references"""

    def __init__(self, *args, **kw):
        def remove(wr, selfref=weakref.ref(self)):
            myself = selfref()
            if myself is not None:
                del myself.__data__[wr.id]
        self.__data__ = {}
        self.__remove__ = remove
        self.update(*args, **kw)

    def __getitem__(self, key):
        try:
            return self.__data__[objectid(key)]
        except KeyError:
            raise KeyError(key)

    def __setitem__(self, key, value):
        self.__data__[weakobjectid(key, self.__remove__)] = value

    def __delitem__(self, key):
        try:
            del self.__data__[id(key)]
        except KeyError:
            raise KeyError(key)

    def __contains__(self, key):
        return id(key) in self.__data__

    def __iter__(self):
        return self.iterkeys()

    def __len__(self):
        return len(self.__data__)

    def __copy__(self):
        return self.__class__(self)

    def __deepcopy__(self, memo):
        return self.__class__((key, deepcopy(value, memo)) for key, value in self.iteritems())

    def __repr__(self):
        return "%s({%s})" % (self.__class__.__name__, ', '.join(('%r: %r' % (key, value) for key, value in self.iteritems())))

    @classmethod
    def fromkeys(cls, iterable, value=None):
        mapping = cls()
        for key in iterable:
            mapping[key] = value
        return mapping

    def clear(self):
        self.__data__.clear()

    def copy(self):
        return self.__class__(self)

    def iterkeys(self):
        return (key for key in (key.ref() for key in self.__data__.keys()) if key is not None)

    def itervalues(self):
        return (value for key, value in ((key.ref(), value) for key, value in self.__data__.items()) if key is not None)

    def iteritems(self):
        return ((key, value) for key, value in ((key.ref(), value) for key, value in self.__data__.items()) if key is not None)

    def keys(self):
        return [key for key in (key.ref() for key in self.__data__.keys()) if key is not None]

    def values(self):
        return [value for key, value in ((key.ref(), value) for key, value in self.__data__.items()) if key is not None]

    def items(self):
        return [(key, value) for key, value in ((key.ref(), value) for key, value in self.__data__.items()) if key is not None]

    def has_key(self, key):
        return key in self

    def get(self, key, default=None):
        return self.__data__.get(id(key), default)

    def setdefault(self, key, default=None):
        return self.__data__.setdefault(weakobjectid(key, self.__remove__), default)

    def pop(self, key, *args):
        try:
            return self.__data__.pop(id(key), *args)
        except KeyError:
            raise KeyError(key)

    def popitem(self):
        while True:
            key, value = self.__data__.popitem()
            object = key.ref()
            if object is not None:
                return object, value



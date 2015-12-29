# Copyright (C) 2011-2012 Dan Pascu. See LICENSE for details.
#

from __future__ import absolute_import

import weakref
from collections import Mapping
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

class weakobjectmap(dict):
    """Mapping between objects and data, that keeps weak object references"""

    def __init__(self, *args, **kw):
        def remove(wr, selfref=weakref.ref(self)):
            myself = selfref()
            if myself is not None:
                dict.__delitem__(myself, wr.id)
        self.__remove__ = remove
        super(weakobjectmap, self).__init__()
        weakobjectmap.update(self, *args, **kw)

    def __getitem__(self, key):
        try:
            return super(weakobjectmap, self).__getitem__(objectid(key))
        except KeyError:
            raise KeyError(key)

    def __setitem__(self, key, value):
        super(weakobjectmap, self).__setitem__(weakobjectid(key, self.__remove__), value)

    def __delitem__(self, key):
        try:
            super(weakobjectmap, self).__delitem__(id(key))
        except KeyError:
            raise KeyError(key)

    def __contains__(self, key):
        return super(weakobjectmap, self).__contains__(id(key))

    def __iter__(self):
        return self.iterkeys()

    def __copy__(self):
        return self.__class__(self)

    def __deepcopy__(self, memo):
        return self.__class__((key, deepcopy(value, memo)) for key, value in self.iteritems())

    def __repr__(self):
        return "%s({%s})" % (self.__class__.__name__, ', '.join(('%r: %r' % (key, value) for key, value in self.iteritems())))

    def copy(self):
        return self.__copy__()

    def iterkeys(self):
        return (key for key in (key.ref() for key in super(weakobjectmap, self).keys()) if key is not None)

    def itervalues(self):
        return (value for key, value in ((key.ref(), value) for key, value in super(weakobjectmap, self).items()) if key is not None)

    def iteritems(self):
        return ((key, value) for key, value in ((key.ref(), value) for key, value in super(weakobjectmap, self).items()) if key is not None)

    def keys(self):
        return [key for key in (key.ref() for key in super(weakobjectmap, self).keys()) if key is not None]

    def values(self):
        return [value for key, value in ((key.ref(), value) for key, value in super(weakobjectmap, self).items()) if key is not None]

    def items(self):
        return [(key, value) for key, value in ((key.ref(), value) for key, value in super(weakobjectmap, self).items()) if key is not None]

    def has_key(self, key):
        return key in self

    def get(self, key, default=None):
        return super(weakobjectmap, self).get(id(key), default)

    def setdefault(self, key, default=None):
        return super(weakobjectmap, self).setdefault(weakobjectid(key, self.__remove__), default)

    def pop(self, key, *args):
        try:
            return super(weakobjectmap, self).pop(id(key), *args)
        except KeyError:
            raise KeyError(key)

    def popitem(self):
        while True:
            key, value = super(weakobjectmap, self).popitem()
            object = key.ref()
            if object is not None:
                return object, value

    def update(self, *args, **kw):
        if len(args) > 1:
            raise TypeError("expected at most 1 positional argument (got %d)" % len(args))
        other = args[0] if args else ()
        if isinstance(other, Mapping):
            for key in other:
                self[key] = other[key]
        elif hasattr(other, "keys"):
            for key in other.keys():
                self[key] = other[key]
        else:
            for key, value in other:
                self[key] = value
        for key, value in kw.iteritems():
            self[key] = value



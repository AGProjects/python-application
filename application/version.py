# Copyright (C) 2009-2016 Dan Pascu. See LICENSE for details.
#

"""Describe and handle version numbers for applications, modules and packages"""

import re


__all__ = ['Version']


class Version(str):
    """A major.minor.micro[extraversion] version string that is comparable"""

    def __new__(cls, major, minor, micro, extraversion=None):
        if major is minor is micro is extraversion is None:
            instance = str.__new__(cls, "undefined")
            instance._version_info = (None, None, None, None, None)
            return instance
        try:
            major, minor, micro = int(major), int(minor), int(micro)
        except (TypeError, ValueError):
            raise TypeError("major, minor and micro must be integer numbers")
        if extraversion is None:
            instance = str.__new__(cls, "%d.%d.%d" % (major, minor, micro))
            weight = 0
        elif isinstance(extraversion, (int, long)):
            instance = str.__new__(cls, "%d.%d.%d-%d" % (major, minor, micro, extraversion))
            weight = 0
        elif isinstance(extraversion, basestring):
            instance = str.__new__(cls, "%d.%d.%d%s" % (major, minor, micro, extraversion))
            match = re.match(r'^[-.]?(?P<name>(pre|rc|alpha|beta|))(?P<number>\d+)$', extraversion)
            if match:
                weight_map = {'alpha': -40, 'beta': -30, 'pre': -20, 'rc': -10, '': 0}
                weight = weight_map[match.group('name')]
                extraversion = int(match.group('number'))
            else:
                weight = 0
                extraversion = extraversion or None
        else:
            raise TypeError("extraversion must be a string, integer, long or None")
        instance._version_info = (major, minor, micro, weight, extraversion)
        return instance

    def __init__(self, *args, **kw):
        super(Version, self).__init__()

    @classmethod
    def parse(cls, value):
        if isinstance(value, Version):
            return value
        elif not isinstance(value, basestring):
            raise TypeError("value should be a string")
        if value == 'undefined':
            return cls(None, None, None)
        match = re.match(r'^(?P<major>\d+)(\.(?P<minor>\d+))?(\.(?P<micro>\d+))?(?P<extraversion>.*)$', value)
        if not match:
            raise ValueError("not a recognized version string")
        return cls(**match.groupdict(0))

    @property
    def major(self):
        return self._version_info[0]

    @property
    def minor(self):
        return self._version_info[1]

    @property
    def micro(self):
        return self._version_info[2]

    @property
    def extraversion(self):
        return self._version_info[4]

    def __repr__(self):
        major, minor, micro, weight, extraversion = self._version_info
        if weight is not None and weight < 0:
            weight_map = {-10: 'rc', -20: 'pre', -30: 'beta', -40: 'alpha'}
            extraversion = "%s%d" % (weight_map[weight], extraversion)
        return "%s(major=%r, minor=%r, micro=%r, extraversion=%r)" % (self.__class__.__name__, major, minor, micro, extraversion)

    def __cmp__(self, other):
        if isinstance(other, Version):
            return cmp(self._version_info, other._version_info)
        elif isinstance(other, basestring):
            return cmp(str(self), other)
        else:
            return NotImplemented

    def __le__(self, other):
        return self.__cmp__(other) <= 0

    def __lt__(self, other):
        return self.__cmp__(other) < 0

    def __ge__(self, other):
        return self.__cmp__(other) >= 0

    def __gt__(self, other):
        return self.__cmp__(other) > 0

    def __eq__(self, other):
        return self.__cmp__(other) == 0

    def __ne__(self, other):
        return self.__cmp__(other) != 0


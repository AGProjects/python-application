# Copyright (C) 2006-2011 Dan Pascu. See LICENSE for details.
#

"""Miscellaneous utility functions and classes. This module is deprecated and will be removed in 1.3.0"""

__all__ = ['Singleton', 'Null', 'NullType']

import sys

class FakeUtil(object):
    def __init__(self, module):
        self.__module = module

    def __getattribute__(self, name):
        value = object.__getattribute__(self, '_FakeUtil__module').__getattribute__(name)
        if name == 'Singleton':
            import warnings
            warnings.warn("importing Singleton from application.pyhton.util has been deprecated and will be removed in version 1.3.0. Singleton has been moved to application.python.types", DeprecationWarning)
        elif name == 'NullTypeMeta':
            import warnings
            warnings.warn("importing NullTypeMeta from application.pyhton.util has been deprecated and will be removed in version 1.3.0. NullTypeMeta has been moved to application.python.types", DeprecationWarning)
        elif name == 'NullType':
            import warnings
            warnings.warn("importing NullType from application.pyhton.util has been deprecated and will be removed in version 1.3.0. NullType has been moved to application.python.types", DeprecationWarning)
        elif name == 'Null':
            import warnings
            warnings.warn("importing Null from application.pyhton.util has been deprecated and will be removed in version 1.3.0. Null has been moved to application.python", DeprecationWarning)
        return value

fake_util = FakeUtil(sys.modules[__name__])
sys.modules[__name__] = fake_util

del FakeUtil, fake_util, sys

from application.python.types import Singleton, NullTypeMeta, NullType
from application.python import Null


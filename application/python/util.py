# Copyright (C) 2006-2011 Dan Pascu. See LICENSE for details.
#

"""Miscellaneous utility functions and classes. This module is deprecated and will be removed in 1.3.0"""

__all__ = ['Singleton', 'Null', 'NullType']

import sys

module_name  = __name__
parent_name, dot, module_basename = __name__.rpartition('.') # this works because we know for sure we have a parent

module = sys.modules[module_name]
parent = sys.modules[parent_name]

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

fake_util = FakeUtil(module)
sys.modules[module_name] = fake_util
setattr(parent, module_basename, fake_util)

del module_name, parent_name, module_basename, module, parent, fake_util, FakeUtil, dot, sys

from application.python.types import Singleton, NullTypeMeta, NullType
from application.python import Null


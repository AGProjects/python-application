
"""Python language extensions"""

from __builtin__ import min as minimum, max as maximum
from application.python.types import NullType


__all__ = 'Null', 'limit', 'subclasses'


Null = NullType()

try:
    negative_infinite = float('-infinity')
    positive_infinite = float('infinity')
except ValueError:
    negative_infinite = -1e300000
    positive_infinite = 1e300000


# noinspection PyShadowingBuiltins
def limit(value, min=negative_infinite, max=positive_infinite):
    """Limit a numeric value to the specified range"""
    return maximum(min, minimum(value, max))


def subclasses(cls):
    """Recursively find all the subclasses of a given class"""
    classes = cls.__subclasses__()
    for subclass in classes:
        for sub_subclass in subclass.__subclasses__():
            if sub_subclass not in classes:
                classes.append(sub_subclass)
    return classes


"""Python language extensions"""

from __builtin__ import min as minimum, max as maximum
from application.python.types import NullType
from collections import deque


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
    classes = deque(cls.__subclasses__())
    while classes:
        subclass = classes.popleft()
        classes.extend(subclass.__subclasses__())
        yield subclass

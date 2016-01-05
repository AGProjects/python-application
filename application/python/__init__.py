
"""Python language extensions"""

from application.python.types import NullType


__all__ = ['Null', 'limit']


Null = NullType()

try:
    negative_infinite = float('-infinity')
    positive_infinite = float('infinity')
except ValueError:
    negative_infinite = -1e300000
    positive_infinite = 1e300000


def limit(value, min=negative_infinite, max=positive_infinite):
    """Limit a numeric value to the specified range"""
    from __builtin__ import min as minimum, max as maximum
    return maximum(min, minimum(value, max))


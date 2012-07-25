# Copyright (C) 2006-2012 Dan Pascu. See LICENSE for details.
#

"""Measure code execution time for benchmarking and profiling purposes.

Usage:

from application.debug.timing import timer

count = 10000
t = timer(count)
for x in xrange(count):
    ...
t.end(msg="executing loop type 1")

"""

__all__ = ["timer"]

from time import time


class timer(object):
    def __init__(self, count):
        self.count = count
        self.start = time()
    def end(self, msg=None, duration=True, rate=True):
        _duration = time() - self.start
        _rate = self.count/_duration
        if duration:
            format = "time = %(_duration)5.2f sec"
        else:
            format = ""
        if rate:
            format += "; rate = %(_rate)d requests/sec"
        if msg is not None:
            format += "; %(msg)s"
        print format % locals()


#!/usr/bin/python

"""Example of using the debug facilities of python-application"""

# Timing code execution

from application.debug.timing import timer

s1 = 'abcdef'
s2 = 'ghijkl'
s3 = 'mnopqr'

print ""
print "Timing different methods of adding strings"
print "------------------------------------------"
print ""

# the loop count can be explicitly specified, but it's easier to let the
# timer automatically detect the loop count that will keep the total runtime
# per loop between 0.2 and 2 seconds (recommended)

with timer('adding strings with +', loops=1000000):
    sa = s1 + s2 + s3

with timer('adding strings using %'):
    sb = '%s%s%s' % (s1, s2, s3)

with timer('adding strings using str.format'):
    sc = '{}{}{}'.format(s1, s2, s3)

with timer("adding strings using ''.join()"):
    sd = ''.join((s1, s2, s3))


# Debugging memory leaks

class C1(object):
    pass


class C2(object):
    def __del__(self):
        pass

from application.debug.memory import *

print ""
print "Debugging memory leaks"
print "----------------------"
print ""

a = C1()
del a

print "This will reveal no memory references"
memory_dump()

a = C1()
b = C1()
a.b = b
b.a = a
del a, b

print "\n\nThis will reveal a collectable circular reference"
memory_dump()

a = C2()
b = C2()
a.b = b
b.a = a
del a, b

print "\n\nThis will reveal an uncollectable circular reference (mem leak)"
memory_dump()


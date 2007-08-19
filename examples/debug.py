#!/usr/bin/python

"""Example of using the debug facilities of python-application"""

# Timing code execution

from application.debug.timing import timer
count = 1000000
s1 = 'abcdef'
s2 = 'ghijkl'
s3 = 'mnopqr'

print ""
print "Timing different methods of adding strings"
print "------------------------------------------"
print ""

t = timer(count)
for x in xrange(count):
    s = s1 + s2 + s3
t.end(rate=True, msg="Adding strings using +")

t = timer(count)
for x in xrange(count):
    s = "%s%s%s" % (s1, s2, s3)
t.end(rate=True, msg="Adding strings using %")

t = timer(count)
for x in xrange(count):
    s = ''.join((s1, s2, s3))
t.end(rate=True, msg="Adding strings using ''.join()")


# Debugging memory leaks

class C1:
    pass

class C2:
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


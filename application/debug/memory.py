# Copyright (C) 2006-2010 Dan Pascu. See LICENSE for details.
#

"""Memory debugging helper.

Using this module:

1. at the beginning of your program import this module...

     from application.debug.memory import *

2. call memory_dump() later, when you want to check the memory leaks

Note: when debugging for memory leaks is enabled by the inclusion of
      this code, the garbage collector will be unable to properly free
      circular references and they will show up in the garbage objects
      list (this will make the application constantly grow). However
      if this code is not loaded, the garbage collector will properly
      detect and free the objects with circular references and the
      size of the application will remain constant even in the
      presence of circular references.
"""

__all__ = ['memory_dump']

import gc
import types
from collections import deque


class Node(object):
    def __init__(self, object):
        self.object = object
        self.successors = None
        self.visitable_successors = None


class Cycle(tuple):
    def __init__(self, *args, **kwargs):
        tuple.__init__(self)
        self.collectable = all(not hasattr(obj, '__del__') for obj in self)

    def __eq__(self, other):
        if len(self) != len(other):
            return False
        for i, obj in enumerate(other):
            if obj is self[0]:
                if tuple.__eq__(self, (other[i:] + other[:i])):
                    return True
        else:
            return len(self) == 0

    def __hash__(self):
        return sum(id(node) for node in self)

    def __repr__(self):
        return '%s%s' % (self.__class__.__name__, tuple.__repr__(self))

    def __str__(self):
        index = max_priority = 0
        for i, obj in enumerate(self):
            if obj is getattr(self[i-1], '__dict__', None):
                continue
            if isinstance(obj, types.MethodType):
                priority = 0
            elif isinstance(obj, types.FunctionType):
                priority = 2
            elif type(obj).__module__ in ('__builtin__', 'builtins'):
                priority = 1
            elif isinstance(obj, (tuple, list, dict, set, frozenset, str, unicode)):
                priority = 3
            else:
                priority = 4
            if priority > max_priority:
                index, max_priority = i, priority
        cycle = deque(self[index:] + self[:index])

        string = ''
        firstobj = cycle[0] if cycle else None
        while cycle:
            obj = cycle.popleft()
            string += repr(obj)
            if cycle and cycle[0] is getattr(obj, '__dict__', None):
                d = cycle.popleft()
                try:
                    if cycle:
                        string += ' .%s' % (key for key, value in d.iteritems() if value is cycle[0]).next()
                    else:
                        string += ' .%s' % (key for key, value in d.iteritems() if value is firstobj).next()
                except StopIteration:
                    string += ' .__dict__ -> %s' % repr(d)
            string += ' -> '
        string += repr(firstobj)

        return string


def memory_dump(show_cycles=True, show_objects=False):
    print "\nGARBAGE:"
    gc.collect()
    garbage = gc.garbage[:]

    if show_cycles:
        nodes = dict((id(obj), Node(obj)) for obj in garbage)
        for obj in garbage:
            nodes[id(obj)].successors = tuple(nodes[id(s)] for s in gc.get_referents(obj) if id(s) in nodes)
            nodes[id(obj)].visitable_successors = deque(nodes[id(obj)].successors)

        cycles = set()
        remaining_nodes = nodes.copy()
        while remaining_nodes:
            path = [remaining_nodes.itervalues().next()]
            while path:
                node = path[-1]
                remaining_nodes.pop(id(node.object), None)
                if node.visitable_successors:
                    succ = node.visitable_successors.pop()
                    if succ in path:
                        cycles.add(Cycle(n.object for n in path[path.index(succ):]))
                    else:
                        path.append(succ)
                else:
                    node.visitable_successors = deque(node.successors)
                    path.pop(-1)

        for node in nodes.itervalues():
            node.successors = node.visitable_successors = None

        print "\nCOLLECTABLE CYCLES:"
        for cycle in (c for c in cycles if c.collectable):
            print cycle

        print "\nUNCOLLECTABLE CYCLES:"
        for cycle in (c for c in cycles if not c.collectable):
            print cycle

    if show_objects:
        try:
            import fcntl, struct, sys, termios
            console_width = struct.unpack('HHHH', fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ, struct.pack('HHHH', 0, 0, 0, 0)))[1]
        except:
            console_width = 80

        print "\nGARBAGE OBJECTS:"
        for x in garbage:
            s = str(x)
            if len(s) > console_width-2:
                s = s[:console_width-5] + '...'
            print "%s\n  %s" % (type(x), s)


gc.enable()
gc.collect() ## Ignore collectable garbage up to this point
gc.set_debug(gc.DEBUG_LEAK)



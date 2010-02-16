# Copyright (C) 2006-2007 Dan Pascu. See LICENSE for details.
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

import gc

def memory_dump():
    print "\nGARBAGE:"
    gc.collect()

    try:
        import fcntl, struct, sys, termios
        console_width = struct.unpack('HHHH', fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ, struct.pack('HHHH', 0, 0, 0, 0)))[1]
    except:
        console_width = 80

    print "\nGARBAGE OBJECTS:"
    for x in gc.garbage:
        s = str(x)
        if len(s) > console_width-2:
            s = s[:console_width-5] + '...'
        print "%s\n  %s" % (type(x), s)

gc.enable()
gc.collect() ## Ignore collectable garbage up to this point
gc.set_debug(gc.DEBUG_LEAK)


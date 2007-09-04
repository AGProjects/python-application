# Copyright (C) 2006-2007 Dan Pascu. See LICENSE for details.
#

"""Miscelaneous utilities"""

__all__ = ['default_host_ip', 'unlink']

## System variables

# The default IP address of this system. This is the IP address of the network
# interface that has the default route assigned to it, or in other words the
# IP address that will be used when making connections to the internet.
import socket
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('1.2.3.4', 56))
        default_host_ip = s.getsockname()[0]
    finally:
        s.close()
        del s
except socket.error:
    default_host_ip = None
del socket

## Functions

def unlink(path):
    """Remove a file ignoring errors"""
    from os import unlink as os_unlink
    try:    os_unlink(path)
    except: pass



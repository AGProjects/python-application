# Copyright (C) 2004-2007 Dan Pascu <dan@ag-projects.com>
#

"""Miscelaneous application related utilities"""

__all__ = ['thisHostIP', 'unlink']

## System variables

import socket
try:    thisHostIP = socket.gethostbyname(socket.getfqdn())
except: thisHostIP = None
del socket

## Functions

def unlink(path):
    """Remove a file ignoring errors"""
    from os import unlink as os_unlink
    try:    os_unlink(path)
    except: pass



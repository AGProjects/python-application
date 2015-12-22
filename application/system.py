# Copyright (C) 2006-2012 Dan Pascu. See LICENSE for details.
#

"""Interaction with the underlying operating system"""

__all__ = ['host', 'makedirs', 'unlink']

import errno
import os
import socket

from application.python.types import Singleton

## System properties and attributes

class HostProperties(object):
    """Host specific properties"""

    __metaclass__ = Singleton

    @staticmethod
    def outgoing_ip_for(destination):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect((destination, 1))
            return s.getsockname()[0]
        except socket.error:
            return None

    @property
    def default_ip(self):
        """
        The default IP address of this system. This is the IP address of the
        network interface that has the default route assigned to it or in other
        words the IP address that will be used when making connections to the
        internet.
        """
        return self.outgoing_ip_for('1.2.3.4')

    @property
    def name(self):
        return socket.gethostname()

    @property
    def fqdn(self):
        return socket.getfqdn()

    @property
    def domain(self):
        return socket.getfqdn()[len(socket.gethostname())+1:] or None

    @property
    def aliases(self):
        hostname = socket.gethostname()
        aliases = socket.gethostbyaddr(hostname)[1]
        if hostname in aliases:
            aliases.remove(hostname)
        return aliases

host = HostProperties()


## Functions

def makedirs(path, mode=0777):
    """Create a directory recursively and ignore error if it already exists"""
    try:
        os.makedirs(path, mode)
    except OSError, e:
        if e.errno==errno.EEXIST and os.path.isdir(path) and os.access(path, os.R_OK | os.W_OK | os.X_OK):
            return
        raise

def unlink(path):
    """Remove a file ignoring errors"""
    try:
        os.unlink(path)
    except:
        pass


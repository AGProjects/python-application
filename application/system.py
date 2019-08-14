
"""Interaction with the operating system"""

import errno
import os
import socket

from application.python.types import Singleton


__all__ = 'host', 'makedirs', 'openfile', 'unlink', 'FileExistsError'


# System properties and attributes

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


# Functions

def makedirs(path, mode=0777):
    """Create a directory recursively and ignore error if it already exists"""
    try:
        os.makedirs(path, mode)
    except OSError, e:
        if e.errno == errno.EEXIST and os.path.isdir(path) and os.access(path, os.R_OK | os.W_OK | os.X_OK):
            return
        raise


class FileExistsError(IOError):
    pass


def openfile(path, mode='r', permissions=0666):
    if not isinstance(mode, str):
        raise TypeError('Invalid mode: {!r}'.format(mode))
    if not set(mode).issubset('rwxabt+'):
        raise ValueError('Invalid mode: {!r}'.format(mode))
    if len(set(mode).intersection('rwxa')) != 1 or mode.count('+') > 1:
        raise ValueError('Must have exactly one of create/read/write/append mode and at most one plus')
    if 'b' in mode and 't' in mode:
        raise ValueError('Cannot have both text and binary modes specified at the same time')

    write = append = False

    if 'w' in mode:
        write = True
        flags = os.O_CREAT | os.O_TRUNC
    elif 'x' in mode:
        write = True
        flags = os.O_CREAT | os.O_EXCL
    elif 'a' in mode:
        write = append = True
        flags = os.O_CREAT | os.O_APPEND
    else:
        flags = 0

    if '+' in mode:
        flags |= os.O_RDWR
    elif write:
        flags |= os.O_WRONLY
    else:
        flags |= os.O_RDONLY

    if 'b' in mode:
        flags |= getattr(os, 'O_BINARY', 0)
    flags |= getattr(os, 'O_NOINHERIT', 0) or getattr(os, 'O_CLOEXEC', 0)

    try:
        fd = os.open(path, flags, permissions)
    except OSError as e:
        if e.errno == errno.EEXIST:
            raise FileExistsError(*e.args)
        else:
            raise IOError(*e.args)

    if append:
        os.lseek(fd, 0, os.SEEK_END)

    return os.fdopen(fd, mode.replace('x', 'w'))


def unlink(path):
    """Remove a file ignoring OS errors"""
    try:
        os.unlink(path)
    except OSError:
        pass

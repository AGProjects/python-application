# Copyright (C) 2006-2007 Dan Pascu. See LICENSE for details.
#

"""Interaction with the underlying operating system"""

__all__ = ['host', 'default_host_ip', 'unlink']

## System variables

from application.python.util import Singleton

class HostProperties(object):
    """Host specific properties"""

    __metaclass__ = Singleton

    @property
    def default_ip(self):
        """
        The default IP address of this system. This is the IP address of the
        network interface that has the default route assigned to it or in other
        words the IP address that will be used when making connections to the
        internet.
        """
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('1.2.3.4', 56))
            return s.getsockname()[0]
        except socket.error:
            return None

    @property
    def name(self):
        import socket
        return socket.gethostname()

    @property
    def fqdn(self):
        import socket
        return socket.getfqdn()

    @property
    def domain(self):
        import socket
        return socket.getfqdn()[len(socket.gethostname())+1:] or None

    @property
    def aliases(self):
        import socket
        hostname = socket.gethostname()
        aliases = socket.gethostbyaddr(hostname)[1]
        if hostname in aliases:
            aliases.remove(hostname)
        return aliases

host = HostProperties()

del HostProperties, Singleton

# This attribute is here for backward compatibility reasons and will be removed
# soon. Do not use it, use host.default_ip instead which is dynamic and updates
# if the host IP changes (default_host_ip is frozen to the value computed when
# the module is loaded).
default_host_ip = host.default_ip


## Functions

def unlink(path):
    """Remove a file ignoring errors"""
    from os import unlink as os_unlink
    try:    os_unlink(path)
    except: pass



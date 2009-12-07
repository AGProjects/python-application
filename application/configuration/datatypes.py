# Copyright (C) 2006-2009 Dan Pascu. See LICENSE for details.
#

"""Basic data types to describe the type of the entries in the configuration file"""


__all__ = ['Boolean', 'LogLevel', 'StringList', 'IPAddress', 'Hostname', 'HostnameList',
           'NetworkRange', 'NetworkRangeList', 'NetworkAddress', 'EndpointAddress']

import socket
import re
import struct

from application import log


class Boolean(int):
    """A boolean validator that handles multiple boolean input keywords: yes/no, true/false, on/off, 1/0"""
    __states = {'1': True, 'yes': True, 'true': True, 'on': True, 1: True, True: True,
                '0': False, 'no': False, 'false': False, 'off': False, 0: False, False: False}
    def __new__(cls, value):
        try: 
            value + 0
        except:
            try: value + ''
            except: raise TypeError('value must be a string')
            else: val = value.lower()
        else:
            val = value # eventually we can accept any int value by using 'not not value'
        try:
            return Boolean.__states[val]
        except KeyError:
            raise ValueError, 'not a boolean: %s' % value


class LogLevel(int):
    """A log level indicated by a non-negative integer or one of the named attributes of log.level"""
    def __new__(cls, value):
        def constrain(value, min_value, max_value):
            return min(max(min_value, value), max_value)
        if isinstance(value, (int, long)):
            return log.NamedLevel(constrain(value, log.level.ALL, log.level.NONE))
        elif not isinstance(value, basestring):
            raise TypeError("value must be a string, int or long")
        log_level = value.upper()
        names = [attr.name for attr in log.level.__class__.__dict__.itervalues() if type(attr) is log.NamedLevel]
        if log_level in names:
            return getattr(log.level, log_level)
        try:
            return log.NamedLevel(constrain(int(log_level), log.level.ALL, log.level.NONE))
        except ValueError:
            raise ValueError("invalid log level: %s" % value)


class StringList(list):
    """A list of strings separated by commas"""
    def __new__(cls, value):
        if isinstance(value, (tuple, list)):
            return [str(x) for x in value]
        elif isinstance(value, basestring):
            if value.lower() in ('none', ''):
                return []
            return re.split(r'\s*,\s*', value)
        else:
            raise TypeError("value must be a string, list or tuple")


class IPAddress(str):
    """An IP address in quad dotted number notation"""
    def __new__(cls, value):
        try:
            socket.inet_aton(value)
        except socket.error:
            raise ValueError("invalid IP address: %r" % value)
        return str(value)


class Hostname(str):
    """A Hostname or an IP address. The keyword `any' stands for '0.0.0.0'"""
    def __new__(cls, value):
        if not isinstance(value, basestring):
            raise TypeError("value must be a string")
        if value.lower() == 'any':
            return '0.0.0.0'
        return str(value)


class HostnameList(list):
    """A list of hostnames separated by commas"""
    def __new__(cls, description):
        if isinstance(description, (list, tuple)):
            return [Hostname(x) for x in description]
        elif not isinstance(description, basestring):
            raise TypeError("value must be a string, list or tuple")
        if description.lower()=='none':
            return []
        lst = re.split(r'\s*,\s*', description)
        hosts = []
        for x in lst:
            try:
                host = Hostname(x)
            except ValueError, why:
                log.warn("%s (ignored)" % why)
            else:
                hosts.append(host)
        return hosts


class NetworkRange(tuple):
    """
    Describes a network address range in the form of a base_address and a
    network_mask which together define the network range in question.

    Input should be a string in the form of:
        - network/mask
        - ip_address
        - hostname
    in the latter two cases a mask of 32 is assumed.
    Except the hostname case, where a DNS name is present, in the other cases
    the address should be in quad dotted number notation. The special address
    0.0.0.0 can also be represented in the short format as 0.
    Mask is number between 0 and 32 (bits used by the network part of address)
    In addition to these, there are 2 special keywords that will be accepted
    as input: none which is equivalent to 0.0.0.0/32 (or its short form 0/32)
    and any which is equivalent to 0.0.0.0/0 (or its short form 0/0)

    Output is a tuple with (base_address, network_mask)

    On error ValueError is raised, or NameError for invalid hostnames.
    """
    def __new__(cls, description):
        if (isinstance(description, tuple) and len(description)==2 and
            isinstance(description[0], (int, long)) and isinstance(description[1], (int, long))):
            return description
        elif not isinstance(description, basestring):
            raise TypeError("value must be a string, or a tuple with 2 integer elements")
        if not description or description.lower()=='none':
            return (0L, 0xFFFFFFFFL)
        if description.lower()=='any':
            return (0L, 0L) ## This is the any address 0.0.0.0
        match = re.search(r'^(?P<net>.+?)/(?P<bits>\d+)$', description)
        if match:
            net     = match.group('net')
            netbits = int(match.group('bits'))
        else:
            try:
                net = socket.gethostbyname(description) # if not a net/mask it may be a host or ip
            except socket.gaierror:
                raise NameError, "invalid hostname or IP address: '%s'" % description
            netbits = 32
        if netbits < 0 or netbits > 32:
            raise ValueError, "invalid network mask in address: '%s' (should be between 0 and 32)" % description
        try:
            netaddr = socket.inet_aton(net)
        except:
            raise ValueError, "invalid IP address: '%s'" % net
        mask = (0xFFFFFFFFL << 32-netbits) & 0xFFFFFFFFL
        netbase = struct.unpack('!L', netaddr)[0] & mask
        return (netbase, mask)


class NetworkRangeList(list):
    """A list of NetworkRange objects separated by commas"""
    def __new__(cls, description):
        if description is None:
            return description
        elif isinstance(description, (list, tuple)):
            return [NetworkRange(x) for x in description] or None
        elif not isinstance(description, basestring):
            raise TypeError("value must be a string, list, tuple or None")
        if description.lower()=='none':
            return None
        lst = re.split(r'\s*,\s*', description)
        ranges = []
        for x in lst:
            try:
                range = NetworkRange(x)
            except NameError:
                log.warn("couldn't resolve hostname: `%s' (ignored)" % x)
            except ValueError:
                log.warn("Invalid network specification: `%s' (ignored)" % x)
            else:
                ranges.append(range)
        return ranges or None


class NetworkAddress(tuple):
    """
    A TCP/IP host[:port] network address.
    Host may be a hostname, an IP address or the keyword `any' which stands
    for 0.0.0.0. If port is missing, 0 will be used.
    The keyword `default' stands for `0.0.0.0:0' (0.0.0.0:default_port).

    Because the default port is 0, this class is not very useful to be used
    directly. Instead, it is meant to be subclassed to get more specific
    types of network addresses. For example to define a SIP proxy address:

        class SIPProxyAddress(NetworkAddress):
            default_port = 5060

    """

    default_port = 0

    def __new__(cls, value):
        if value is None:
            return value
        elif isinstance(value, tuple) and len(value)==2 and isinstance(value[1], (int, long)):
            return (Hostname(value[0]), value[1])
        elif not isinstance(value, basestring):
            raise TypeError("value must be a string, a (host, port) tuple or None")
        if value.lower() == 'none': return None
        if value.lower() == 'default': return ('0.0.0.0', cls.default_port)
        match = re.search(r'^(?P<address>.+?):(?P<port>\d+)$', value)
        if match:
            address = str(match.group('address'))
            port = int(match.group('port'))
        else:
            address = value
            port = cls.default_port
        try:
            address = Hostname(address)
        except ValueError:
            raise ValueError("invalid network address: %r" % value)
        return (address, port)


class EndpointAddress(NetworkAddress):
    """
    A network endpoint. This is a NetworkAddress that cannot be None or have
    an undefined address/port.

    This class is meant to be subclassed to get more specific network enpoint
    descriptions. For example for SIP endpoint:

        class SIPEndpointAddress(EndpointAddress):
            default_port = 5060
            name = 'SIP endpoint address'

    """

    default_port = 0
    name = 'endpoint address'

    def __new__(cls, value):
        address = NetworkAddress.__new__(cls, value)
        if address is None:
            raise ValueError("invalid %s: %s" % (cls.name, value))
        elif address[0]=='0.0.0.0' or address[1]==0:
            raise ValueError("invalid %s: %s:%s" % (cls.name, address[0], address[1]))
        return address



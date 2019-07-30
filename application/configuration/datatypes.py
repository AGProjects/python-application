
"""Basic data types to describe the type of the entries in the configuration file"""

import re
import socket
import struct

from application import log
from application.python import limit


__all__ = 'Boolean', 'LogLevel', 'StringList', 'IPAddress', 'Hostname', 'HostnameList', 'NetworkRange', 'NetworkRangeList', 'NetworkAddress', 'EndpointAddress'


class Boolean(object):
    """A boolean validator that handles multiple boolean input keywords: yes/no, true/false, on/off, 1/0"""

    __valuemap__ = {'1': True,  'yes': True, 'true': True,   'on': True,
                    '0': False, 'no': False, 'false': False, 'off': False}

    def __new__(cls, value):
        if isinstance(value, (int, long, float)):
            return bool(value)
        elif not hasattr(value, 'lower'):
            raise TypeError('value must be a string, number or boolean')
        try:
            return cls.__valuemap__[value.lower()]
        except KeyError:
            raise ValueError('not a boolean value: %r' % value)


class LogLevel(object):
    """A log level indicated by a non-negative integer or one of the named attributes of log.level"""

    def __new__(cls, value):
        if isinstance(value, basestring):
            value = value.upper()
        elif not isinstance(value, (int, long)):
            raise TypeError('value must be a string or number')
        named_levels = {level.name: level for level in log.level.named_levels}
        if value in named_levels:
            return named_levels[value]
        try:
            return log.NamedLevel(limit(int(value), min=log.level.NOTSET))
        except ValueError:
            raise ValueError('invalid log level: %s' % value)


class StringList(object):
    """A list of strings separated by commas"""

    def __new__(cls, value):
        if isinstance(value, (tuple, list)):
            return [str(x) for x in value]
        elif isinstance(value, basestring):
            if value.lower() in ('none', ''):
                return []
            return re.split(r'\s*,\s*', value)
        else:
            raise TypeError('value must be a string, list or tuple')


class IPAddress(str):
    """An IP address in quad dotted number notation"""

    def __new__(cls, value):
        try:
            socket.inet_aton(value)
        except socket.error:
            raise ValueError('invalid IP address: %r' % value)
        except TypeError:
            raise TypeError('value must be a string')
        return str(value)


class Hostname(str):
    """A Hostname or an IP address. The keyword `any' stands for '0.0.0.0'"""

    def __new__(cls, value):
        if not isinstance(value, basestring):
            raise TypeError('value must be a string')
        if value.lower() == 'any':
            return '0.0.0.0'
        return str(value)


class HostnameList(object):
    """A list of hostnames separated by commas"""

    def __new__(cls, description):
        if isinstance(description, (list, tuple)):
            return [Hostname(x) for x in description]
        elif not isinstance(description, basestring):
            raise TypeError('value must be a string, list or tuple')
        if description.lower() == 'none':
            return []
        lst = re.split(r'\s*,\s*', description)
        hosts = []
        for x in lst:
            try:
                host = Hostname(x)
            except ValueError as e:
                log.warning('%s (ignored)' % e)
            else:
                hosts.append(host)
        return hosts


class NetworkRange(object):
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
        if isinstance(description, tuple) and len(description) == 2 and all(isinstance(item, (int, long)) and 0 <= item < 2**32 for item in description):
            return description
        elif not isinstance(description, basestring):
            raise TypeError('value must be a string, or a tuple with 2 32-bit unsigned integers')
        if not description or description.lower() == 'none':
            return 0L, 0xFFFFFFFFL
        if description.lower() == 'any':
            return 0L, 0L  # This is the any address 0.0.0.0
        match = re.search(r'^(?P<address>.+?)/(?P<bits>\d+)$', description)
        if match:
            ip_address = match.group('address')
            mask_bits = int(match.group('bits'))
        else:
            try:
                ip_address = socket.gethostbyname(description)  # if not a network/mask it may be a host or ip
            except socket.gaierror:
                raise NameError('invalid hostname or IP address: %r' % description)
            mask_bits = 32
        if not 0 <= mask_bits <= 32:
            raise ValueError('invalid network mask in address: %r (should be between 0 and 32)' % description)
        try:
            network_address = socket.inet_aton(ip_address)
        except Exception:
            raise ValueError('invalid IP address: %r' % ip_address)
        network_mask = (0xFFFFFFFFL << 32-mask_bits) & 0xFFFFFFFFL
        base_address = struct.unpack('!L', network_address)[0] & network_mask
        return base_address, network_mask


class NetworkRangeList(object):
    """A list of NetworkRange objects separated by commas"""

    def __new__(cls, description):
        if description is None:
            return description
        elif isinstance(description, (list, tuple)):
            return [NetworkRange(x) for x in description] or None
        elif not isinstance(description, basestring):
            raise TypeError('value must be a string, list, tuple or None')
        if description.lower() == 'none':
            return None
        lst = re.split(r'\s*,\s*', description)
        ranges = []
        for x in lst:
            try:
                network_range = NetworkRange(x)
            except NameError:
                log.warning('Could not resolve hostname: %r (ignored)' % x)
            except ValueError:
                log.warning('Invalid network specification: %r (ignored)' % x)
            else:
                ranges.append(network_range)
        return ranges or None


class NetworkAddress(object):
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
        elif isinstance(value, tuple) and len(value) == 2 and isinstance(value[1], (int, long)):
            return Hostname(value[0]), value[1]
        elif not isinstance(value, basestring):
            raise TypeError('value must be a string, a (host, port) tuple or None')
        if value.lower() == 'none':
            return None
        if value.lower() == 'default':
            return '0.0.0.0', cls.default_port
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
            raise ValueError('invalid network address: %r' % value)
        return address, port


class EndpointAddress(NetworkAddress):
    """
    A network endpoint. This is a NetworkAddress that cannot be None or have
    an undefined address/port.

    This class is meant to be subclassed to get more specific network endpoint
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
            raise ValueError('invalid %s: %s' % (cls.name, value))
        elif address[0] == '0.0.0.0' or address[1] == 0:
            raise ValueError('invalid %s: %s:%s' % (cls.name, address[0], address[1]))
        return address

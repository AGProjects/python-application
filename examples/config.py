#!/usr/bin/python

"""Example of reading application settings from a configuration file"""

from application.configuration import *
from application.process import process
from application.system import host
from application import log

# Define a specific data type we will later use with the configuration
class Priority(int):
    """A numeric priority level. The keywords High, Normal and Low map to certain numeric values."""
    def __new__(typ, value):
        if isinstance(value, (int, long)):
            return int(value)
        elif isinstance(value, basestring):
            map = {'high': 10, 'normal': 50, 'low': 100}
            try:
                return map.get(value.lower()) or int(value)
            except ValueError:
                raise ValueError, "invalid priority value: should be a number or the keywords High, Normal or Low"
        else:
            raise TypeError, 'value should be an integer or string'


# Define a class that gives access (through its attributes) to the values
# defined in a section (or possibly more) of the configuration file.
# The data type for an attributes is taken from the type of the specified
# default value, or it can be declared using a ConfigSetting descriptor in
# case the type used to instantiate the attribute is just a validator.
#
# The python bool type is automatically mapped to the datatypes.Boolean
# validator which recognizes multiple logic values like: yes/no, on/off,
# true/false, 1/0, so there is no need to use a ConfigSetting descriptor
# for a boolean value, only to assign a True/False value to its attribute.

class NetworkConfig(ConfigSection):
    name = 'undefined'
    ip = ConfigSetting(type=datatypes.IPAddress, value=host.default_ip)
    port = 8000
    priority = ConfigSetting(type=Priority, value=Priority('Normal'))
    domains = ConfigSetting(type=datatypes.StringList, value=[])
    allow = ConfigSetting(type=datatypes.NetworkRangeList, value=[])
    use_tls = False

# And another class for another section
class StorageConfig(ConfigSection):
    dburi = 'mysql://undefined@localhost/database'

# Dump the default hardcoded values of the options defined above
print "Settings before reading the configuration file (default hardcoded values)\n"
print NetworkConfig
print
print StorageConfig
print

# Read the settings from the configuration file into the attributes of our
# configuration classes. The read function takes a configuration file name
# and a section name (or an iterable that returns multiple section names
# in which case they will be read in the order that the iterable returns
# them). Internally the ConfigSection will create a ConfigFile instance
# using the provided filename. The file is searched in both the system
# and the local config directories and the files which are present will be
# loaded in this order. This means that a local config file will overwrite
# settings from the system config file if both are present.
# The config directories are configurable on the process instance available
# from application.process.process, as process.system_config_directory and
# process.local_config_directory. By default the system config directory
# defaults to /etc and the local config directory defaults to the path from
# where the script is run, thus allowing applications to run from inside a
# directory without any other dependencies. In this example the config file
# will be read from ./config.ini which is in the local config directory.
#
# While reading the section, only settings that are defined on the config
# class wil be considered. Those present in the section that do not have a
# correspondent in the class attributes will be ignored, while the class
# attributes for which there are no settings in the section will remain
# unchanged.
#
NetworkConfig.read('config.ini', 'Network')
StorageConfig.read('config.ini', 'Storage')

# Dump the values of the options after they were loaded from the config file
print "\nSettings after reading the configuration file(s)\n"
print NetworkConfig
print
print StorageConfig
print

# Configuration options can be accessed as class attributes
ip = NetworkConfig.ip

# Starting with version 1.1.2, there is a simpler way to have a section loaded
# automatically, by defining the __cfgfile__ and __section__ attributes on
# the class. (Note: between version 1.1.2 through 1.1.4, __cfgfile__ was
# named __configfile__)

# Here is an example of such a class that will be automatically loaded

print "\n------------------------------------\n"
print "Using __cfgfile__ and __section__ to automatically load sections\n"

class AutoStorageConfig(ConfigSection):
    __cfgfile__ = 'config.ini'
    __section__ = 'Storage'
    dburi = 'mysql://undefined@localhost/database'

# Dump the values of the options after they were loaded from the config file
print "Settings in the automatically loaded section\n"
print AutoStorageConfig

# An example of how to use tracing to see inner workings of our configuration
# class and to display its internal state after it is operated on. We will
# redefine the NetworkConfig class with auto-loading and tracing enabled
#

print "\n------------------------------------\n"
print "Tracing the inner working of a config class using __tracing__\n"

class NetworkConfigTraced(ConfigSection):
    __cfgfile__ = 'config.ini'
    __section__ = 'Network'
    __tracing__ = log.level.INFO # log trace to INFO level

    name = 'undefined'
    ip = ConfigSetting(type=datatypes.IPAddress, value=host.default_ip)
    port = 8000
    priority = ConfigSetting(type=Priority, value=Priority('Normal'))
    domains = ConfigSetting(type=datatypes.StringList, value=[])
    allow = ConfigSetting(type=datatypes.NetworkRangeList, value=[])
    use_tls = False

print "\nReset to defaults and read settings from config file again\n"
# reset to defaults
NetworkConfigTraced.reset()
# read back from config file. since we defined __cfgfile__ and __section__
# we do not need to pass a file and section as arguments to read, the above
# mentioned class attributes will be used instead. Passing arguments to read()
# will overwrite the class attributes though.
NetworkConfigTraced.read()

print "\nChange individual options\n"
NetworkConfigTraced.name = 'manually_set_name'
NetworkConfigTraced.ip = '1.2.3.4'

print "\nSave current state, reset to defaults and then restore from saved state\n"
# save a snapshot of the current settings
state = dict(NetworkConfigTraced)
# reset to defaults
NetworkConfigTraced.reset()
# restore to a previously saved state
NetworkConfigTraced.set(**state)

# disabled tracing
NetworkConfigTraced.__tracing__ = None
# the following operations will not be traced
NetworkConfigTraced.reset()
NetworkConfigTraced.read()
NetworkConfigTraced.set(**state)


# We can also get individual settings from a given section.
#
# For this we create ConfigFile instance that will handle the configuration
# file. The information about the system and local configuration directories
# and where are the configuration files being looked up (which was presented
# above with the ConfigSection.read() method) apply here as well.
#

print "\n------------------------------------\n"
print "Reading individual settings from sections without using ConfigSection"

configuration = ConfigFile('config.ini')

dburi = configuration.get_setting('Storage', 'dburi', type=str, default='undefined')
print "\nGot dburi directly from Storage section as `%s'\n" % dburi


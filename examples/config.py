#!/usr/bin/python

"""Example of reading application settings from a configuration file"""

from application.configuration import *
from application.process import process
from application.util import host_ip

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
# The data type for the attributes is taken from the _dataTypes mapping
# if defined, else it is taken from the type of the default value assigned
# to the attribute. The python bool type is automatically mapped to
# datatypes.Boolean which recognizes multiple logic values like: yes/no,
# on/off, true/false, 1/0, so there is no need to define a type mapping
# for a boolean value, only to assign a True/False value to its attribute.

class NetworkConfig(ConfigSection):
    _dataTypes = {
        'ip': datatypes.IPAddress,
        'priority': Priority,
        'domains': datatypes.StringList,
        'allow': datatypes.NetworkRangeList
    }
    name = 'undefined'
    ip = host_ip
    port = 8000
    priority = Priority('Normal')
    domains = []
    allow = []
    use_tls = False

# And another class for another section
class StorageConfig(ConfigSection):
    dburi = 'mysql://undefined@localhost/database'

# Dump the default hardcoded values of the options defined above
print "\nSettings before reading the configuration file (default hardcoded values)\n"
dump_settings(NetworkConfig)
dump_settings(StorageConfig)

# Create a ConfigFile instance that handles our configuration
#
# The configuration files are read from two directories:
#  1. The directory where the application resides.
#  2. A system directory given by process.config_directory (/etc by default)
#
# The first directory is there to allow one to run an application that is
# self contained inside a directory. This directory is automatically
# determined from the application path and is not configurable.
# The second directory is useful if the application is installed and running
# from a standard path like /usr/bin. This directory is configurable using
# process.config_directory. In this example though, we do not use the system
# config directory, instead the configuration file is in the same directory
# as the example itself.
#
configuration = ConfigFile('config.ini')

# Read the settings from the configuration file into the attributes of our
# configuration classes defined above. The functions below will search in
# the configuration file in the specified section for settings that have
# names that match the names of the class attributes. If they are found,
# their values will be interpreted using the specified data types and if
# the values are valid they will be used to overwrite the default values
# of the corresponding attributes which were defined above.
# If an attribute doesn't have a corresponding value in the configuration
# file it will keep its default value defined above. The settings in the
# configuration file that do not have a corresponding attribute in the
# configuration class we load will be ignored.
#
configuration.read_settings('Network', NetworkConfig)
configuration.read_settings('Storage', StorageConfig)

# Dump the values of the options after they were loaded from the config file
print "\nSettings after reading the configuration file(s)\n"
dump_settings(NetworkConfig)
dump_settings(StorageConfig)

# Configuration options can be accessed as class attributes
ip = NetworkConfig.ip

# Or we can get individual options from a given section
dburi = configuration.get_option('Storage', 'dburi', default='undefined', type=str)
print "\nGot dburi from Storage as `%s'\n" % dburi


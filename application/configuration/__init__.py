# Copyright (C) 2004-2006 Dan Pascu <dan@ag-projetcs.com>
#

"""Processing the application configuration file"""

__all__ = ['ConfigSection', 'readSettings', 'getOption', 'getSection', 'dumpSettings', 'datatypes']

import os
try:    from ConfigParser import SafeConfigParser as ConfigParser
except: from ConfigParser import ConfigParser
from ConfigParser import NoSectionError

from application import log
from application.process import process
from application.configuration import datatypes


## The configuration name
name = 'config.ini'

## Context for the log system
logContext = {'system': 'configuration'}

## The configuration
Configuration = None


class ConfigSection:
    """Basic class that defines a section in the configuration file. Should be inherited."""
    _dataTypes = {}


def _read_configuration():
    global Configuration
    Configuration = ConfigParser()
    files = [os.path.join(path, name) for path in process.get_config_directories() if path is not None]
    Configuration.read(files)


def readSettings(section, object):
    """Update the object's attributes with values read from the given section in the config"""
    if Configuration is None:
        _read_configuration()
    if section not in Configuration.sections():
        return
    for prop in dir(object):
        if prop[0]=='_':
            continue
        ptype = object._dataTypes.get(prop, eval('object.%s.__class__' % prop))
        try:
            val = Configuration.get(section, prop)
        except:
            pass
        else:
            try:
                if ptype is bool:
                    value = bool(datatypes.Boolean(val))
                else:
                    value = ptype(val)
            except Exception, why:
                msg = "ignoring invalid config value: %s.%s=%s (%s)." % (section, prop, val, why)
                log.warn(msg, **logContext)
            else:
                setattr(object, prop, value)


def getOption(section, option, default='', otype=str):
    if Configuration is None:
        _read_configuration()
    try:
        value = Configuration.get(section, option)
    except:
        return default
    else:
        try:
            if otype is bool:
                return bool(datatypes.Boolean(value))
            else:
                return otype(value)
        except Exception, why:
            msg = "ignoring invalid config value: %s.%s=%s (%s)." % (section, option, value, why)
            log.warn(msg, **logContext)
            return default


def getSection(section):
    """Return a list of tuples with name, value pairs from the section"""
    if Configuration is None:
        _read_configuration()
    try:
        return Configuration.items(section)
    except NoSectionError:
        return None


def dumpSettings(object):
    print '%s:' % object.__name__
    for x in dir(object):
        if x[0] == '_': continue
        print '  %s: %s' % (x, eval('object.%s' % x))
    print ''


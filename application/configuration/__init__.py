# Copyright (C) 2006-2007 Dan Pascu. See LICENSE for details.
#

"""Application configuration file handling"""

__all__ = ['ConfigSection', 'read_settings', 'get_option', 'get_section', 'dump_settings', 'datatypes']

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
    """Defines a section in the configuration file"""
    _dataTypes = {}


def _read_configuration():
    global Configuration
    Configuration = ConfigParser()
    files = [os.path.join(path, name) for path in process.get_config_directories() if path is not None]
    Configuration.read(files)


def read_settings(section, object):
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


def get_option(section, option, default='', type=str):
    if Configuration is None:
        _read_configuration()
    try:
        value = Configuration.get(section, option)
    except:
        return default
    else:
        try:
            if type is bool:
                return bool(datatypes.Boolean(value))
            else:
                return type(value)
        except Exception, why:
            msg = "ignoring invalid config value: %s.%s=%s (%s)." % (section, option, value, why)
            log.warn(msg, **logContext)
            return default


def get_section(section):
    """Return a list of tuples with name, value pairs from the section"""
    if Configuration is None:
        _read_configuration()
    try:
        return Configuration.items(section)
    except NoSectionError:
        return None


def dump_settings(object):
    print '%s:' % object.__name__
    for x in dir(object):
        if x[0] == '_': continue
        print '  %s: %s' % (x, eval('object.%s' % x))
    print ''


# Backward compatibility functions. Do not use! They will be removed soon.
#
import warnings

def readSettings(section, object):
    warnings.warn("readSettings was replaced by read_settings", DeprecationWarning, stacklevel=2)
    return read_settings(section, object)

def getOption(section, option, default='', type=str):
    warnings.warn("getOption was replaced by get_option", DeprecationWarning, stacklevel=2)
    return get_option(section, option, default, type)

def getSection(section):
    warnings.warn("getSection was replaced by get_section", DeprecationWarning, stacklevel=2)
    return get_section(section)

def dumpSettings(object):
    warnings.warn("dumpSettings was replaced by dump_settings", DeprecationWarning, stacklevel=2)
    dump_settings(object)


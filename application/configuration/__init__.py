# Copyright (C) 2006-2007 Dan Pascu. See LICENSE for details.
#

"""Application configuration file handling"""

__all__ = ['ConfigSection', 'ConfigFile', 'datatypes']

import os
try:    from ConfigParser import SafeConfigParser as ConfigParser
except: from ConfigParser import ConfigParser
from ConfigParser import NoSectionError

from application import log
from application.process import process
from application.configuration import datatypes


class ConfigSection:
    """Defines a section in the configuration file"""
    _dataTypes = {}


class ConfigFile(object):
    """Provide access to a configuration file"""
    
    instances = {}
    log_context = {'system': 'configuration'}
    
    def __new__(cls, filename):
        if not cls.instances.has_key(filename):
            instance = object.__new__(cls)
            instance.parser = ConfigParser()
            files = [os.path.join(path, filename) for path in process.get_config_directories() if path is not None]
            instance.parser.read(files)
            cls.instances[filename] = instance
        return cls.instances[filename]
    
    def read_settings(self, section, cls):
        """Update cls's attributes with values read from the given section"""
        if not issubclass(cls, ConfigSection):
            raise TypeError("cls must be a subclass of ConfigSection")
        if section not in self.parser.sections():
            return
        for prop in dir(cls):
            if prop[0]=='_':
                continue
            ptype = cls._dataTypes.get(prop, eval('cls.%s.__class__' % prop))
            try:
                val = self.parser.get(section, prop)
            except:
                continue
            else:
                try:
                    if ptype is bool:
                        value = bool(datatypes.Boolean(val))
                    else:
                        value = ptype(val)
                except Exception, why:
                    msg = "ignoring invalid config value: %s.%s=%s (%s)." % (section, prop, val, why)
                    log.warn(msg, **ConfigFile.log_context)
                else:
                    setattr(cls, prop, value)
    
    def get_option(self, section, option, default='', type=str):
        """Get an option from a given section using type, or default if not found"""
        try:
            value = self.parser.get(section, option)
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
                log.warn(msg, **ConfigFile.log_context)
                return default
    
    def get_section(self, section):
        """Return a list of tuples with name, value pairs from the section or None if section doesn't exist"""
        try:
            return self.parser.items(section)
        except NoSectionError:
            return None
    
    @staticmethod
    def dump_settings(cls):
        print '%s:' % cls.__name__
        for x in dir(cls):
            if x[0] == '_': continue
            print '  %s: %s' % (x, eval('cls.%s' % x))
        print ''



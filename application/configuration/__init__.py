# Copyright (C) 2006-2007 Dan Pascu. See LICENSE for details.
#

"""Application configuration file handling"""

__all__ = ['ConfigFile', 'ConfigSection', 'ConfigSetting', 'datatypes', 'dump_settings']

import os
try:    from ConfigParser import SafeConfigParser as ConfigParser
except: from ConfigParser import ConfigParser
from ConfigParser import NoSectionError
from warnings import warn

from application import log
from application.process import process
from application.configuration import datatypes


class ConfigSetting(object):
    def __init__(self, type, value=None):
        self.type = type
        self.value = value

    def __get__(self, obj, objtype):
        return self.value

    def __set__(self, obj, value):
        if value is not None and not isinstance(value, self.type):
            value = self.type(value)
        self.value = value


class ConfigSectionMeta(type):
    def __init__(cls, clsname, bases, dct):
        if None not in (cls.__configfile__, cls.__section__):
            config_file = ConfigFile(cls.__configfile__)
            config_file.read_settings(cls.__section__, cls)

    def __new__(clstype, clsname, bases, dct):
        settings = {}
        if '_datatypes' in dct:
            warn("using _datatypes is deprecated in favor of ConfigSetting descriptors and will be removed in 1.2.0.", DeprecationWarning)
            for setting_name, setting_type in dct['_datatypes'].iteritems():
                settings[setting_name] = ConfigSetting(type=setting_type)
        for attr, value in dct.iteritems():
            if attr == '_datatypes' or attr.startswith('__'):
                continue
            if isinstance(value, ConfigSetting):
                settings[attr] = value
                continue
            if attr in settings:
                # already added descriptor from _datatypes declarations
                data_type = settings[attr]
            else:
                if type(value) is bool:
                    data_type = ConfigSetting(datatypes.Boolean)
                else:
                    data_type = ConfigSetting(type(value))
                settings[attr] = data_type
            data_type.value = value
        for setting_name in set(settings)-set(dct):
            log.warn("%s declared in %s._datatypes but not defined" % (setting_name, clsname))
            del settings[setting_name]
        dct.update(settings)
        dct['__settings__'] = settings
        return type.__new__(clstype, clsname, bases, dct)

    def __setattr__(cls, attr, value):
        if attr in cls.__settings__:
            cls.__settings__[attr].__set__(None, value)
        else:
            type.__setattr__(cls, attr, value)


class ConfigSection(object):
    """Defines a section in the configuration file"""
    __metaclass__ = ConfigSectionMeta
    __configfile__ = None
    __section__ = None

    def __new__(cls, *args, **kwargs):
        raise TypeError("cannot instantiate ConfigSection class")


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
        for name in cls.__settings__:
            try:
                value = self.parser.get(section, name)
            except:
                continue
            else:
                try:
                    setattr(cls, name, value)
                except Exception, why:
                    msg = "ignoring invalid config value: %s.%s=%s (%s)." % (section, name, value, why)
                    log.warn(msg, **ConfigFile.log_context)
    
    def get_setting(self, section, setting, type=str, default=''):
        """Get a setting from a given section using type, or default if not found"""
        try:
            value = self.parser.get(section, setting)
        except:
            return default
        else:
            try:
                if type is bool:
                    return datatypes.Boolean(value)
                else:
                    return type(value)
            except Exception, why:
                msg = "ignoring invalid config value: %s.%s=%s (%s)." % (section, setting, value, why)
                log.warn(msg, **ConfigFile.log_context)
                return default
    
    def get_option(self, section, option, default='', type=str):
        """Get an option from a given section using type, or default if not found"""
        warn("get_option is deprecated in favor of get_setting and will be removed in 1.2.0.", DeprecationWarning)
        return self.get_setting(section, option, type=type, default=default)
    
    def get_section(self, section):
        """Return a list of tuples with name, value pairs from the section or None if section doesn't exist"""
        try:
            return self.parser.items(section)
        except NoSectionError:
            return None


def dump_settings(cls):
    """Print a ConfigSection class attributes"""
    print '%s:' % cls.__name__
    for name in cls.__settings__:
        print '  %s: %s' % (name, getattr(cls, name))
    print ''


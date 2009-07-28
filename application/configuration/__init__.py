# Copyright (C) 2006-2007 Dan Pascu. See LICENSE for details.
#

"""Application configuration file handling"""

__all__ = ['ConfigFile', 'ConfigSection', 'ConfigSetting', 'datatypes', 'dump_settings']

import os
import types
try:    from ConfigParser import SafeConfigParser as ConfigParser
except: from ConfigParser import ConfigParser
from ConfigParser import NoSectionError
from itertools import chain
from warnings import warn

from application import log
from application.process import process
from application.python.descriptor import isdescriptor
from application.configuration import datatypes


class ConfigSetting(object):
    def __init__(self, type, value=None):
        self.type = type
        self.value = value
        self.type_is_class = isinstance(type, (types.ClassType, types.TypeType))

    def __get__(self, obj, objtype):
        return self.value

    def __set__(self, obj, value, convert=True):
        if convert and value is not None and not (self.type_is_class and isinstance(value, self.type)):
            value = self.type(value)
        self.value = value


class ConfigSectionMeta(type):
    def __init__(cls, clsname, bases, dct):
        cls.__defaults__ = dict(cls)
        if None not in (cls.__configfile__, cls.__section__):
            if isinstance(cls.__configfile__, ConfigFile):
                config_file = cls.__configfile__
            else:
                config_file = ConfigFile(cls.__configfile__)
            config_file.read_settings(cls.__section__, cls)

    def __new__(clstype, clsname, bases, dct):
        settings = {}
        # copy all settings defined by parents unless also defined in the class being constructed
        for name, setting in chain(*(cls.__settings__.iteritems() for cls in bases if isinstance(cls, ConfigSectionMeta))):
            if name not in dct and name not in settings:
                settings[name] = ConfigSetting(type=setting.type, value=setting.value)
        if '_datatypes' in dct:
            warn("using _datatypes is deprecated in favor of ConfigSetting descriptors and will be removed in 1.2.0.", DeprecationWarning)
            for setting_name, setting_type in dct['_datatypes'].iteritems():
                try:
                    value = dct[setting_name]
                except KeyError:
                    log.warn("%s declared in %s._datatypes but not defined" % (setting_name, clsname))
                else:
                    settings[setting_name] = ConfigSetting(type=setting_type, value=value)
        for attr, value in dct.iteritems():
            if isinstance(value, ConfigSetting):
                settings[attr] = value
            elif attr == '_datatypes' or attr.startswith('__'):
                continue
            elif isdescriptor(value) or type(value) is types.BuiltinFunctionType:
                continue
            elif attr in settings:
                pass # already added descriptor from _datatypes declarations
            else:
                if type(value) is bool:
                    data_type = datatypes.Boolean
                else:
                    data_type = type(value)
                settings[attr] = ConfigSetting(type=data_type, value=value)
        dct.update(settings)
        dct['__settings__'] = settings
        return type.__new__(clstype, clsname, bases, dct)

    def __iter__(cls):
        return ((name, desc.__get__(None, cls)) for name, desc in cls.__settings__.iteritems())

    def __setattr__(cls, attr, value):
        if attr in cls.__settings__:
            cls.__settings__[attr].__set__(None, value)
        else:
            type.__setattr__(cls, attr, value)

    def __delattr__(cls, attr):
        if attr in cls.__settings__:
            raise AttributeError("'%s' attribute '%s' cannot be deleted" % (cls.__name__, attr))
        else:
            type.__delattr__(cls, attr)


class ConfigSection(object):
    """
    Defines a section in the configuration file

    Settings defined in superclasses are not inherited, but cloned as if
    defined in the subclass using ConfigSetting. All other attributes
    are inherited as normal.
    """
    __metaclass__ = ConfigSectionMeta
    __configfile__ = None
    __section__ = None

    def __new__(cls, *args, **kwargs):
        raise TypeError("cannot instantiate ConfigSection class")

    @classmethod
    def __set__(cls, **kw):
        """Set multiple settings at once"""
        if not set(cls.__settings__).issuperset(kw):
            raise TypeError("Got unexpected keyword argument '%s'" % set(kw).difference(cls.__settings__).pop())
        saved_state = dict(cls)
        try:
            for name, value in kw.iteritems():
                setattr(cls, name, value)
        except:
            for name, descriptor in cls.__settings__.iteritems():
                descriptor.__set__(None, saved_state[name], convert=False)
            raise

    @classmethod
    def __reset__(cls):
        """Reset settings to the default values from the class definition"""
        for name, descriptor in cls.__settings__.iteritems():
            descriptor.__set__(None, cls.__defaults__[name], convert=False)

    @classmethod
    def __read__(cls, cfgfile=None, section=None):
        """Update settings by reading them from the given file and section"""
        cfgfile = cfgfile or cls.__configfile__
        section = section or cls.__section__
        if None in (cfgfile, section):
            raise ValueError("A config file and section are required for reading settings")
        if isinstance(cfgfile, ConfigFile):
            config_file = cfgfile
        else:
            config_file = ConfigFile(cfgfile)
        if isinstance(section, basestring):
            section_list = (section,)
        else:
            section_list = section
        for section in section_list:
            for name, value in config_file.get_section(section, filter=cls.__settings__, default=[]):
                try:
                    setattr(cls, name, value)
                except Exception, why:
                    msg = "ignoring invalid config value: %s.%s=%s (%s)." % (section, name, value, why)
                    log.warn(msg, **config_file.log_context)

    set   = __set__
    reset = __reset__
    read  = __read__


class ConfigFile(object):
    """Provide access to a configuration file"""
    
    instances = {}
    log_context = {'system': 'configuration'}

    def __new__(cls, filename):
        files = []
        timestamp = 0
        for path in process.get_config_directories():
            file = os.path.realpath(os.path.join(path, filename))
            if os.access(file, os.R_OK):
                try:
                    timestamp = max(timestamp, os.stat(file).st_mtime)
                except (OSError, IOError):
                    continue
                files.append(file)

        instance = cls.instances.get(filename, None)
        if instance is None or instance.files != files or instance.timestamp < timestamp:
            instance = object.__new__(cls)
            instance.parser = ConfigParser()
            instance.files = instance.parser.read(files)
            instance.timestamp = timestamp
            cls.instances[filename] = instance
        return instance

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
        """Get a setting from a given section using type, or default if missing"""
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
        """Get an option from a given section using type, or default if missing"""
        warn("get_option is deprecated in favor of get_setting and will be removed in 1.2.0.", DeprecationWarning)
        return self.get_setting(section, option, type=type, default=default)
    
    def get_section(self, section, filter=None, default=None):
        """
        Return a list of (name, value) pairs from a section. If filter is an
        iterable, use it to filter the returned pairs by name. If section is
        missing, return the value specified by the default argument.
        """
        try:
            if filter is None:
                items = self.parser.items(section)
            else:
                items = [(name, value) for name, value in self.parser.items(section) if name in filter]
        except NoSectionError:
            return default
        else:
            return items


def dump_settings(cls):
    """Print a ConfigSection class attributes"""
    print '%s:' % cls.__name__
    for name in cls.__settings__:
        print '  %s: %s' % (name, getattr(cls, name))
    print ''


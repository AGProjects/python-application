# Copyright (C) 2006-2012 Dan Pascu. See LICENSE for details.
#

"""Application configuration file handling"""

import os

from ConfigParser import SafeConfigParser, NoSectionError
from itertools import chain
from types import ClassType, TypeType, BuiltinFunctionType

from application import log
from application.process import process
from application.python.descriptor import isdescriptor
from application.configuration import datatypes


__all__ = ['ConfigFile', 'ConfigSection', 'ConfigSetting', 'SaveState', 'AtomicUpdate', 'datatypes']


class ConfigFile(object):
    """Provide access to a configuration file"""
    
    instances = {}
    log_context = {'system': 'configuration'}

    def __new__(cls, filename):
        files = []
        timestamp = 0
        for path in process.get_config_directories():
            config_file = os.path.realpath(os.path.join(path, filename))
            if os.access(config_file, os.R_OK):
                try:
                    timestamp = max(timestamp, os.stat(config_file).st_mtime)
                except (OSError, IOError):
                    continue
                files.append(config_file)

        instance = cls.instances.get(filename, None)
        if instance is None or instance.files != files or instance.timestamp < timestamp:
            instance = object.__new__(cls)
            instance.parser = SafeConfigParser()
            instance.parser.optionxform = lambda x: x.replace('-', '_')
            instance.files = instance.parser.read(files)
            instance.filename = filename
            instance.timestamp = timestamp
            cls.instances[filename] = instance
        return instance

    def get_setting(self, section, setting, type=str, default=''):
        """Get a setting from a given section using type, or default if missing"""
        try:
            value = self.parser.get(section, setting)
        except Exception:
            return default
        else:
            try:
                if type is bool:
                    return datatypes.Boolean(value)
                else:
                    return type(value)
            except Exception, e:
                msg = "ignoring invalid config value: %s.%s=%s (%s)." % (section, setting, value, e)
                log.warn(msg, **ConfigFile.log_context)
                return default
    
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


class ConfigSetting(object):
    def __init__(self, type, value=None):
        self.type = type
        self.value = value

    def __get__(self, obj, owner):
        return self.value

    def __set__(self, obj, value, convert=True):
        if convert and value is not None and not (self.type_is_class and isinstance(value, self.type)):
            value = self.type(value)
        self.value = value


class ConfigSectionMeta(type):
    def __init__(cls, name, bases, dct):
        cls.__defaults__ = dict(cls)
        cls.__trace__("Dumping initial %s state:\n%s", cls.__name__, cls)
        if None not in (cls.__cfgfile__, cls.__section__):
            cls.__read__()

    def __new__(mcls, name, bases, dct):
        settings = {}
        # copy all settings defined by parents unless also defined in the class being constructed
        for name, setting in chain(*(cls.__settings__.iteritems() for cls in bases if isinstance(cls, ConfigSectionMeta))):
            if name not in dct and name not in settings:
                settings[name] = ConfigSetting(type=setting.type, value=setting.value)
        for attr, value in dct.iteritems():
            if isinstance(value, ConfigSetting):
                settings[attr] = value
            elif attr.startswith('__') or isdescriptor(value) or type(value) is BuiltinFunctionType:
                continue
            else:
                if type(value) is bool:
                    data_type = datatypes.Boolean
                else:
                    data_type = type(value)
                settings[attr] = ConfigSetting(type=data_type, value=value)
        dct.update(settings)
        dct['__settings__'] = settings
        if dct.get('__tracing__', None) not in (log.level.INFO, log.level.DEBUG, None):
            raise ValueError("__tracing__ must be one of log.level.INFO, log.level.DEBUG or None")
        return type.__new__(mcls, name, bases, dct)

    def __str__(cls):
        return "%s:\n%s" % (cls.__name__, '\n'.join("  %s = %r" % (name, value) for name, value in cls) or "  pass")

    def __iter__(cls):
        return ((name, desc.__get__(None, cls)) for name, desc in cls.__settings__.iteritems())

    def __setattr__(cls, attr, value):
        if attr in cls.__settings__:
            cls.__settings__[attr].__set__(None, value)
            cls.__trace__("setting %s.%s as %r from %r", cls.__name__, attr, getattr(cls, attr), value)
        else:
            if attr == '__tracing__' and value not in (log.level.INFO, log.level.DEBUG, None):
                raise ValueError("__tracing__ must be one of log.level.INFO, log.level.DEBUG or None")
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

    The following special attributes can be set on a ConfigSection class:

      __cfgtype__ - the ConfigFile type used to read/parse the config file
      __cfgfile__ - the configuration file name
      __section__ - the section in the config file. It can be a string for
                    reading one section, or an iterable returning strings
                    for reading multiple sections (they will be read in
                    the order the iterable returns them)
      __tracing__ - one of log.level.INFO, log.level.DEBUG or None
                    indicating where to log messages about the inner
                    workings of the ConfigSection
    """

    __metaclass__ = ConfigSectionMeta
    __cfgtype__ = ConfigFile
    __cfgfile__ = None
    __section__ = None
    __tracing__ = None

    def __new__(cls, *args, **kwargs):
        raise TypeError("cannot instantiate ConfigSection class")

    @classmethod
    def __set__(cls, **kw):
        """Set multiple settings at once"""
        if not set(cls.__settings__).issuperset(kw):
            raise TypeError("Got unexpected keyword argument '%s'" % set(kw).difference(cls.__settings__).pop())
        saved_state = dict(cls)
        cls.__trace__("changing multiple settings of %s", cls.__name__)
        try:
            for name, value in kw.iteritems():
                setattr(cls, name, value)
        except Exception:
            cls.__trace__("reverting settings to previous values due to error while setting %s", name)
            for name, descriptor in cls.__settings__.iteritems():
                descriptor.__set__(None, saved_state[name], convert=False)
            raise
        else:
            cls.__trace__("Dumping %s state after set():\n%s", cls.__name__, cls)

    @classmethod
    def __reset__(cls):
        """Reset settings to the default values from the class definition"""
        cls.__trace__("resetting %s to default values", cls.__name__)
        for name, descriptor in cls.__settings__.iteritems():
            descriptor.__set__(None, cls.__defaults__[name], convert=False)
        cls.__trace__("Dumping %s state after reset():\n%s", cls.__name__, cls)

    @classmethod
    def __read__(cls, cfgfile=None, section=None):
        """Update settings by reading them from the given file and section"""
        cfgfile = cfgfile or cls.__cfgfile__
        section = section or cls.__section__
        if None in (cfgfile, section):
            raise ValueError("A config file and section are required for reading settings")
        if isinstance(cfgfile, ConfigFile):
            config_file = cfgfile
        else:
            config_file = cls.__cfgtype__(cfgfile)
        if isinstance(section, basestring):
            section_list = (section,)
        else:
            section_list = section
        cls.__trace__("reading %s from %s requested as '%s'", cls.__name__, ', '.join(config_file.files), config_file.filename)
        for section in section_list:
            cls.__trace__("reading section '%s'", section)
            for name, value in config_file.get_section(section, filter=cls.__settings__, default=[]):
                try:
                    setattr(cls, name, value)
                except Exception, why:
                    msg = "ignoring invalid config value: %s.%s=%s (%s)." % (section, name, value, why)
                    log.warn(msg, **config_file.log_context)
        cls.__trace__("Dumping %s state after read():\n%s", cls.__name__, cls)

    @classmethod
    def __trace__(cls, message, *args):
        if cls.__tracing__ == log.level.INFO:
            log.info(message % args)
        elif cls.__tracing__ == log.level.DEBUG:
            log.debug(message % args)

    set   = __set__
    reset = __reset__
    read  = __read__



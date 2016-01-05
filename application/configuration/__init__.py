# Copyright (C) 2006-2016 Dan Pascu. See LICENSE for details.
#

"""A framework for describing and handling .ini configuration files as objects with attributes"""

import os

from ConfigParser import SafeConfigParser, NoSectionError
from inspect import isclass
from itertools import chain
from types import BuiltinFunctionType

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
        if convert and value is not None and not (isclass(self.type) and isinstance(value, self.type)):
            value = self.type(value)
        self.value = value


class SaveState(object):
    def __init__(self, owner):
        if not isclass(owner) or not isinstance(owner, ConfigSectionType):
            raise TypeError("owner should be a ConfigSection subclass")
        self.__owner__ = owner
        self.__state__ = dict(owner)

    def __repr__(self):
        return "<{0.__owner__.__name__} state: {0.__state__!r}>".format(self)

    def __getitem__(self, item):
        return self.__state__[item]

    def __iter__(self):
        return self.__state__.iteritems()

    def __len__(self):
        return len(self.__state__)

    def __eq__(self, other):
        if not isinstance(other, SaveState):
            return NotImplemented
        return self.__owner__ is other.__owner__ and self.__state__ == other.__state__

    def __ne__(self, other):
        return not (self == other)


class AtomicUpdate(object):
    def __init__(self, config_section):
        self.config_section = config_section

    def __enter__(self):
        self._saved_state = SaveState(self.config_section)
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if exc_value is not None:
            self.config_section.reset(state=self._saved_state)
        del self._saved_state
        return False


class ConfigSectionType(type):
    __cfgtype__ = ConfigFile
    __cfgfile__ = None
    __section__ = None

    def __new__(mcls, name, bases, dictionary):
        settings = {}
        # copy all settings defined by parents unless also defined in the class being constructed
        for name, setting in chain(*(cls.__settings__.iteritems() for cls in bases if isinstance(cls, ConfigSectionType))):
            if name not in dictionary and name not in settings:
                settings[name] = ConfigSetting(type=setting.type, value=setting.value)
        for attr, value in dictionary.iteritems():
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
        dictionary.update(settings)

        cls = super(ConfigSectionType, mcls).__new__(mcls, name, bases, dictionary)
        cls.__settings__ = settings
        cls.__defaults__ = SaveState(cls)

        return cls

    def __init__(cls, name, bases, dictionary):
        super(ConfigSectionType, cls).__init__(name, bases, dictionary)
        if cls.__cfgfile__ is not None and cls.__section__ is not None:
            cls.read()

    def __str__(cls):
        return "%s:\n%s" % (cls.__name__, '\n'.join("  %s = %r" % (name, value) for name, value in cls) or "  pass")

    def __iter__(cls):
        return ((name, descriptor.__get__(cls, cls.__class__)) for name, descriptor in cls.__settings__.iteritems())

    def __setattr__(cls, name, value):
        if name == '__settings__' or name not in cls.__settings__:  # need to check for __settings__ as it is set first and the second part of the test depends on it being available
            super(ConfigSectionType, cls).__setattr__(name, value)
        else:
            cls.__settings__[name].__set__(cls, value)

    def __delattr__(cls, name):
        if name == '__settings__' or name in cls.__settings__:
            raise AttributeError("'%s' attribute '%s' cannot be deleted" % (cls.__name__, name))
        else:
            super(ConfigSectionType, cls).__delattr__(name)

    def read(cls, cfgfile=None, section=None):
        """Read the settings from the given file and section"""
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
        for section in section_list:
            for name, value in config_file.get_section(section, filter=cls.__settings__, default=[]):
                try:
                    setattr(cls, name, value)
                except Exception, e:
                    msg = "ignoring invalid config value: %s.%s=%s (%s)." % (section, name, value, e)
                    log.warn(msg, **config_file.log_context)

    def set(cls, **kw):
        """Atomically set multiple settings at once"""
        if not set(kw).issubset(cls.__settings__):
            raise TypeError("Got unexpected keyword argument '%s'" % set(kw).difference(cls.__settings__).pop())
        with AtomicUpdate(cls):
            for name, value in kw.iteritems():
                setattr(cls, name, value)

    def reset(cls, state=None):
        """Reset settings to the provided save state or to the default values from the class definition if state is None"""
        state = state or cls.__defaults__
        if not isinstance(state, SaveState):
            raise TypeError("state should be a SaveState instance")
        if state.__owner__ is not cls:
            raise ValueError("save state does not belong to this config section")
        for name, descriptor in cls.__settings__.iteritems():
            descriptor.__set__(cls, state[name], convert=False)


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
    """

    __metaclass__ = ConfigSectionType

    __cfgtype__ = ConfigFile
    __cfgfile__ = None
    __section__ = None

    def __new__(cls, *args, **kw):
        raise TypeError("cannot instantiate ConfigSection class")



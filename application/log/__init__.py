
"""Application logging system for console and syslog"""

import abc
import io
import sys
import logging
import warnings

from application.log.extensions import twisted
from application.python import Null

try:
    import syslog
except ImportError:
    syslog = Null


__all__ = ('ContextualLogger', 'level', 'debug', 'info', 'warning', 'warn', 'error', 'exception', 'critical', 'fatal',
           'get_logger', 'set_default_formatter', 'set_handler', 'capture_warnings', 'capture_output', 'use_syslog')


class Formatter(logging.Formatter):
    prefix_format = '{record.levelname:<8s} [{record.name}] '
    prefix_length = 0

    def format(self, record):
        record.message = record.getMessage()
        if record.exc_info and not record.exc_text:
            # Cache the traceback text to avoid converting it multiple times (this is problematic with multiple formatters with different formatException)
            record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            message = record.message + '\n' + record.exc_text if record.message else record.exc_text
        else:
            message = record.message
        if self.prefix_format:
            prefix = self.prefix_format.format(record=record).ljust(self.prefix_length)
            message = '\n'.join(prefix+l for l in message.split('\n'))
        return message

    def formatException(self, exc_info):
        output = super(Formatter, self).formatException(exc_info)
        return 'No exception' if output == 'None' else output


_default_formatter = logging._defaultFormatter = Formatter()

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(_default_formatter)
root_logger = logging.getLogger()
root_logger.addHandler(stream_handler)
root_logger.name = 'main'


def set_default_formatter(formatter):
    global _default_formatter
    _default_formatter = logging._defaultFormatter = formatter
    for handler in root_logger.handlers:
        handler.setFormatter(formatter)


def get_logger(name=None):
    return logging.getLogger(name)


def debug(message, *args, **kw):
    root_logger.debug(message, *args, **kw)


def info(message, *args, **kw):
    root_logger.info(message, *args, **kw)


def warning(message, *args, **kw):
    root_logger.warning(message, *args, **kw)


warn = warning


def error(message, *args, **kw):
    root_logger.error(message, *args, **kw)


def exception(message='', *args, **kw):
    exc_info = kw.pop('exc_info', None) or True
    root_logger.error(message, *args, exc_info=exc_info, **kw)


def critical(message, *args, **kw):
    root_logger.critical(message, *args, **kw)


fatal = critical


# The following two functions are deprecated and will be removed in the future
#
def msg(*args, **kw):
    warnings.warn('log.msg is deprecated and should be replaced with log.info', category=DeprecationWarning, stacklevel=2)
    info(*args, **kw)


def err(*args, **kw):
    warnings.warn('log.err is deprecated and should be replaced with log.exception', category=DeprecationWarning, stacklevel=2)
    exception(*args, **kw)


# noinspection PyShadowingBuiltins
def _showwarning(message, category, filename, lineno, file=None, line=None):
    if file is not None:
        _warnings_showwarning(message, category, filename, lineno, file, line)
    else:
        _warning_logger.warning(warnings.formatwarning(message, category, filename, lineno, line).rstrip('\n'))


_warnings_showwarning = warnings.showwarning
_warning_logger = logging.getLogger('python')
warnings.showwarning = _showwarning  # By default we capture and log python warnings through the logging system


def capture_warnings(capture=True):
    """Toggle capturing and logging of python warnings through the logging system"""
    warnings.showwarning = _showwarning if capture else _warnings_showwarning


# Overwrite the exception method on the Logger class and the one in the logging module with our enhanced version
# that can be called without a message to just log the traceback and it also accepts passing a custom exc_info
# in order to log a particular exception, not only the current one.

class Logger(logging.Logger):
    def exception(self, message='', *args, **kw):
        exc_info = kw.pop('exc_info', None) or True
        self.error(message, *args, exc_info=exc_info, **kw)


# logging.setLoggerClass(Logger)
logging.Logger.exception = Logger.exception.__func__
logging.exception = exception


class ContextualLogger(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, logger, **context):
        self.logger = logger
        self.__dict__.update(context)

    @abc.abstractmethod
    def apply_context(self, message):
        return message

    def debug(self, message, *args, **kw):
        self.logger.debug(self.apply_context(message), *args, **kw)

    def info(self, message, *args, **kw):
        self.logger.info(self.apply_context(message), *args, **kw)

    def warning(self, message, *args, **kw):
        self.logger.warning(self.apply_context(message), *args, **kw)

    warn = warning

    def error(self, message, *args, **kw):
        self.logger.error(self.apply_context(message), *args, **kw)

    def exception(self, message='', *args, **kw):
        exc_info = kw.pop('exc_info', None) or True
        self.logger.error(self.apply_context(message), *args, exc_info=exc_info, **kw)

    def critical(self, message, *args, **kw):
        self.logger.critical(self.apply_context(message), *args, **kw)

    fatal = critical

    # noinspection PyShadowingNames
    def log(self, level, message, *args, **kw):
        self.logger.log(level, self.apply_context(message), *args, **kw)


class NamedLevel(int):
    _level_instances = {}

    # noinspection PyInitNewSignature,PyArgumentList
    def __new__(cls, value):
        if value in cls._level_instances:
            return cls._level_instances[value]
        instance = int.__new__(cls, value)
        instance.name = logging.getLevelName(value)
        cls._level_instances[value] = instance
        return instance

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name

    def __format__(self, fmt):
        if fmt.endswith('s'):
            return self.name.__format__(fmt)
        else:
            return super(NamedLevel, self).__format__(fmt)

    def __setattr__(self, name, value):
        if name == 'name' and 'name' in self.__dict__:
            logging.addLevelName(int(self), value)
        super(NamedLevel, self).__setattr__(name, value)


class CurrentLevelDescriptor(object):
    def __init__(self, value):
        self.value = value
        root_logger.setLevel(value)

    def __get__(self, obj, owner):
        return self.value

    def __set__(self, obj, value):
        self.value = value
        root_logger.setLevel(value)


class LevelHandler(object):
    NOTSET = NamedLevel(logging.NOTSET)
    DEBUG = NamedLevel(logging.DEBUG)
    INFO = NamedLevel(logging.INFO)
    WARNING = NamedLevel(logging.WARNING)
    ERROR = NamedLevel(logging.ERROR)
    CRITICAL = NamedLevel(logging.CRITICAL)

    current = CurrentLevelDescriptor(INFO)

    @property
    def named_levels(self):
        return {self.NOTSET, self.DEBUG, self.INFO, self.WARNING, self.ERROR, self.CRITICAL} | {item for item in self.__dict__.values() if isinstance(item, NamedLevel)}

    def __setattr__(self, name, value):
        if isinstance(value, NamedLevel) and value not in self.named_levels:
            value.name = name
        super(LevelHandler, self).__setattr__(name, value)


level = LevelHandler()


# Syslog handling
#

class SyslogHandler(logging.Handler):
    priority_map = {logging.DEBUG:    syslog.LOG_DEBUG,
                    logging.INFO:     syslog.LOG_INFO,
                    logging.WARNING:  syslog.LOG_WARNING,
                    logging.ERROR:    syslog.LOG_ERR,
                    logging.CRITICAL: syslog.LOG_CRIT}

    def __init__(self, name, facility=syslog.LOG_DAEMON):
        logging.Handler.__init__(self)
        syslog.openlog(name, syslog.LOG_PID, facility)

    def close(self):
        syslog.closelog()
        logging.Handler.close(self)

    def emit(self, record):
        # noinspection PyBroadException
        try:
            priority = self.priority_map.get(record.levelno, syslog.LOG_INFO)
            message = self.format(record)
            if isinstance(message, unicode):
                message = message.encode('UTF-8')
            for line in message.rstrip().replace('\0', '#000').split('\n'):  # syslog.syslog() raises TypeError if null bytes are present in the message
                syslog.syslog(priority, line)
        except Exception:
            self.handleError(record)


# noinspection PyMethodMayBeStatic
class StandardIOLogger(io.IOBase):
    softspace = 0

    def __init__(self, logger, encoding='UTF-8'):
        super(StandardIOLogger, self).__init__()
        self._logger = logger
        self._encoding = encoding or sys.getdefaultencoding()
        self._buffer = ''

    @property
    def name(self):
        return '<{0.__class__.__name__} ({0._encoding})>'.format(self)

    @property
    def mode(self):
        return 'w'

    @property
    def encoding(self):
        return self._encoding

    @property
    def newlines(self):
        return None

    @property
    def errors(self):
        return None

    def read(self, size=None):
        raise io.UnsupportedOperation('read')

    def readinto(self, buf):
        raise io.UnsupportedOperation('readinto')

    def writable(self):
        return True

    def write(self, string):
        self._checkClosed()
        if isinstance(string, unicode):
            string = string.encode(self._encoding)
        lines = (self._buffer + string).split('\n')
        self._buffer = lines[-1]
        for line in lines[:-1]:
            self._logger(line)

    def writelines(self, lines):
        self._checkClosed()
        for line in lines:
            if isinstance(line, unicode):
                line = line.encode(self._encoding)
            self._logger(line)


class IfNotInteractive(object):
    """True when running under a non-interactive interpreter and False otherwise"""

    def __nonzero__(self):
        return sys.argv[0] is not ''

    def __repr__(self):
        return self.__class__.__name__


IfNotInteractive = IfNotInteractive()


def capture_output(capture_stdout=IfNotInteractive, capture_stderr=IfNotInteractive):
    sys.stdout = StandardIOLogger(root_logger.info) if capture_stdout else sys.__stdout__
    sys.stderr = StandardIOLogger(root_logger.error) if capture_stderr else sys.__stderr__


def set_handler(handler):
    for old_handler in root_logger.handlers[:]:
        root_logger.removeHandler(old_handler)
    handler.setFormatter(_default_formatter)
    root_logger.addHandler(handler)


def use_syslog(name=sys.argv[0] or 'python-app', facility=syslog.LOG_DAEMON, capture_stdout=IfNotInteractive, capture_stderr=IfNotInteractive):
    if syslog is Null:
        raise RuntimeError("syslog is not available on this platform")
    set_handler(SyslogHandler(name, facility))
    capture_output(capture_stdout, capture_stderr)


def start_syslog(*args, **kw):
    try:
        use_syslog(*args, **kw)
    finally:
        # emit the warning after setting up syslog, else the warning will most likely go to /dev/null, considering that start_syslog is usually called after forking
        warnings.warn('start_syslog is deprecated and should be replaced with use_syslog', category=DeprecationWarning, stacklevel=2)

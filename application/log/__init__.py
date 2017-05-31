
"""Application logging system for standard output/error and syslog"""

import sys
import logging

from application.log.extensions import twisted
from application.python import Null


__all__ = ['level', 'info', 'warning', 'debug', 'error', 'critical', 'exception', 'msg', 'warn', 'fatal', 'err', 'start_syslog']


try:
    import syslog
except ImportError:
    syslog = Null


class IfNotInteractive(object):
    """True when running under a non-interactive interpreter and False otherwise"""
    def __nonzero__(self):
        return sys.argv[0] is not ''

    def __repr__(self):
        return self.__class__.__name__

IfNotInteractive = IfNotInteractive()


def info(message, **context):
    logging.info(message, extra=context)


def warning(message, **context):
    logging.warning(message, extra=context)


def debug(message, **context):
    logging.debug(message, extra=context)


def error(message, **context):
    logging.error(message, extra=context)


def critical(message, **context):
    logging.critical(message, extra=context)


def exception(message=None, **context):
    logging.error(message, exc_info=1, extra=context)

# Some aliases that are commonly used
msg = info
warn = warning
fatal = critical
err = exception


class SimpleFormatter(logging.Formatter):
    def format(self, record):
        if not record.msg:
            message = ''
        elif record.levelno == level.INFO:
            message = record.getMessage()
        else:
            prefix = NamedLevel(record.levelno).prefix
            message = '\n'.join(l.rstrip() and (prefix+l) or l for l in record.getMessage().split('\n'))
        if record.exc_info:
            # Cache the traceback text to avoid converting it multiple times
            # (it's constant anyway)
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            if not record.msg:
                message = record.exc_text
            else:
                if message[-1:] != "\n":
                    message += "\n"
                message += record.exc_text
        return message


class SyslogHandler(logging.Handler):
    priority_map = {logging.DEBUG:    syslog.LOG_DEBUG,
                    logging.INFO:     syslog.LOG_INFO,
                    logging.WARNING:  syslog.LOG_WARNING,
                    logging.ERROR:    syslog.LOG_ERR,
                    logging.CRITICAL: syslog.LOG_CRIT}

    def __init__(self, prefix, facility=syslog.LOG_DAEMON):
        logging.Handler.__init__(self)
        syslog.openlog(prefix, syslog.LOG_PID, facility)

    def close(self):
        syslog.closelog()
        logging.Handler.close(self)

    def emit(self, record):
        priority = self.priority_map.get(record.levelno, syslog.LOG_INFO)
        message = self.format(record)
        if isinstance(message, unicode):
            message = message.encode('utf-8')
        for line in message.rstrip().split('\n'):
            syslog.syslog(priority, line)


class LoggingFile(object):
    closed = False
    encoding = 'UTF-8'
    mode = 'w'
    name = '<logging file>'
    newlines = None
    softspace = 0

    def __init__(self, logger):
        self.buf = ''
        self.logger = logger

    def write(self, data):
        if isinstance(data, unicode):
            data = data.encode(self.encoding)
        lines = (self.buf + data).split('\n')
        self.buf = lines[-1]
        for line in lines[:-1]:
            self.logger(line)

    def writelines(self, lines):
        for line in lines:
            if isinstance(line, unicode):
                line = line.encode(self.encoding)
            self.logger(line)

    def close(self): pass
    def flush(self): pass
    def fileno(self): return -1
    def isatty(self): return False
    def next(self): raise IOError("cannot read from log")
    def read(self): raise IOError("cannot read from log")
    def readline(self): raise IOError("cannot read from log")
    def readlines(self): raise IOError("cannot read from log")
    def readinto(self, buf): raise IOError("cannot read from log")
    def seek(self, offset, whence=0): raise IOError("cannot seek in log")
    def tell(self): raise IOError("log does not have position")
    def truncate(self, size=0): raise IOError("cannot truncate log")


def start_syslog(prefix='python-app', facility=syslog.LOG_DAEMON, capture_stdout=IfNotInteractive, capture_stderr=IfNotInteractive):
    if syslog is Null:
        raise RuntimeError("syslog is not available on this platform")
    logger = logging.getLogger()
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    handler = SyslogHandler(prefix, facility)
    handler.setFormatter(SimpleFormatter())
    logger.addHandler(handler)
    if capture_stdout:
        sys.stdout = LoggingFile(info)
    if capture_stderr:
        sys.stderr = LoggingFile(error)

handler = logging.StreamHandler()
handler.setFormatter(SimpleFormatter())
logger = logging.getLogger()
logger.addHandler(handler)


class NamedLevel(int):
    _level_instances = {}

    def __new__(cls, value, name=None, prefix=''):
        if value in cls._level_instances:
            return cls._level_instances[value]
        instance = int.__new__(cls, value)
        instance.name = name or ('LEVEL%02d' % value)
        instance.prefix = prefix
        cls._level_instances[value] = instance
        return instance

    def __init__(self, *args, **kw):
        super(NamedLevel, self).__init__()

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name

    def __format__(self, fmt):
        if fmt.endswith('s'):
            return self.name.__format__(fmt)
        else:
            return super(NamedLevel, self).__format__(fmt)


class CurrentLevelDescriptor(object):
    def __init__(self, value):
        self.value = value
        logging.getLogger().setLevel(value)

    def __get__(self, obj, owner):
        return self.value

    def __set__(self, obj, value):
        self.value = value
        logging.getLogger().setLevel(value)


class LevelClass(object):
    ALL      = NamedLevel(logging.NOTSET,   name='ALL')
    NONE     = NamedLevel(sys.maxint,       name='NONE')
    
    DEBUG    = NamedLevel(logging.DEBUG,    name='DEBUG',    prefix='debug: ')
    INFO     = NamedLevel(logging.INFO,     name='INFO',     prefix='')
    WARNING  = NamedLevel(logging.WARNING,  name='WARNING',  prefix='warning: ')
    ERROR    = NamedLevel(logging.ERROR,    name='ERROR',    prefix='error: ')
    CRITICAL = NamedLevel(logging.CRITICAL, name='CRITICAL', prefix='fatal error: ')

    current  = CurrentLevelDescriptor(INFO)

level = LevelClass()
del LevelClass, CurrentLevelDescriptor, IfNotInteractive


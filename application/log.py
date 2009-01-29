# Copyright (C) 2006-2009 Dan Pascu. See LICENSE for details.
#

"""Application logging system for stdout/stderr and syslog"""

__all__ = ['msg', 'err', 'info', 'warn', 'debug', 'error', 'fatal', 'startSyslog']

import sys
import syslog

try:
    from twisted.python import log
except ImportError:
    # Twisted is not available. Use the logging module to implement our functionality
    import logging
    
    def info(message, **context):
        logging.info(message)
    msg = info
    
    def warn(message, **context):
        logging.warning(message)
    
    def debug(message, **context):
        logging.debug(message)
    
    def error(message, **context):
        logging.error(message)
    
    def fatal(message, **context):
        logging.critical(message)
    
    def err(exception=None, **context):
        logging.exception(None)
    
    class LoggingFile(object):
        closed = False
        encoding = 'UTF-8'
        mode = 'w'
        name = '<logging file>'
        newlines = None
        softspace = 0
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
        def __init__(self, logger):
            self.buf = ''
            self.logger = logger
        def write(self, data):
            lines = (self.buf + data).split('\n')
            self.buf = lines[-1]
            for line in lines[:-1]:
                self.logger(line)
        def writelines(self, lines):
            for line in lines:
                self.logger(line)
    
    class SimpleFormatter(logging.Formatter):
        def format(self, record):
            if not record.msg:
                message = ''
            elif record.levelno == logging.INFO:
                message = record.getMessage()
            else:
                prefix = record.levelname.lower() + ': '
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
                        logging.WARN:     syslog.LOG_WARNING,
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
            for line in self.format(record).rstrip().split('\n'):
                syslog.syslog(priority, line)
    
    def startSyslog(prefix='python-app', facility=syslog.LOG_DAEMON, setStdout=True):
        logger = logging.getLogger()
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        handler = SyslogHandler(prefix, facility)
        handler.setFormatter(SimpleFormatter())
        logger.addHandler(handler)
        if setStdout:
            sys.stdout = LoggingFile(info)
            sys.stderr = LoggingFile(error)
    
    handler = logging.StreamHandler()
    handler.setFormatter(SimpleFormatter())
    logger = logging.getLogger()
    logger.setLevel(logging.NOTSET)
    logger.addHandler(handler)

else:
    # Twisted is available. Use the twisted.log module to implement our functionality
    
    msg = log.msg
    err = log.err
    
    info = msg
    
    def warn(message, **kwargs):
        context = kwargs.copy()
        context['prefix'] = 'warning: '
        context['syslog_priority'] = syslog.LOG_WARNING
        msg(message, **context)
    
    def debug(message, **kwargs):
        context = kwargs.copy()
        context['debug'] = True
        context['syslog_priority'] = syslog.LOG_DEBUG
        msg(message, **context)
    
    def error(message, **kwargs):
        context = kwargs.copy()
        context['prefix'] = 'error: '
        context['syslog_priority'] = syslog.LOG_ERR
        msg(message, **context)
    
    def fatal(message, **kwargs):
        context = kwargs.copy()
        context['prefix'] = 'fatal error: '
        context['syslog_priority'] = syslog.LOG_CRIT
        msg(message, **context)
    
    class SimpleObserver(log.DefaultObserver):
        """
        Send all error messages to sys.stderr and other messages to sys.stdout
        Will be removed when startLogging() is called for the first time.
        Used to overwrite the twisted DefaultObserver which only logs errors
        """
        def _emit(self, eventDict):
            if eventDict['isError']:
                if eventDict.has_key('failure'):
                    text = eventDict['failure'].getTraceback()
                else:
                    text = ' '.join([str(m) for m in eventDict['message']]) + '\n'
                sys.stderr.write(text)
                sys.stderr.flush()
            else:
                text = ' '.join([str(m) for m in eventDict['message']]) + '\n'
                sys.stdout.write(text)
                sys.stdout.flush()
    
    class SyslogObserver:
        def __init__(self, prefix, facility=syslog.LOG_DAEMON):
            syslog.openlog(prefix, syslog.LOG_PID, facility)
        def emit(self, eventDict):
            edm = eventDict['message']
            if not edm:
                if eventDict['isError'] and eventDict.has_key('failure'):
                    text = eventDict['failure'].getTraceback()
                elif eventDict.has_key('format'):
                    text = eventDict['format'] % eventDict
                else:
                    # we don't know how to log this
                    return
            else:
                text = ' '.join([str(m) for m in edm])
            prefix = eventDict.get('prefix', '')
            priority = eventDict.get('syslog_priority', syslog.LOG_INFO)
            for line in text.rstrip().split('\n'):
                syslog.syslog(priority, '[%s] %s%s' % (eventDict['system'], prefix, line))
    
    def startSyslog(prefix='python-app', facility=syslog.LOG_DAEMON, setStdout=True):
        obs = SyslogObserver(prefix, facility)
        log.startLoggingWithObserver(obs.emit, setStdout=setStdout)
    
    # Overwrite the twisted DefaultObserver with our SimpleObserver
    #
    if log.defaultObserver is not None:
        log.defaultObserver.stop()
        log.defaultObserver = SimpleObserver()
        log.defaultObserver.start()


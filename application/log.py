# Copyright (C) 2006-2007 Dan Pascu. See LICENSE for details.
#

"""Application logging system for stdout/stderr and syslog"""

__all__ = ['msg', 'err', 'info', 'warn', 'debug', 'error', 'fatal', 'startSyslog']

import sys
import syslog
from twisted.python import log

msg = log.msg
err = log.err

info = msg

def warn(message, **kwargs):
    context = kwargs.copy()
    context['prefix'] = 'warning: '
    msg(message, **context)

def debug(message, **kwargs):
    context = kwargs.copy()
    context['debug'] = True
    msg(message, **context)

def error(message, **kwargs):
    context = kwargs.copy()
    context['prefix'] = 'error: '
    msg(message, **context)

def fatal(message, **kwargs):
    context = kwargs.copy()
    context['prefix'] = 'fatal error: '
    msg(message, **context)


class SimpleObserver(log.DefaultObserver):
    """Simple observer.

    Will send all error messages to sys.stderr and other messages to sys.stdout
    Will be removed when startLogging() is called for the first time.
    Used to overwrite the twisted DefaultObserver which only logs errors
    """

    def _emit(self, eventDict):
        #sys.stdout.write(str(eventDict))
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

        lines = text.split('\n')
        while lines[-1:] == ['']:
            lines.pop()

        for line in lines:
            syslog.syslog('[%s] %s%s' % (eventDict['system'], prefix, line))


def startSyslog(prefix='python-app', facility=syslog.LOG_DAEMON, setStdout=True):
    obs = SyslogObserver(prefix, facility)
    log.startLoggingWithObserver(obs.emit, setStdout=setStdout)


##
## Overwrite the twisted DefaultObserver with our SimpleObserver
##

if log.defaultObserver is not None:
    log.defaultObserver.stop()
    log.defaultObserver = SimpleObserver()
    log.defaultObserver.start()


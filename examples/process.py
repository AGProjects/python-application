#!/usr/bin/python

"""Example of controlling the process behavior using the process module"""

# This example also shows how to use the log module for logging

import os
import sys
import time
import signal

from application import log
from application.process import process, ProcessError


# Some signal handlers
def signal_handler(*args):
    """A sample signal handler"""
    log.info("first handler received signal %s" % args[0])


def signal_handler2(*args):
    """Another sample signal handler"""
    log.info("second handler received signal %s" % args[0])


# The application name.
name = 'process-example'

# Set the process runtime directory. This is where the pid file and other
# process runtime related files will be created. The default is /var/run
# but in this example we use /tmp because we need a place where we have
# write access even without running as root.
process.runtime_directory = '/tmp'

# These log lines will go to stdout.
log.info("Starting %s. Check syslog to see what's going on next." % name)
log.info("Use `watch -n .1 ls /tmp' to see how the pid file is created and deleted.")

# Set the process to run in the background and create a pid file.
# If daemonize is called without arguments or pidfile is None no pid file
# will be created.
pidfile = process.runtime_file('%s.pid' % name)
try:
    process.daemonize(pidfile)
except ProcessError as e:
    log.fatal(e)
    sys.exit(1)

# process was successfully put in the background. Redirect logging to syslog
log.use_syslog(name)

# This log line will go to syslog
log.info('application started (running in the background)')

# Add a signal handler for SIGUSR1
process.signals.add_handler(signal.SIGUSR1, signal_handler)
# Add another signal handler for SIGUSR1. Multiple handlers can be added
# for a given signal by different components/modules/threads of the
# application. The only limitation is that the first handler must be added
# from the main thread.
process.signals.add_handler(signal.SIGUSR1, signal_handler2)

log.info("sending SIGUSR1 to self")
os.kill(os.getpid(), signal.SIGUSR1)
log.info("sleeping for 3 seconds")
time.sleep(3)

# Simulate some error
try:
    # noinspection PyUnresolvedReferences
    bar = foo
except NameError as e:
    # Log an error message and the backtrace
    log.exception("cannot access foo: %s" % e)

log.info("program done, exiting")

# Copyright (C) 2006-2009 Dan Pascu. See LICENSE for details.
#

"""UNIX process and signal management"""

import sys
import os
import errno
import signal
import atexit

from application import log
from application.python.types import Singleton

try:
    set
except NameError:
    from sets import Set as set


class ProcessError(Exception): pass


class Process(object):
    """Control how the current process runs and interacts with the operating system"""

    __metaclass__ = Singleton

    def __init__(self):
        self._daemon = False
        self._pidfile = None
        self.signals = Signals()
        self._runtime_directory = '/var/run'
        self._system_config_directory = '/etc'
        self._local_config_directory = os.path.realpath(os.path.dirname(sys.argv[0]))

    def _get_local_config_directory(self):
        return self._local_config_directory

    def _set_local_config_directory(self, path):
        self._local_config_directory = os.path.realpath(path)

    local_config_directory = property(_get_local_config_directory, _set_local_config_directory)

    def _get_system_config_directory(self):
        return self._system_config_directory

    def _set_system_config_directory(self, path):
        self._system_config_directory = os.path.realpath(path)

    system_config_directory = property(_get_system_config_directory, _set_system_config_directory)

    def _get_runtime_directory(self):
        return self._runtime_directory

    def _set_runtime_directory(self, path):
        path = os.path.realpath(path)
        if not os.path.isdir(path):
            try:
                os.makedirs(path)
            except OSError, e:
                raise ProcessError("cannot set runtime directory to %s: %s" % (path, e.args[1]))
        if not os.access(path, os.X_OK | os.W_OK):
            raise ProcessError("runtime directory %s is not writable" % path)
        self._runtime_directory = path

    runtime_directory = property(_get_runtime_directory, _set_runtime_directory)

    def _check_if_running(self):
        """Check if the process is already running"""
        pidfile = self._pidfile
        if pidfile is None or not os.path.isfile(pidfile):
            return
        try:
            pf = open(pidfile, 'rb')
        except IOError, why:
            raise ProcessError, "unable to open pidfile %s: %s" % (pidfile, str(why))
        else:
            try:
                try:
                    pid = int(pf.readline().strip())
                except IOError, why:
                    raise ProcessError, "unable to read pidfile %s: %s" % (pidfile, str(why))
                except ValueError:
                    pass
                else:
                    ## Check if the process identified by pid is running
                    ## Send the process a signal of zero (0)
                    try:
                        os.kill(pid, 0)
                    except OSError, why:
                        if why[0] in (errno.EPERM, errno.EACCES):
                            raise ProcessError, "already running with pid %d" % pid
                    else:
                        raise ProcessError, "already running with pid %d" % pid
            finally:
                pf.close()

    def _do_fork(self):
        """Perform the Unix double fork"""
        ## First fork.
        ## This will return control to the command line/shell that invoked us and
        ## will guarantee that the forked child will not be a process group leader
        ## (which is required for setsid() below to succeed).
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0) ## exit parent
                #os._exit(0)
        except OSError, e:
            raise ProcessError, "fork #1 failed: %d: %s" % (e.errno, e.strerror)
        
        ## Decouple from the controling terminal.
        ## Calling setsid() we become a process group and session group leader.
        ## Since a controlling terminal is associated with a session, and this
        ## new session has not yet acquired a controlling terminal our process
        ## now has no controlling terminal, which is a Good Thing for daemons.
        os.setsid()
        
        ## Second fork
        ## This will allow the parent (the session group leader obtained above)
        ## to exit. This means that the child, as a non-session group leader,
        ## can never regain a controlling terminal.
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0) ## exit 1st child too
                #os._exit(0)
        except OSError, e:
            raise ProcessError, "fork #2 failed: %d: %s" % (e.errno, e.strerror)
        
        ## Setup our environment.
        ## Change working directory to / so we do not keep any directory in use
        ## preventing them from being unmounted. Also set file creation mask.
        os.chdir("/")
        os.umask(022)

    def _make_pidfile(self):
        """Create the pidfile if defined"""
        if not self._pidfile:
            return
        try:
            pf = open(self._pidfile, "wb")
            try:
                pf.write("%s\n" % os.getpid())
            finally:
                pf.close()
        except IOError, e:
            raise ProcessError, "unable to write pidfile %s: %s" % (self._pidfile, str(e))

    def _redirect_stdio(self):
        """Redirect stdin, stdout and stderr to /dev/null"""
        sys.stdout.flush()
        sys.stderr.flush()
        null = os.open('/dev/null', os.O_RDWR)
        os.dup2(null, sys.stdin.fileno())
        os.dup2(null, sys.stdout.fileno())
        os.dup2(null, sys.stderr.fileno())
        os.close(null)

    def _setup_signal_handlers(self):
        """Setup the signal handlers for daemon mode"""
        signals = self.signals
        ## Ignore Terminal I/O Signals
        if hasattr(signal, 'SIGTTOU'):
            signals.ignore(signal.SIGTTOU)
        if hasattr(signal, 'SIGTTIN'):
            signals.ignore(signal.SIGTTIN)
        if hasattr(signal, 'SIGTSTP'):
            signals.ignore(signal.SIGTSTP)
        ## Ignore USR signals
        if hasattr(signal, 'SIGUSR1'):
            signals.ignore(signal.SIGUSR1)
        if hasattr(signal, 'SIGUSR2'):
            signals.ignore(signal.SIGUSR2)

    def __on_exit(self):
        if self._pidfile:
            try:
                os.unlink(self._pidfile)
            except OSError, why:
                log.warn("unable to delete pidfile %s: %s" % (self._pidfile, str(why)))

    def daemonize(self, pidfile=None):
        """Detach from terminal and run in the background"""
        if self._daemon:
            raise ProcessError('already in daemon mode')
        self._daemon = True
        if pidfile:
            self._pidfile = self.runtime_file(pidfile)
        self._check_if_running()
        self._do_fork()
        self._make_pidfile()
        self._redirect_stdio()
        self._setup_signal_handlers()
        atexit.register(self.__on_exit)

    def get_config_directories(self):
        """Return a tuple containing the system and local config directories."""
        return (self._system_config_directory, self._local_config_directory)

    def config_file(self, name):
        """Return a config file name. Lookup order: name if absolute, local_dir/name, system_dir/name, None if none found"""
        path = os.path.realpath(os.path.join(self._local_config_directory, name))
        if os.path.isfile(path) and os.access(path, os.R_OK):
            return path
        path = os.path.realpath(os.path.join(self._system_config_directory, name))
        if os.path.isfile(path) and os.access(path, os.R_OK):
            return path
        return None

    def runtime_file(self, name):
        """Return a runtime file name (prepends runtime_directory if defined and name is not absolute, else name)."""
        if name is None:
            return None
        if self.runtime_directory is not None:
            return os.path.realpath(os.path.join(self.runtime_directory, name))
        else:
            return os.path.realpath(name)


class Signals(object):
    """Interface to the system signals"""

    __metaclass__ = Singleton
    
    def __init__(self):
        self._handlers = {}
        if not hasattr(signal, '_original_signal'):
            signal._original_signal = signal.signal

    def __dispatcher(self, signum, frame):
        for handler in self._handlers.get(signum, []):
            handler(signum, frame)

    def add_handler(self, signum, sighandler):
        """Add handler to handler list for signal"""
        if not callable(sighandler):
            raise RuntimeError("signal handler needs to be a callable")
        self._handlers.setdefault(signum, set()).add(sighandler)
        if signal.getsignal(signum) != self.__dispatcher:
            signal._original_signal(signum, self.__dispatcher)

    def ignore(self, signum):
        """Ignore signal"""
        signal._original_signal(signum, signal.SIG_IGN)
        try:
            del self._handlers[signum]
        except KeyError:
            pass

    def default_handler(self, signum):
        """Use default handler for signal"""
        signal._original_signal(signum, signal.SIG_DFL)
        try:
            del self._handlers[signum]
        except KeyError:
            pass

    def steal_handlers(self, enable):
        """Replace signal() from the signal module with add_handler()"""
        if enable:
            signal.signal = self.add_handler
        else:
            signal.signal = signal._original_signal


process = Process()



"""UNIX process and signal management"""

import sys
import os
import time
import errno
import signal
import atexit
import __main__

from application import log
from application.python.types import Singleton
from application.system import host


__all__ = 'Process', 'ProcessError', 'Signals', 'process'


class ProcessError(Exception):
    pass


class Process(object):
    """Control how the current process runs and interacts with the operating system"""

    __metaclass__ = Singleton

    def __init__(self):
        self._daemon = False
        self._pidfile = None
        self.signals = Signals()
        self._runtime_directory = os.path.realpath('/var/run')
        self._system_config_directory = os.path.realpath('/etc')
        self._local_config_directory = os.path.dirname(os.path.realpath(getattr(__main__, '__file__', sys.executable if hasattr(sys, 'frozen') else 'none')))

    @property
    def daemon(self):
        return self._daemon

    @property
    def local_config_directory(self):
        return self._local_config_directory

    @local_config_directory.setter
    def local_config_directory(self, path):
        self._local_config_directory = os.path.realpath(path)

    @property
    def system_config_directory(self):
        return self._system_config_directory

    @system_config_directory.setter
    def system_config_directory(self, path):
        self._system_config_directory = os.path.realpath(path)

    @property
    def runtime_directory(self):
        return self._runtime_directory

    @runtime_directory.setter
    def runtime_directory(self, path):
        path = os.path.realpath(path)
        if not os.path.isdir(path):
            try:
                os.makedirs(path)
            except OSError as e:
                raise ProcessError('cannot set runtime directory to %s: %s' % (path, e.strerror))
        if not os.access(path, os.X_OK | os.W_OK):
            raise ProcessError('runtime directory %s is not writable' % path)
        self._runtime_directory = path

    def _check_if_running(self):
        pidfile = self._pidfile
        if pidfile is None or not os.path.isfile(pidfile):
            return
        try:
            pf = open(pidfile, 'rb')
        except IOError as e:
            raise ProcessError('unable to open pidfile %s: %s' % (pidfile, e))
        else:
            try:
                try:
                    pid = int(pf.readline().strip())
                except IOError as e:
                    raise ProcessError('unable to read pidfile %s: %s' % (pidfile, e))
                except ValueError:
                    pass
                else:
                    # Check if the process identified by pid is running
                    # Send the process a signal of zero (0)
                    try:
                        os.kill(pid, 0)
                    except OSError as e:
                        if e.errno in (errno.EPERM, errno.EACCES):
                            raise ProcessError('already running with pid %d' % pid)
                    else:
                        raise ProcessError('already running with pid %d' % pid)
            finally:
                pf.close()

    @staticmethod
    def _do_fork():
        # Perform the Unix double fork

        # First fork.
        # This will return control to the command line/shell that invoked us and
        # will guarantee that the forked child will not be a process group leader
        # (which is required for setsid() below to succeed).
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)  # exit parent
                # os._exit(0)
        except OSError as e:
            raise ProcessError('fork #1 failed: %d: %s' % (e.errno, e.strerror))
        
        # Decouple from the controlling terminal.
        # Calling setsid() we become a process group and session group leader.
        # Since a controlling terminal is associated with a session, and this
        # new session has not yet acquired a controlling terminal our process
        # now has no controlling terminal, which is a Good Thing for daemons.
        os.setsid()
        
        # Second fork
        # This will allow the parent (the session group leader obtained above)
        # to exit. This means that the child, as a non-session group leader,
        # can never regain a controlling terminal.
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)  # exit 1st child too
                # os._exit(0)
        except OSError as e:
            raise ProcessError('fork #2 failed: %d: %s' % (e.errno, e.strerror))
        
        # Setup our environment.
        # Change working directory to / so we do not keep any directory in use
        # preventing them from being unmounted. Also set file creation mask.
        os.chdir('/')
        os.umask(0o022)

    def _make_pidfile(self):
        if not self._pidfile:
            return
        try:
            with open(self._pidfile, 'wb') as pf:
                pf.write('%s\n' % os.getpid())
        except IOError as e:
            raise ProcessError('unable to write pidfile %s: %s' % (self._pidfile, e))

    @staticmethod
    def _redirect_stdio():
        # Redirect standard input, standard output and standard error to /dev/null
        sys.stdout.flush()
        sys.stderr.flush()
        null = os.open('/dev/null', os.O_RDWR)
        os.dup2(null, sys.stdin.fileno())
        os.dup2(null, sys.stdout.fileno())
        os.dup2(null, sys.stderr.fileno())
        os.close(null)

    def _setup_signal_handlers(self):
        signals = self.signals
        # Ignore Terminal I/O Signals
        if hasattr(signal, 'SIGTTOU'):
            signals.ignore(signal.SIGTTOU)
        if hasattr(signal, 'SIGTTIN'):
            signals.ignore(signal.SIGTTIN)
        if hasattr(signal, 'SIGTSTP'):
            signals.ignore(signal.SIGTSTP)
        # Ignore USR signals
        if hasattr(signal, 'SIGUSR1'):
            signals.ignore(signal.SIGUSR1)
        if hasattr(signal, 'SIGUSR2'):
            signals.ignore(signal.SIGUSR2)

    def __on_exit(self):
        if self._pidfile:
            try:
                os.unlink(self._pidfile)
            except OSError as e:
                log.warning('unable to delete pidfile %s: %s' % (self._pidfile, e))

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
        return self._system_config_directory, self._local_config_directory

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

    @staticmethod
    def wait_for_network(wait_time=10, wait_message=None, test_ip='1.2.3.4'):
        """
        Make sure the network is available and can be reached. The function
        will return as soon as the network is reachable or it will raise
        RuntimeError if network is still unreachable after wait_time. The
        default value for test_ip checks if internet is reachable. Optionally
        it can log wait_message at INFO level if the function needs to wait.
        """
        for step in range(wait_time):
            local_ip = host.outgoing_ip_for(test_ip)
            if local_ip is not None:
                break
            elif step == 0 and wait_message is not None:
                log.info(wait_message)
            time.sleep(1)
        else:
            raise RuntimeError('Network is not available after waiting for {} seconds'.format(wait_time))


class Signals(object):
    """Interface to the system signals"""

    __metaclass__ = Singleton
    
    def __init__(self):
        self._handlers = {}
        self._original_signal = signal.signal

    def __dispatcher(self, signum, frame):
        for handler in self._handlers.get(signum, []):
            handler(signum, frame)

    def add_handler(self, signum, handler):
        """Add handler to handler list for signal"""
        if not callable(handler):
            raise RuntimeError('signal handler needs to be a callable')
        self._handlers.setdefault(signum, set()).add(handler)
        if signal.getsignal(signum) != self.__dispatcher:
            self._original_signal(signum, self.__dispatcher)

    def ignore(self, signum):
        """Ignore signal"""
        self._original_signal(signum, signal.SIG_IGN)
        self._handlers.pop(signum, None)

    def default_handler(self, signum):
        """Use default handler for signal"""
        self._original_signal(signum, signal.SIG_DFL)
        self._handlers.pop(signum, None)

    def steal_handlers(self, enable):
        """Replace signal() from the signal module with add_handler()"""
        if enable:
            signal.signal = self.add_handler
        else:
            signal.signal = self._original_signal


process = Process()

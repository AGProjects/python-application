
"""UNIX process and signal management"""

import __main__
import atexit
import errno
import os
import signal
import sys
import time

from application import log
from application.python.types import Singleton
from application.system import host


__all__ = 'Process', 'ProcessError', 'Signals', 'process'


class ProcessError(Exception):
    pass


# noinspection PyProtectedMember
class DirectoryAttribute(object):
    def __init__(self, type_name=None):
        self.type = type_name
        self.name = '_'.join(part for part in (type_name, 'directory') if part)
        self.root = '_'.join(part for part in (type_name, 'root') if part)

    def __get__(self, instance, owner):
        if instance is None:
            return self
        if self.name in instance.__dict__:
            return instance.__dict__[self.name]
        try:
            return instance._cache[self.name]
        except KeyError:
            root_directory = getattr(instance, self.root)
            if root_directory is None:
                directory = None
            elif self.type == 'local':
                directory = root_directory  # the local directory doesn't use the subdirectory
            else:
                directory = os.path.realpath(os.path.join(root_directory, instance.subdirectory or ''))
            return instance._cache.setdefault(self.name, directory)

    def __set__(self, instance, value):
        instance.__dict__[self.name] = os.path.realpath(value) if value is not None else None

    def __delete__(self, instance):
        try:
            del instance.__dict__[self.name]
        except KeyError:
            raise AttributeError(self.name)


class ConfigurationSettings(object):
    _cache_affecting_attributes = {'system_root', 'user_root', 'local_root', 'subdirectory'}
    _system_binary_directories = {'/bin', '/sbin', '/usr/bin', '/usr/sbin', '/usr/local/bin', '/usr/local/sbin'}

    system_directory = DirectoryAttribute('system')  # type: str
    user_directory = DirectoryAttribute('user')      # type: str
    local_directory = DirectoryAttribute('local')    # type: str

    def __init__(self):
        # the script directory (the current directory when running in interactive mode)
        script_directory = os.path.dirname(os.path.realpath(getattr(__main__, '__file__', sys.executable if hasattr(sys, 'frozen') else 'none')))
        self._cache = {}
        self.system_root = os.path.realpath('/etc')
        self.user_root = os.path.realpath(os.path.expanduser('~/.config'))
        self.local_root = script_directory if script_directory not in self._system_binary_directories else None
        self.subdirectory = None

    def __setattr__(self, name, value):
        super(ConfigurationSettings, self).__setattr__(name, value)
        if name in self._cache_affecting_attributes:
            self._cache.clear()

    @property
    def directories(self):
        return [directory for directory in (self.system_directory, self.user_directory, self.local_directory) if directory is not None]

    def file(self, name):
        for directory in reversed(self.directories):
            path = os.path.realpath(os.path.join(directory, name))
            if os.path.isfile(path) and os.access(path, os.R_OK):
                return path
        return None


class RuntimeSettings(object):
    _cache_affecting_attributes = {'root', 'subdirectory'}

    directory = DirectoryAttribute()  # type: str

    def __init__(self):
        self._cache = {}
        self.root = os.path.realpath('/var/run')
        self.subdirectory = None

    def __setattr__(self, name, value):
        super(RuntimeSettings, self).__setattr__(name, value)
        if name in self._cache_affecting_attributes:
            self._cache.clear()

    def file(self, name):
        if self.directory is not None:
            return os.path.realpath(os.path.join(self.directory, name))
        else:
            return None

    def create_directory(self):
        directory = self.directory
        if directory is None:
            raise ProcessError('runtime directory is not defined')
        if not os.path.exists(directory):
            try:
                os.makedirs(directory)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise ProcessError('cannot create runtime directory at %s: %s' % (directory, e.strerror))
        if not os.path.isdir(directory):
            raise ProcessError('the path at %s is not a directory' % directory)
        if not os.access(directory, os.R_OK | os.W_OK | os.X_OK):
            raise ProcessError('lacking permissions to access the runtime directory at %s' % directory)


class Process(object):
    """Control how the current process runs and interacts with the operating system"""

    __metaclass__ = Singleton

    def __init__(self):
        self._daemon = False
        self._pidfile = None
        self.configuration = ConfigurationSettings()
        self.runtime = RuntimeSettings()
        self.signals = Signals()

    @property
    def daemon(self):
        return self._daemon

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
        if os.path.dirname(self._pidfile) == self.runtime.directory:
            self.runtime.create_directory()
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
        """Detach from the terminal and run in the background"""
        if self._daemon:
            raise ProcessError('already in daemon mode')
        self._daemon = True
        if pidfile:
            self._pidfile = self.runtime.file(pidfile)
        self._check_if_running()
        self._do_fork()
        self._make_pidfile()
        self._redirect_stdio()
        self._setup_signal_handlers()
        atexit.register(self.__on_exit)

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

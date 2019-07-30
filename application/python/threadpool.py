
"""A generic, resizable thread pool"""

from Queue import Queue
from itertools import count
from threading import Lock, Thread, current_thread

from application import log
from application.python import limit
from application.python.decorator import decorator, preserve_signature


__all__ = 'ThreadPool', 'run_in_threadpool'


class CallFunctionEvent(object):
    __slots__ = 'function', 'args', 'kw'

    # noinspection PyShadowingBuiltins
    def __init__(self, function, args, kw):
        self.function = function
        self.args = args
        self.kw = kw


class ThreadPool(object):
    StopWorker = object()

    def __init__(self, name=None, min_threads=1, max_threads=10):
        assert 0 <= min_threads <= max_threads > 0, 'invalid bounds'
        self.name = name
        self._lock = Lock()
        self._queue = Queue()
        self._thread_id = None
        self._threads = []
        self._started = False
        self.__dict__['min_threads'] = min_threads
        self.__dict__['max_threads'] = max_threads
        self.__dict__['workers'] = 0
        self.__dict__['jobs'] = 0

    @property
    def min_threads(self):
        return self.__dict__['min_threads']

    @property
    def max_threads(self):
        return self.__dict__['max_threads']

    @property
    def workers(self):
        return self.__dict__['workers']

    @property
    def jobs(self):
        return self.__dict__['jobs']

    def start(self):
        with self._lock:
            if self._started:
                return
            self._started = True
            self._thread_id = count(1)
            needed_workers = limit(self.jobs, min=self.min_threads, max=self.max_threads)
            while self.workers < needed_workers:
                self._start_worker()

    def stop(self):
        with self._lock:
            if not self._started:
                return
            self._started = False
            threads = self._threads[:]
            while self.workers:
                self._stop_worker()
            for thread in threads:
                thread.join()
            self._thread_id = None

    def resize(self, min_threads=1, max_threads=10):
        assert 0 <= min_threads <= max_threads > 0, 'invalid bounds'
        with self._lock:
            self.__dict__['min_threads'] = min_threads
            self.__dict__['max_threads'] = max_threads
            if self._started:
                needed_workers = limit(self.jobs, min=min_threads, max=max_threads)
                while self.workers > max_threads:  # compare against needed_workers to compact or against max_threads to not
                    self._stop_worker()
                while self.workers < needed_workers:
                    self._start_worker()

    def compact(self):
        with self._lock:
            needed_workers = limit(self.jobs, min=self.min_threads, max=self.max_threads)
            while self.workers > needed_workers:
                self._stop_worker()

    def run(self, func, *args, **kw):
        with self._lock:
            self._queue.put(CallFunctionEvent(func, args, kw))
            self.__dict__['jobs'] += 1
            if self._started and self.workers < limit(self.jobs, max=self.max_threads):
                self._start_worker()

    def _start_worker(self):
        # Must be called with the lock held
        self.__dict__['workers'] += 1
        name = '%sThread-%s-%s' % (self.__class__.__name__, self.name or id(self), next(self._thread_id))
        thread = Thread(target=self._worker, name=name)
        self._threads.append(thread)
        thread.daemon = True
        thread.start()

    def _stop_worker(self):
        # Must be called with the lock held
        self._queue.put(self.StopWorker)
        self.__dict__['workers'] -= 1

    def _worker(self):
        thread = current_thread()
        while True:
            task = self._queue.get()
            if task is self.StopWorker:
                break
            # noinspection PyBroadException
            try:
                task.function(*task.args, **task.kw)
            except Exception:
                log.exception('Unhandled exception while calling %r in the %r thread' % (task.function, thread.name))
            finally:
                with self._lock:
                    self.__dict__['jobs'] -= 1
                del task
        self._threads.remove(thread)


@decorator
def run_in_threadpool(pool):
    def thread_decorator(func):
        @preserve_signature(func)
        def wrapper(*args, **kw):
            pool.run(func, *args, **kw)
        return wrapper
    return thread_decorator

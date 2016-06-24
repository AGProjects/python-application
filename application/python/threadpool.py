
"""A generic, resizable thread pool"""

from Queue import Queue
from threading import Lock, Thread, current_thread

from application import log
from application.python import limit
from application.python.decorator import decorator, preserve_signature


__all__ = ['ThreadPool', 'run_in_threadpool']


class CallFunctionEvent(object):
    __slots__ = 'function', 'args', 'kw'

    def __init__(self, function, args, kw):
        self.function = function
        self.args = args
        self.kw = kw


class ThreadPool(object):
    StopWorker = object()

    def __init__(self, name=None, min_threads=1, max_threads=10):
        self.name = name
        self._lock = Lock()
        self._queue = Queue()
        self._threads = []
        self._workers = 0
        self._jobs = 0
        self._started = False
        self._set_size(min_threads, max_threads)

    @property
    def min_threads(self):
        return self.__dict__['min_threads']

    @property
    def max_threads(self):
        return self.__dict__['max_threads']

    def start(self):
        with self._lock:
            if self._started:
                return
            self._started = True
            needed_workers = limit(self._jobs, min=self.min_threads, max=self.max_threads)
            while self._workers < needed_workers:
                self._start_worker()

    def stop(self):
        with self._lock:
            if not self._started:
                return
            self._started = False
            threads = self._threads[:]
            while self._workers:
                self._stop_worker()
            for thread in threads:
                thread.join()

    def resize(self, min_threads=1, max_threads=10):
        with self._lock:
            self._set_size(min_threads, max_threads)

    def compact(self):
        with self._lock:
            needed_workers = limit(self._jobs, min=self.min_threads, max=self.max_threads)
            while self._workers > needed_workers:
                self._stop_worker()

    def run(self, func, *args, **kw):
        with self._lock:
            self._queue.put(CallFunctionEvent(func, args, kw))
            self._jobs += 1
            if self._started and self._workers < limit(self._jobs, max=self.max_threads):
                self._start_worker()

    def _set_size(self, min_threads, max_threads):
        # Must be called with the lock held
        assert 0 <= min_threads <= max_threads > 0, "invalid bounds"

        self.__dict__['min_threads'] = min_threads
        self.__dict__['max_threads'] = max_threads

        if self._started:
            needed_workers = limit(self._jobs, min=min_threads, max=max_threads)
            while self._workers > max_threads:
                self._stop_worker()
            while self._workers < needed_workers:
                self._start_worker()

    def _start_worker(self):
        # Must be called with the lock held
        self._workers += 1
        name = "%sThread-%s-%s" % (self.__class__.__name__, self.name or id(self), self._workers)
        thread = Thread(target=self._worker, name=name)
        self._threads.append(thread)
        thread.daemon = True
        thread.start()

    def _stop_worker(self):
        # Must be called with the lock held
        self._queue.put(self.StopWorker)
        self._workers -= 1

    def _worker(self):
        thread = current_thread()
        while True:
            task = self._queue.get()
            if task is self.StopWorker:
                break
            try:
                task.function(*task.args, **task.kw)
            except:
                log.exception('Exception occurred while calling %r in the %r thread' % (task.function, thread.name))
            finally:
                with self._lock:
                    self._jobs -= 1
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


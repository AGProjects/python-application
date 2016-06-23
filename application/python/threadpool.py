
"""A generic, resizable thread pool"""

from Queue import Queue
from threading import Lock, Thread, current_thread

from application import log
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
            self._set_size(self.min_threads, self.max_threads)

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
            while self._workers > self.min_threads:
                self._stop_worker()

    def run(self, func, *args, **kw):
        with self._lock:
            self._queue.put(CallFunctionEvent(func, args, kw))
            if self._started:
                self._maybe_start_workers()

    def _set_size(self, min, max):
        # Must be called with the lock held
        assert 0 <= min <= max, "invalid bounds"

        self.__dict__['min_threads'] = min
        self.__dict__['max_threads'] = max

        if not self._started:
            return

        while self._workers > max:
            self._stop_worker()
        while self._workers < min:
            self._start_worker()

        self._maybe_start_workers()

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

    def _maybe_start_workers(self):
        # Must be called with the lock held
        needed = self._queue.qsize() + self._workers
        while self._workers < min(self.max_threads, needed):
            self._start_worker()

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


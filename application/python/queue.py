
"""Event processing queues, that process the events in a distinct thread"""

import Queue
from threading import Thread, Event, Lock

from application import log
from application.python.types import MarkerType


__all__ = 'EventQueue', 'CumulativeEventQueue'


# Special events that control the queue operation (for internal use)

class StopProcessing: __metaclass__ = MarkerType
class ProcessEvents:  __metaclass__ = MarkerType
class DiscardEvents:  __metaclass__ = MarkerType


class EventQueue(Thread):
    """Simple event processing queue that processes one event at a time"""

    def __init__(self, handler, name=None, preload=()):
        if not callable(handler):
            raise TypeError('handler should be a callable')
        Thread.__init__(self, name=name or self.__class__.__name__)
        self.setDaemon(True)
        self._exit = Event()
        self._active = Event()
        self._pause_counter = 0
        self._pause_lock = Lock()
        self._accepting_events = True
        self.queue = Queue.Queue()
        self.handle = handler
        self.load(preload)
        self._active.set()

    def run(self):
        """Run the event queue processing loop in its own thread"""
        while not self._exit.isSet():
            self._active.wait()
            event = self.queue.get()
            if event is StopProcessing:
                break
            # noinspection PyBroadException
            try:
                self.handle(event)
            except Exception:
                log.exception('Unhandled exception during event handling')
            finally:
                del event  # do not reference this event until the next event arrives, in order to allow it to be released

    def stop(self, force_exit=False):
        """Terminate the event processing loop/thread (force_exit=True skips processing events already on queue)"""
        if force_exit:
            self._exit.set()
        self.queue.put(StopProcessing)
        # resume processing in case it is paused
        with self._pause_lock:
            self._pause_counter = 0
            self._active.set()

    def pause(self):
        """Pause processing events"""
        with self._pause_lock:
            self._pause_counter += 1
            self._active.clear()

    def unpause(self):
        """Resume processing events"""
        with self._pause_lock:
            if self._pause_counter == 0:
                return  # already active
            self._pause_counter -= 1
            if self._pause_counter == 0:
                self._active.set()

    def resume(self, events=()):
        """Add events on the queue and resume processing (will unpause and enable accepting events)."""
        [self.queue.put(event) for event in events]
        self.unpause()
        self.accept_events()

    def accept_events(self):
        """Accept events for processing"""
        self._accepting_events = True

    def ignore_events(self):
        """Ignore events for processing"""
        self._accepting_events = False

    def put(self, event):
        """Add an event on the queue"""
        if self._accepting_events:
            self.queue.put(event)

    def load(self, events):
        """Add multiple events on the queue"""
        if self._accepting_events:
            [self.queue.put(event) for event in events]

    def empty(self):
        """Discard all events that are present on the queue"""
        self.pause()
        try:
            while True:
                self.queue.get_nowait()
        except Queue.Empty:
            pass
        self.unpause()

    def get_unhandled(self):
        """Get unhandled events after the queue is stopped (events are removed from queue)"""
        if self.isAlive():
            raise RuntimeError('Queue is still running')
        unhandled = []
        try:
            while True:
                event = self.queue.get_nowait()
                if event is not StopProcessing:
                    unhandled.append(event)
        except Queue.Empty:
            pass
        return unhandled

    @staticmethod
    def handle(event):
        raise RuntimeError('unhandled event')


class CumulativeEventQueue(EventQueue):
    """An event queue that accumulates events and processes all of them together when its process method is called"""

    def __init__(self, handler, name=None, preload=()):
        EventQueue.__init__(self, handler, name, preload)
        self._waiting = []

    def run(self):
        """Run the event queue processing loop in its own thread"""
        while not self._exit.isSet():
            self._active.wait()
            event = self.queue.get()
            if event is StopProcessing:
                break
            elif event is ProcessEvents:
                if self._waiting:
                    preserved = []
                    # noinspection PyBroadException
                    try:
                        unhandled = self.handle(self._waiting)
                        if not isinstance(unhandled, (list, type(None))):
                            raise ValueError('%s handler must return a list of unhandled events or None' % self.__class__.__name__)
                        if unhandled is not None:
                            preserved = unhandled  # preserve the unhandled events that the handler returned
                    except Exception:
                        log.exception('Unhandled exception during event handling')
                    self._waiting = preserved
            elif event is DiscardEvents:
                self._waiting = []
            else:
                if getattr(event, 'high_priority', False):
                    # noinspection PyBroadException
                    try:
                        self.handle([event])
                    except Exception:
                        log.exception('Unhandled exception during high priority event handling')
                    finally:
                        del event  # do not reference this event until the next event arrives, in order to allow it to be released
                else:
                    self._waiting.append(event)

    def process(self):
        """Trigger accumulated event processing. The processing is done on the queue thread"""
        if self._accepting_events:
            self.queue.put(ProcessEvents)

    def empty(self):
        """Discard any events present on the queue"""
        EventQueue.empty(self)
        self.queue.put(DiscardEvents)

    def get_unhandled(self):
        """Get unhandled events after the queue is stopped (events are removed from queue)"""
        unhandled = self._waiting + EventQueue.get_unhandled(self)
        self._waiting = []
        return [e for e in unhandled if e is not ProcessEvents]

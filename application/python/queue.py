# Copyright (C) 2006-2007 Dan Pascu <dan@ag-projects.com>.
#

"""Event processing queues, that process the events in a distinct thread"""

__all__ = ['EventQueue', 'CumulativeEventQueue']

from threading import Thread, Event
import Queue

# Special events that control the queue operation (for internal use)
class StopProcessing: pass
class ProcessEvents: pass


class EventQueue(Thread):
    """Simple event processing queue that processes one event at a time"""

    def __init__(self, handler, name=None, preload=[]):
        if not callable(handler):
            raise TypeError("handler should be a callable")
        Thread.__init__(self, name=name or self.__class__.__name__)
        self.setDaemon(True)
        self._exit = Event()
        self.queue = Queue.Queue()
        self.handle = handler
        self.load(preload)
    def run(self):
        """Run the event queue processing loop in its own thread"""
        while not self._exit.isSet():
            event = self.queue.get()
            if event is StopProcessing:
                break
            self.handle(event)
    def stop(self, force_exit=False):
        """Terminate the event processing loop/thread (force_exit=True skips processing events already on queue)"""
        if force_exit:
            self._exit.set()
        self.queue.put(StopProcessing)
    def put(self, event):
        """Add an event to the queue to be processed"""
        self.queue.put(event)
    def load(self, events):
        """Add multiple events to the queue at once"""
        [self.queue.put(event) for event in events]
    def get_unhandled(self):
        """Get unhandled events, after the queue is stopped (events are removed from queue)"""
        if self.isAlive():
            raise RuntimeError("Queue is still running. Stop it first.")
        unhandled = []
        try:
            while True:
                event = self.queue.get_nowait()
                if event is not StopProcessing:
                    unhandled.append(event)
        except Queue.Empty:
            pass
        return unhandled
    def handle(self, event):
        raise RuntimeError("unhandled event")


class CumulativeEventQueue(EventQueue):
    """An event queue that accumulates events and processes all of them together when its process method is called"""

    def __init__(self, handler, name=None, preload=[]):
        EventQueue.__init__(self, handler, name, preload)
        self._waiting = []
    def run(self):
        """Run the event queue processing loop in its own thread"""
        while not self._exit.isSet():
            event = self.queue.get()
            if event is StopProcessing:
                break
            elif event is ProcessEvents:
                if self._waiting:
                    self.handle(self._waiting)
                    self._waiting = []
            else:
                if getattr(event, 'high_priority', False):
                    self.handle([event])
                else:
                    self._waiting.append(event)
    def process(self):
        """Trigger accumulated event processing. The processing is done on the queue thread"""
        self.put(ProcessEvents)
    def get_unhandled(self):
        """Get unhandled events, after the queue is stopped (events are removed from queue)"""
        unhandled = self._waiting + EventQueue.get_unhandled(self)
        self._waiting = []
        return [e for e in unhandled if e is not ProcessEvents]



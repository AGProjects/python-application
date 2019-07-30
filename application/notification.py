
"""A notification system"""

import weakref
from collections import deque
from datetime import datetime
from threading import Lock
from time import time
from zope.interface import Interface, implements

from application import log
from application.python.descriptor import ThreadLocal
from application.python.types import Singleton, MarkerType
from application.python.weakref import weakobjectmap


__all__ = 'Any', 'UnknownSender', 'IObserver', 'NotificationData', 'Notification', 'NotificationCenter', 'ObserverWeakrefProxy'


class Any(object):
    """Any sender or notification name"""
    __metaclass__ = MarkerType


class UnknownSender(object):
    """A special sender used for anonymous notifications"""
    __metaclass__ = MarkerType


class IObserver(Interface):
    """Interface describing a Notification Observer"""

    # noinspection PyMethodMayBeStatic
    def handle_notification(self, notification):
        """Function used to handle a posted Notification"""


class ObserverWeakrefProxy(object):
    """
    A proxy that allows an observer to be weakly referenced and automatically
    removes any remaining registrations that the observer didn't clean itself
    before its reference count dropped to zero.
    """

    implements(IObserver)

    observer_map = weakobjectmap()
    lock = Lock()

    def __new__(cls, observer):
        if not IObserver.providedBy(observer):
            raise TypeError('observer must implement the IObserver interface')
        with cls.lock:
            if observer in cls.observer_map:
                return cls.observer_map[observer]
            instance = object.__new__(cls)
            instance.observer_ref = weakref.ref(observer, instance.cleanup)
            cls.observer_map[observer] = instance
            return instance

    # noinspection PyUnusedLocal
    def cleanup(self, ref):
        # remove all observer's remaining registrations (the ones that the observer didn't remove itself)
        for notification_center in NotificationCenter.__instances__.itervalues():
            notification_center.purge_observer(self)

    def handle_notification(self, notification):
        observer = self.observer_ref()
        if observer is not None:
            observer.handle_notification(notification)


class NotificationData(object):
    """Object containing the notification data"""

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, ', '.join('%s=%r' % (name, value) for name, value in self.__dict__.iteritems()))


class Notification(object):
    """Object representing a notification"""

    def __init__(self, name, sender=UnknownSender, data=NotificationData()):
        if name is Any or sender is Any:
            raise ValueError('name and/or sender must not be the special object Any')
        self.name = name
        self.sender = sender
        self.data = data
        self.timestamp = time()

    @property
    def datetime(self):
        return self.__dict__.get('datetime') or self.__dict__.setdefault('datetime', datetime.fromtimestamp(self.timestamp))

    @property
    def utcdatetime(self):
        return self.__dict__.get('utcdatetime') or self.__dict__.setdefault('utcdatetime', datetime.utcfromtimestamp(self.timestamp))

    def __repr__(self):
        return '%s(%r, %r, %r)' % (self.__class__.__name__, self.name, self.sender, self.data)


class NotificationCenter(object):
    """
    A NotificationCenter allows observers to subscribe to receive notifications
    identified by name and sender and will distribute the posted notifications
    according to those subscriptions.
    """

    __metaclass__ = Singleton

    queue = ThreadLocal(deque)

    def __init__(self, name='default'):
        """
        Create a NotificationCenter with the specified name. Subsequent calls
        with the same `name' parameter will return the same NotificationCenter
        object.
        """
        self.name = name
        self.observers = {}
        self.lock = Lock()

    def add_observer(self, observer, name=Any, sender=Any):
        """
        Register an observer to receive notifications identified by a name and a
        sender.

        If `name' is Any, the observer will receive all notifications sent by
        the specified sender. If `sender' is Any, it will receive notifications
        sent by all senders, rather than from only one; if `sender' is
        UnknownSender, the observer will only receive anonymous notifications.
        """
        if not IObserver.providedBy(observer):
            raise TypeError('observer must implement the IObserver interface')
        with self.lock:
            self.observers.setdefault((name, sender), set()).add(observer)

    def remove_observer(self, observer, name=Any, sender=Any):
        """
        Remove an observer's subscription if present, else raise KeyError.

        The `name' and `sender' arguments must match the ones used to
        register the observer.

        See discard_observer for a variant that doesn't raise KeyError if
        the observer is not registered.
        """
        with self.lock:
            try:
                observer_set = self.observers[(name, sender)]
                observer_set.remove(observer)
            except KeyError:
                raise KeyError('observer %r not registered for %r events from %r' % (observer, name, sender))
            if not observer_set:
                del self.observers[(name, sender)]

    def discard_observer(self, observer, name=Any, sender=Any):
        """
        Remove an observer's subscription if present, else do nothing.

        The `name' and `sender' arguments must match the ones used to
        register the observer.

        See remove_observer for a variant that raises KeyError if the
        observer is not registered.
        """
        with self.lock:
            observer_set = self.observers.get((name, sender), None)
            if observer_set is not None:
                observer_set.discard(observer)
                if not observer_set:
                    del self.observers[(name, sender)]

    def purge_observer(self, observer):
        """Remove all the observer's subscriptions."""
        with self.lock:
            subscriptions = [(key, observer_set) for key, observer_set in self.observers.iteritems() if observer in observer_set]
            for key, observer_set in subscriptions:
                observer_set.remove(observer)
                if not observer_set:
                    del self.observers[key]

    def post_notification(self, name, sender=UnknownSender, data=NotificationData()):
        """
        Post a notification which will be delivered to all observers whose
        subscription matches the name and sender attributes of the notification.
        """

        notification = Notification(name, sender, data)
        notification.center = self
        queue = self.queue
        queue.append(notification)
        # noinspection PyTypeChecker
        if len(queue) > 1:  # This is true if we post a notification from inside a notification handler
            return

        empty_set = set()

        while queue:
            notification = queue[0]
            observers = (self.observers.get((Any, Any), empty_set) |
                         self.observers.get((Any, notification.sender), empty_set) |
                         self.observers.get((notification.name, Any), empty_set) |
                         self.observers.get((notification.name, notification.sender), empty_set))
            for observer in observers:
                try:
                    observer.handle_notification(notification)
                except Exception:
                    log.exception('Unhandled exception in notification observer %r while handling notification %r' % (observer, notification.name))
            queue.popleft()

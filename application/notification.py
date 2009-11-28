# Copyright (C) 2009 AG Projects. See LICENSE for details.
#

"""Implements a notification system"""

from __future__ import with_statement

__all__ = ['Any', 'UnknownSender', 'IObserver', 'NotificationData', 'Notification', 'NotificationCenter', 'ObserverWeakrefProxy']


import weakref
from collections import deque
from threading import Lock
from zope.interface import Interface, implements

from application import log
from application.python.util import Singleton
from application.python.descriptor import ThreadLocal


## Special objects

class SpecialType(type):
    def __str__(cls):
        return cls.__name__
    __repr__ = __str__

class Any(object):
    """Any sender or notification name"""
    __metaclass__ = SpecialType

class UnknownSender(object):
    """A special sender used for anonymous notifications"""
    __metaclass__ = SpecialType

del SpecialType


## Notification Observer

class IObserver(Interface):
    """Interface describing a Notification Observer"""

    def handle_notification(notification):
        """Function used to handle a posted Notification"""


class ObserverWeakrefProxy(object):
    """
    A proxy that allows an observer to be weakly referenced and automatically
    removes any remaining registrations that the observer didn't clean itself
    before its reference count dropped to zero.
    """

    implements(IObserver)

    observer_map = weakref.WeakKeyDictionary()
    lock = Lock()

    def __new__(cls, observer):
        if not IObserver.providedBy(observer):
            raise TypeError("observer must implement the IObserver interface")
        with cls.lock:
            if observer in cls.observer_map:
                return cls.observer_map[observer]
            instance = object.__new__(cls)
            instance.observer_ref = weakref.ref(observer, instance.cleanup)
            instance.tracked_items = set()
            cls.observer_map[observer] = instance
            return instance

    def track(self, notification_center, name, sender):
        observer = self.observer_ref() # retain a reference to avoid threading issues while we add tracking data
        if observer is not None:       # track data only if observer is alive, else preserve tracked_items as cleanup iterates through them
            self.tracked_items.add((notification_center, name, sender))

    def untrack(self, notification_center, name, sender):
        observer = self.observer_ref() # retain a reference to avoid threading issues while we discard tracking data
        if observer is not None:       # untrack data only if observer is alive, else preserve tracked_items as cleanup iterates through them
            self.tracked_items.discard((notification_center, name, sender))

    def cleanup(self, ref):
        # remove all observer's remaining registrations (the ones that the observer didn't remove itself)
        for notification_center, name, sender in self.tracked_items:
            notification_center.discard_observer(self, name, sender)

    def handle_notification(self, notification):
        observer = self.observer_ref()
        if observer is not None:
            observer.handle_notification(notification)


## Notification

class NotificationData(object):
    """Object containing the notification data"""

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, ', '.join('%s=%r' % (name, value) for name, value in self.__dict__.iteritems()))

    __str__ = __repr__

class Notification(object):
    """Object representing a notification"""

    def __init__(self, name, sender=UnknownSender, data=NotificationData()):
        if Any in (name, sender):
            raise ValueError("name and/or sender must not be the special object Any")
        self.name = name
        self.sender = sender
        self.data = data

    def __repr__(self):
        return '%s(%r, %r, %r)' % (self.__class__.__name__, self.name, self.sender, self.data)

    __str__ = __repr__


## Notification Center

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
            raise TypeError("observer must implement the IObserver interface")
        with self.lock:
            self.observers.setdefault((name, sender), set()).add(observer)
            if isinstance(observer, ObserverWeakrefProxy):
                observer.track(self, name, sender)

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
                raise KeyError("observer %r not registered for %r events from %r" % (observer, name, sender))
            if not observer_set:
                del self.observers[(name, sender)]
            if isinstance(observer, ObserverWeakrefProxy):
                observer.untrack(self, name, sender)

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
                if isinstance(observer, ObserverWeakrefProxy):
                    observer.untrack(self, name, sender)

    def post_notification(self, name, sender=UnknownSender, data=NotificationData()):
        """
        Post a notification which will be delivered to all observers whose
        subscription matches the name and sender attributes of the notification.
        """

        notification = Notification(name, sender, data)
        self.queue.append(notification)
        if len(self.queue) > 1: # This is true if we post a notification from inside a notification handler
            return

        while self.queue:
            notification = self.queue[0]
            observers = (self.observers.get((Any, Any), set()) |
                         self.observers.get((Any, notification.sender), set()) |
                         self.observers.get((notification.name, Any), set()) |
                         self.observers.get((notification.name, notification.sender), set()))
            for observer in observers:
                try:
                    observer.handle_notification(notification)
                except:
                    log.error("Exception occured in observer %r while handling notification %r" % (observer, notification.name))
                    log.err()
            self.queue.popleft()



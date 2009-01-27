# Copyright (C) 2009 AG Projects. See LICENSE for details.
#

"""Implements a notification system"""

__all__ = ['Any', 'UnknownSender', 'IObserver', 'NotificationData', 'Notification', 'NotificationCenter']

from collections import deque
from zope.interface import Interface

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
        self.observers.setdefault((name, sender), set()).add(observer)

    def remove_observer(self, observer, name=Any, sender=Any):
        """
        Remove an observer's subscription.

        The `name' and `sender' arguments must match the ones used to register
        the observer.
        """
        try:
            observer_set = self.observers[(name, sender)]
            observer_set.remove(observer)
        except KeyError:
            raise KeyError("observer %r not registered for %r events from %r" % (observer, name, sender))
        if len(observer_set) == 0:
            del self.observers[(name, sender)]

    def post_notification(self, name, sender=UnknownSender, data=NotificationData()):
        """
        Post a notification which will be delivered to all observers whose
        subscription matches the name and sender attributes of the notification.
        """
        
        notification = Notification(name, sender, data)
        self.queue.append(notification)
        if len(self.queue) > 1:
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



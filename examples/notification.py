#!/usr/bin/python

from time import time
from zope.interface import implements
from application.notification import IObserver, NotificationData, NotificationCenter, ObserverWeakrefProxy

class Sender(object):
    def publish(self):
        center = NotificationCenter()
        print "Sending notification with name 'simple':"
        print "Expecting CatchAllObserver, SimpleObserver, ObjectObserver and VolatileAllObserver to receive notifications"
        center.post_notification(name='simple', sender=self)
        print "\nSending notification with name 'complex':"
        print "Expecting CatchAllObserver, ObjectObserver and VolatileAllObserver to receive notifications"
        center.post_notification(name='complex', sender=self, data=NotificationData(timestamp=time(), complex_attribute='complex_value'))

    def __repr__(self):
        return '%s()' % self.__class__.__name__

class AnonymousSender(Sender):
    def publish(self):
        center = NotificationCenter()
        print "Sending notification with name 'simple':"
        print "Expecting SimpleObserver to receive notifications (CatchAllObserver and VolatileAllObserver have been unregistered)"
        center.post_notification(name='simple')
        print "\nSending notification with name 'empty':"
        print "Expecting no observer to receive notifications (CatchAllObserver and VolatileAllObserver have been unregistered)"
        center.post_notification(name='empty', data=None)

class CatchAllObserver(object):
    """An observer that registers itself to receive all notifications."""
    implements(IObserver)
    
    def register(self):
        print "Registering CatchAllObserver to receive all notifications"
        NotificationCenter().add_observer(self)
    
    def unregister(self):
        print "Unregistering CatchAllObserver from receiving all notifications"
        NotificationCenter().remove_observer(self)
    
    def handle_notification(self, notification):
        print "In CatchAllObserver got %r" % (notification,)

class SimpleObserver(object):
    """An observer that registers itself for notifications with name 'simple'."""
    implements(IObserver)
    
    def register(self):
        print "Registering SimpleObserver to receive notifications with name 'simple' from any sender"
        NotificationCenter().add_observer(self, name='simple')
    
    def unregister(self):
        print "Unregistering SimpleObserver from receiving notifications with name 'simple' from any sender"
        NotificationCenter().remove_observer(self, name='simple')
    
    def handle_notification(self, notification):
        print "In SimpleObserver got %r" % (notification,)

class ObjectObserver(object):
    """An observer that registers itself for notifications coming from a specific object."""
    implements(IObserver)

    def __init__(self, sender):
        self.sender = sender
    
    def register(self):
        print "Registering ObjectObserver to receive notifications with any name from sender %r" % (self.sender,)
        NotificationCenter().add_observer(self, sender=self.sender)
    
    def unregister(self):
        print "Unregistering ObjectObserver from receiving notifications with any name from sender %r" % (self.sender,)
        NotificationCenter().remove_observer(self, sender=self.sender)
    
    def handle_notification(self, notification):
        print "In ObjectObserver got %r" % (notification,)

class VolatileAllObserver(object):
    """An observer that registers itself to receive all notifications and it is weakly referenced"""
    implements(IObserver)
    
    def __init__(self):
        print "Registering VolatileAllObserver to receive all notifications"
        NotificationCenter().add_observer(ObserverWeakrefProxy(self))
    
    def handle_notification(self, notification):
        print "In VolatileAllObserver got %r" % (notification,)


# instatiate senders
sender = Sender()
anonymous = AnonymousSender()

# instantiate the observers and register them
print "Creating and registering observers:"
catchall_observer = CatchAllObserver()
catchall_observer.register()
simple_observer = SimpleObserver()
simple_observer.register()
object_observer = ObjectObserver(sender)
object_observer.register()
volatile_observer = VolatileAllObserver()

# send notifications
print "\nSending notifications from Sender:"
print "----------------------------------"
sender.publish()

print "\nUnregistering some observers:"
catchall_observer.unregister()
print "Deleting VolatileAllObserver which will automatically unregister it from receiving all notifications"
del volatile_observer

print "\nSending notifications from AnonymousSender:"
print "-------------------------------------------"
anonymous.publish()


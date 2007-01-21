# Copyright (C) 2007 Dan Pascu <dan@ag-projects.com>.
#

"""Helper functions for writing well behaved decorators."""

__all__ = ['decorator', 'preserve_signature']

def decorator(func):
    """A syntactic marker with no other effect than improving readability."""
    return func

def preserve_signature(func):
    """Preserve the original function signature and attributes in decorator wrappers."""
    from inspect import getargspec, formatargspec
    signature  = formatargspec(*getargspec(func))[1:-1]
    parameters = formatargspec(*getargspec(func), **{'formatvalue': lambda value: ""})[1:-1]
    def fix_signature(wrapper):
        code = "def %s(%s): return wrapper(%s)\nnew_wrapper = %s\n" % (func.__name__, signature, parameters, func.__name__)
        exec code in locals(), locals()
        #expression = "lambda %s: wrapper(%s)" % (signature, parameters)
        #new_wrapper = eval(expression, {'wrapper': wrapper})
        new_wrapper.__name__ = func.__name__
        new_wrapper.__doc__ = func.__doc__
        new_wrapper.__module__ = func.__module__
        new_wrapper.__dict__.update(func.__dict__)
        return new_wrapper
    return fix_signature


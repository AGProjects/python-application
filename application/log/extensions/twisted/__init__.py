# Copyright (C) 2009-2016 Dan Pascu. See LICENSE for details.
#

from __future__ import absolute_import

import os
import sys


def divert_logger():
    from twisted.python import log
    import logging

    class SimpleObserver(log.DefaultObserver):
        """Use logging as log backend for twisted"""

        def _emit(self, record):
            message = ' '.join(record['message'])
            if record['isError']:
                if 'failure' in record:
                    failure = record['failure']
                    logging.error(message, exc_info=(type(failure.value), failure.value, failure.tb))
                else:
                    logging.error(message)
            else:
                logging.info(message)

    if log.defaultObserver is not None:
        log.defaultObserver.stop()
        log.defaultObserver = SimpleObserver()
        log.defaultObserver.start()

if 'twisted' in sys.modules:
    divert_logger()
else:
    sys.path.insert(0, os.path.realpath(__path__[0]))


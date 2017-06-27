
from __future__ import absolute_import

import os
import sys
import warnings


def divert_logger():
    # noinspection PyPackageRequirements
    from twisted.logger import FilteringLogObserver, LogLevel, LogLevelFilterPredicate, STDLibLogObserver, globalLogBeginner
    showwarning = warnings.showwarning
    globalLogBeginner.beginLoggingTo([FilteringLogObserver(STDLibLogObserver(), [LogLevelFilterPredicate(defaultLogLevel=LogLevel.critical)])], redirectStandardIO=False)
    warnings.showwarning = showwarning  # twisted's beginLoggingTo() will divert python warnings to its own logging system. here we undo that.

if 'twisted' in sys.modules:
    divert_logger()
else:
    sys.path.insert(0, os.path.realpath(__path__[0]))

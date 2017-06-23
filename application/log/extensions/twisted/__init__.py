
from __future__ import absolute_import

import os
import sys


def divert_logger():
    from twisted.logger import FilteringLogObserver, LogLevel, LogLevelFilterPredicate, STDLibLogObserver, globalLogBeginner
    globalLogBeginner.beginLoggingTo([FilteringLogObserver(STDLibLogObserver(), [LogLevelFilterPredicate(defaultLogLevel=LogLevel.critical)])], redirectStandardIO=False)

if 'twisted' in sys.modules:
    divert_logger()
else:
    sys.path.insert(0, os.path.realpath(__path__[0]))


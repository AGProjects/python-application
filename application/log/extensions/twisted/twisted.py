
from __future__ import absolute_import

from application.log.extensions import twisted as fake_twisted
import os
import sys

try:
    sys.path.remove(os.path.realpath(fake_twisted.__path__[0]))
except ValueError:
    pass
else:
    sys.modules.pop('twisted', None)
    import twisted
    from application.log.extensions.twisted import divert_logger
    divert_logger()


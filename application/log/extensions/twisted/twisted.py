
from __future__ import absolute_import

import os
import sys

from application.log.extensions import twisted

try:
    sys.path.remove(os.path.realpath(twisted.__path__[0]))
except ValueError:
    pass
else:
    sys.modules.pop('twisted', None)
    # noinspection PyPackageRequirements
    import twisted
    from application.log.extensions.twisted import divert_logger
    divert_logger()

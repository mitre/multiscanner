# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter("%(asctime)s [%(name)s] [lno: %(lineno)d] [%(levelname)-7s] %(message)s"))
logger.addHandler(sh)

from .config import (  # noqa F401
    PY3, MS_WD, CONFIG, MODULESDIR
)

from .ms import (  # noqa F401
    config_init, multiscan, parse_reports, _ModuleInterface,
    _GlobalModuleInterface, _Thread, _run_module, _main
)

from .version import __version__  # noqa F401

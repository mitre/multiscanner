# -*- coding: utf-8 -*-

__version__ = '1.1.1'

from multiscanner.config import (               # noqa F401
    PY3, raw_input, MS_WD, CONFIG, MODULEDIR
)

from multiscanner.multiscanner import (         # noqa F401
    config_init, multiscan, parse_reports, _ModuleInterface,
    _GlobalModuleInterface, _Thread, _run_module, _main
)

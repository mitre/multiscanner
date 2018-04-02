# -*- coding: utf-8 -*-

__version__ = '1.1.1'

from multiscanner.config import (
    PY3, raw_input, MS_WD, CONFIG, MODULEDIR
)

from multiscanner.multiscanner import (
    config_init, multiscan, parse_reports, CONFIG, MODULEDIR, _ModuleInterface,
    _GlobalModuleInterface, _Thread, _run_module, _main, MS_WD
)

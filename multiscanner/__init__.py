import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from . import multiscanner

__version__ = '1.1.1'

common = multiscanner.common
multiscan = multiscanner.multiscan
parse_reports = multiscanner.parse_reports
config_init = multiscanner.config_init

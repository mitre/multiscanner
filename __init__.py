import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from . import multiscanner, storage
common = multiscanner.common
multiscan = multiscanner.multiscan
parse_reports = multiscanner.parse_reports
config_init = multiscanner.config_init

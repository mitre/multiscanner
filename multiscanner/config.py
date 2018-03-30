import os
import sys


PY3 = False
if sys.version_info < (2, 7) or sys.version_info > (4,):
    print("WARNING: You're running an untested version of python")
elif sys.version_info > (3,):
    PY3 = True

if PY3:
    raw_input = input

# Gets the directory that this file is in
# TODO: Add this as configuration option
MS_WD = os.path.dirname(os.path.abspath(__file__))

# The default config file
CONFIG = os.path.join(MS_WD, "config.ini")

# The directory where the modules are kept
MODULEDIR = os.path.join(MS_WD, "modules")

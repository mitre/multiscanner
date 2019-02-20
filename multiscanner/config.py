# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import os
import sys

from six import PY3  # noqa F401
from multiscanner.common.utils import parse_dir

if sys.version_info < (2, 7) or sys.version_info > (4,):
    print("WARNING: You're running an untested version of python")


# Gets the directory that this file is in
MS_WD = os.path.dirname(os.path.abspath(__file__))

# The directory where the modules are kept
MODULESDIR = os.path.join(MS_WD, 'modules')


def get_configuration_paths():
    # Possible paths for the configuration file.
    # This should go in order from local to global.
    return [
        os.path.join(os.getcwd(), 'config.ini'),
        os.path.join(os.path.expanduser('~'), '.multiscanner', 'config.ini'),
        '/opt/multiscanner/config.ini',
    ]


def determine_configuration_path(filepath):
    if filepath:
        return filepath

    config_paths = get_configuration_paths()
    config_file = None

    for config_path in config_paths:
        if os.path.exists(config_path):
            config_file = config_path

    if not config_file:
        # If the local storage folder doesn't exist, we create it.
        local_storage = os.path.join(os.path.expanduser('~'), '.multiscanner')
        if not os.path.exists(local_storage):
            os.makedirs(local_storage)
        return os.path.join(local_storage, 'config.ini')
    else:
        return config_file


# The default config file
CONFIG = determine_configuration_path(None)


def get_enabled_modules():
    """Returns a dictionary with module names as keys, with boolean values
    denoting whether or not they are enabled in the config.
    """
    files = parse_dir(MODULESDIR, recursive=True, exclude=["__init__"])
    filenames = [os.path.splitext(os.path.basename(f)) for f in files]
    module_names = [m[0] for m in filenames if m[1] == '.py']

    global CONFIG
    modules = {}
    for module in module_names:
        try:
            modules[module] = CONFIG[module]['ENABLED']
        except KeyError:
            pass
    return modules


# The list of enabled modules
MODULESLIST = get_enabled_modules()

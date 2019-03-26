# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import ast
import codecs
import configparser
import logging
import os
import sys

from six import PY3  # noqa F401
from multiscanner.common.utils import parse_dir

logger = logging.getLogger(__name__)

if sys.version_info < (2, 7) or sys.version_info > (4,):
    logger.warning("You're running an untested version of python")


# Gets the directory that this file is in
MS_WD = os.path.dirname(os.path.abspath(__file__))

# The directory where the modules are kept
MODULES_DIR = os.path.join(MS_WD, 'modules')

# The default config file
CONFIG_FILE = None

# Main MultiScanner config, as a dictionary
MS_CONFIG = None

# The dictionary of modules and whether they're enabled or not
MODULE_LIST = None


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


CONFIG_FILE = determine_configuration_path(None)


def parse_config(config_object):
    """Converts a config object to a dictionary"""
    return_var = {}
    for section in config_object.sections():
        section_dict = dict(config_object.items(section))
        for key in section_dict:
            try:
                section_dict[key] = ast.literal_eval(section_dict[key])
            except (SyntaxError, ValueError) as e:
                # Ignore if config value isn't convertible to a Python literal
                pass
            except Exception as e:
                logger.debug(e)
        return_var[section] = section_dict
    return return_var


def write_config(config_object, config_file, section_name, default_config):
    """Write the default configuration to the given config file

    config_object - the ConfigParser object
    config_file - the filename of the config file
    section_name - the name of the section of defaults to be added
    default_config - values to set this configuration to
    """
    if section_name not in config_object.sections():
        config_object.add_section(section_name)
    for key in default_config:
        config_object.set(section_name, key, str(default_config[key]))
    with codecs.open(config_file, 'w', 'utf-8') as conffile:
        config_object.write(conffile)


def read_config(config_file, section_name=None, default_config=None):
    """Parse a config file into a dictionary

    Can optionally set a default configuration by providing 'section_name' and
    'default_config' arguments.

    config_file - the filename of the config file
    section_name - the name of the section of defaults to be added
    default_config - values to set this configuration to
    """
    config_object = configparser.ConfigParser()
    config_object.optionxform = str
    config_object.read(config_file)
    if section_name is not None and default_config is not None and \
           (not config_object.has_section(section_name) or not os.path.isfile(config_file)):
        # Write default config
        write_config(config_object, config_file, section_name, default_config)
    return parse_config(config_object)


MS_CONFIG = read_config(CONFIG_FILE)


def get_config_path(component, config=None):
    """Gets the location of the config file for the given MultiScanner component
    from the MultiScanner config

    Components:
        storage
        api
        web

    component - component to get the path for
    config - dictionary or ConfigParser object containing MultiScanner config
    """
    if config is None:
        config = MS_CONFIG

    try:
        return config['main']['%s-config' % component]
    except KeyError:
        logger.error(
            "Couldn't find '{}-config' value in 'main' section "
            "of config file. Have you run 'python multiscanner.py init'?"
            .format(component)
        )
        sys.exit()


def get_modules():
    """Returns a dictionary with module names as keys. Values contain a boolean
    denoting whether or not they are enabled in the config, and the folder
    containing the module.
    """
    files = parse_dir(MODULES_DIR, recursive=True, exclude=["__init__"])

    global MS_CONFIG
    modules = {}
    # for module in module_names:
    for f in files:
        folder = os.path.dirname(f)
        filename = os.path.splitext(os.path.basename(f))

        if filename[1] == '.py':
            module = filename[0]
            try:
                modules[module] = [MS_CONFIG[module]['ENABLED'], folder]
            except KeyError as e:
                logger.debug(e)
                modules[module] = [False, folder]
    return modules


MODULE_LIST = get_modules()


def update_ms_config(config):
    """Update global config dictionary.

    config - the ConfigParser object or dictionary to replace MS_CONFIG with
    """
    global MS_CONFIG
    if isinstance(config, configparser.ConfigParser):
        MS_CONFIG = parse_config(config)
    else:
        MS_CONFIG = config


def update_ms_config_file(config_file):
    """Update config globals to a different file than the default.

    config_file - the file to be assigned to CONFIG_FILE and read into MS_CONFIG
    """
    global CONFIG_FILE, MS_CONFIG
    CONFIG_FILE = config_file
    MS_CONFIG = read_config(CONFIG_FILE)

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import ast
import codecs
import configparser
import logging
import os
import sys

from six import PY3, iteritems  # noqa F401
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

# Main MultiScanner config, as a ConfigParser object
MS_CONFIG = None

# The dictionary of modules and whether they're enabled or not
MODULE_LIST = None


class MSConfigParser(configparser.ConfigParser):
    def __init__(self, *args, **kwargs):
        super(MSConfigParser, self).__init__(*args, **kwargs)
        self.optionxform = str  # Preserve case

    def __getitem__(self, key):
        value = super(MSConfigParser, self).__getitem__(key)
        return _convert_to_literal(value)

    def get(self, *args, **kwargs):
        value = super(MSConfigParser, self).get(*args, **kwargs)
        return _convert_to_literal(value)


def _convert_to_literal(value):
    """Attempts to convert value to a Python literal if possible."""
    try:
        return ast.literal_eval(value)
    except (SyntaxError, ValueError) as e:
        # Ignore if config value isn't convertible to a Python literal
        pass
    except Exception as e:
        logger.debug(e)
    return value


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
    """Converts a ConfigParser object to a dictionary"""
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


def dict_to_config(dictionary):
    """Converts a dictionary to a ConfigParser object"""
    config = MSConfigParser()

    for name, section in dictionary.items():
        config.add_section(name)
        for key in section.keys():
            config.set(name, key, str(section[key]))
    return config


def write_config(config_object, config_file, default_config):
    """Write the default configuration to the given config file

    config_object - the ConfigParser object
    config_file - the filename of the config file
    default_config - dictionary of section names and values to set within this configuration
    """
    for section_name, section in default_config.items():
        if section_name not in config_object.sections():
            config_object.add_section(section_name)
        for key in section:
            config_object.set(section_name, key, str(default_config[section_name][key]))
    with codecs.open(config_file, 'w', 'utf-8') as conffile:
        config_object.write(conffile)


def read_config(config_file, default_config=None):
    """Parse a config file into a ConfigParser object

    Can optionally set a default configuration by providing 'section_name' and
    'default_config' arguments.

    config_file - the filename of the config file
    default_config - dictionary of section names and values to set within this configuration
    """
    config_object = MSConfigParser()
    config_object.read(config_file)
    if default_config is not None:
        contains_sections = set(default_config.keys()).issubset(config_object.sections())
        if not contains_sections or not os.path.isfile(config_file):
            # Write default config
            write_config(config_object, config_file, default_config)
    return config_object


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
    """Update global config object.

    config - the ConfigParser object or dictionary to replace MS_CONFIG with
    """
    global MS_CONFIG
    if isinstance(config, MSConfigParser):
        MS_CONFIG = config
    else:
        MS_CONFIG = dict_to_config(config)


def update_ms_config_file(config_file):
    """Update config globals to a different file than the default.

    config_file - the file to be assigned to CONFIG_FILE and read into MS_CONFIG
    """
    global CONFIG_FILE, MS_CONFIG
    CONFIG_FILE = config_file
    MS_CONFIG = read_config(CONFIG_FILE)


def update_paths_in_config(conf, filepath):
    """Rewrite config values containing paths to point to a new multiscanner config directory.
    """
    base_dir = os.path.split(filepath)[0]
    if 'storage-config' in conf:
        conf['storage-config'] = os.path.join(base_dir, 'storage.ini')
    if 'api-config' in conf:
        conf['api-config'] = os.path.join(base_dir, 'api_config.ini')
    if 'web-config' in conf:
        conf['web-config'] = os.path.join(base_dir, 'web_config.ini')
    if 'ruledir' in conf:
        conf['ruledir'] = os.path.join(base_dir, "etc", "yarasigs")
    if 'key' in conf:
        conf['key'] = os.path.join(base_dir, 'etc', 'id_rsa')
    if 'hash_list' in conf:
        conf['hash_list'] = os.path.join(base_dir, 'etc', 'nsrl', 'hash_list')
    if 'offsets' in conf:
        conf['offsets'] = os.path.join(base_dir, 'etc', 'nsrl', 'offsets')


def config_init(filepath, sections, overwrite=False):
    """
    Creates a new config file at filepath

    filepath - The config file to create
    sections - Dictionary mapping section names to the Python module containing its DEFAULTCONF
    overwrite - Whether to overwrite the config file at filepath, if it already exists
    """

    config = MSConfigParser()

    if overwrite or not os.path.isfile(filepath):
        return reset_config(sections, config, filepath)
    else:
        config.read(filepath)
        write_missing_config(sections, config, filepath)
        return config


def write_missing_config(sections, config_object, filepath):
    """
    Write in default config for modules not in config file. Returns True if config was written, False if not.

    config_object - The ConfigParser object
    filepath - The path to the config file
    sections - Dictionary mapping section names to the Python module containing its DEFAULTCONF
    """
    ConfNeedsWrite = False
    keys = list(sections.keys())
    keys.sort()
    for section_name in keys:
        if section_name in config_object:
            continue
        try:
            conf = sections[section_name].DEFAULTCONF
        except Exception as e:
            logger.warning(e)
            continue
        ConfNeedsWrite = True
        update_paths_in_config(conf, filepath)
        config_object.add_section(section_name)
        for key in conf:
            config_object.set(section_name, key, str(conf[key]))

    if ConfNeedsWrite:
        with codecs.open(filepath, 'w', 'utf-8') as f:
            config_object.write(f)
        return True
    return False


def reset_config(sections, config, filepath=None):
    """
    Reset specific sections of a config file to their factory defaults.

    sections - Dictionary mapping section names to the Python module containing its DEFAULTCONF
    config - ConfigParser object in which to store config
    filepath - Path to the config file

    Returns:
        The ConfigParser object that was written to the file.
    """
    if not filepath:
        CONFIG_FILE

    # Read in the old config to preserve any sections not being reset
    if os.path.isfile(filepath):
        config.read(filepath)

    logger.info('Rewriting config at {}...'.format(filepath))

    keys = list(sections.keys())
    keys.sort()
    for section_name in keys:
        try:
            conf = sections[section_name].DEFAULTCONF
        except Exception as e:
            logger.warning(e)
            continue

        update_paths_in_config(conf, filepath)
        if not config.has_section(section_name):
            config.add_section(section_name)
        for key in conf:
            config.set(section_name, key, str(conf[key]))

    with codecs.open(filepath, 'w', 'utf-8') as f:
        config.write(f)
    return config

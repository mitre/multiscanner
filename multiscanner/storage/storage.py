# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import (absolute_import, division, print_function,
                        unicode_literals, with_statement)

import codecs
import configparser
import inspect
import os
import time
import threading
from builtins import *  # noqa: F401,F403

from future import standard_library
standard_library.install_aliases()


from multiscanner.config import CONFIG as MS_CONFIG
from multiscanner.common import utils


DEFAULTCONF = {
    'retry_time': 5,  # Number of seconds to wait between retrying to connect to storage
    'retry_num': 20,  # Number of times to retry to connect to storage
}


STORAGE_DIR = os.path.dirname(__file__)


class StorageNotLoadedError(Exception):
    pass


class ThreadCounter(object):
    def __init__(self):
        self.lock = threading.Lock()
        self.value = 0
        self.event = threading.Event()

    def add(self):
        self.lock.acquire()
        self.value += 1
        self.lock.release()
        self._check_event()

    def sub(self):
        self.lock.acquire()
        self.value -= 1
        self.lock.release()
        self._check_event()

    def _check_event(self):
        if self.value == 0:
            self.event.set()
        elif self.event.is_set():
            self.event.clear()

    def wait(self, timeout=None):
        self.event.wait(timeout=timeout)

    def is_done(self):
        if self.value == 0:
            return True
        else:
            return False


class Storage(object):
    DEFAULTCONF = {
        'ENABLED': False
    }

    def __init__(self, config=DEFAULTCONF):
        self.config = config

    def setup(self):
        return True

    def store(self, results):
        raise NotImplementedError

    def teardown(self):
        return True


class StorageHandler(object):
    def __init__(self, configfile=MS_CONFIG, config=None, configregen=False):
        self.storage_lock = threading.Lock()
        self.storage_counter = ThreadCounter()
        # Load all storage classes
        storage_classes = _get_storage_classes()

        # Read in config
        if configfile:
            configfile = utils.get_config_path(MS_CONFIG, 'storage')
            config_object = configparser.SafeConfigParser()
            config_object.optionxform = str
            # Regen the config if needed or wanted
            if configregen or not os.path.isfile(configfile):
                _write_main_config(config_object)
                _rewrite_config(storage_classes, config_object, configfile)

            config_object.read(configfile)
            if config:
                file_conf = utils.parse_config(config_object)
                for key in config:
                    if key not in file_conf:
                        file_conf[key] = config[key]
                        file_conf[key]['_load_default'] = True
                    else:
                        file_conf[key].update(config[key])
                config = file_conf
            else:
                config = utils.parse_config(config_object)
        else:
            if config is None:
                config = {}
                for storage_name in storage_classes:
                    config[storage_name] = {}
            config['_load_default'] = True

        self.sleep_time = config.get('main', {}).get('retry_time', DEFAULTCONF['retry_time'])
        self.num_retries = config.get('main', {}).get('retry_num', DEFAULTCONF['retry_num'])

        # Set the config inside of the storage classes
        for storage_name in storage_classes:
            if storage_name in config:
                if '_load_default' in config or '_load_default' in config[storage_name]:
                    # Remove _load_default from config
                    if '_load_default' in config[storage_name]:
                        del config[storage_name]['_load_default']
                    # Update the default storage config
                    storage_classes[storage_name].config = storage_classes[storage_name].DEFAULTCONF
                    storage_classes[storage_name].config.update(config[storage_name])
                else:
                    storage_classes[storage_name].config = config[storage_name]

        self.storage_classes = storage_classes
        self.loaded_storage = {}

        # Setup each enabled storage
        self.load_modules()

    def load_modules(self, required_module=''):
        """ Call setup for each enabled storage module. Specify a required module
        to retry until that module is loaded.

        Returns:
            All loaded modules.
        """
        # Check if required module is already loaded
        if required_module:
            for module in self.loaded_storage:
                if module.__class__.__name__ == required_module:
                    return module

        # Sleep and retry until storage setup is successful
        storage_error = None
        for x in range(0, self.num_retries):
            for storage_name in self.storage_classes:
                storage = self.storage_classes[storage_name]
                if storage_name in self.loaded_storage:  # already loaded
                    continue

                if storage.config['ENABLED'] is True:
                    try:
                        if storage.setup():
                            self.loaded_storage[storage_name] = storage
                    except Exception as e:
                        storage_error = e
                        print('ERROR:', 'storage', storage_name, 'failed to load.', e)
                elif storage_name == required_module and storage.config['ENABLED'] is False:
                    raise StorageNotLoadedError('{} module is required but not loaded!'.format(required_module))

            if not self.loaded_storage:
                print('ERROR: No storage classes loaded.')
                if x < self.num_retries:
                    print('Retrying...')
            elif required_module:
                if required_module in self.loaded_storage:
                    storage_error = None
                else:
                    print('WARNING: Required storage {} not loaded.'.format(required_module))
                    if x < self.num_retries:
                        print('Retrying...')
            else:
                storage_error = None

            if storage_error:
                time.sleep(self.sleep_time)
            else:
                break

        if storage_error:
            if required_module:
                raise StorageNotLoadedError('{} module not loaded!'.format(required_module))
            else:
                raise StorageNotLoadedError('No storage module loaded!')

        return self.loaded_storage

    def load_required_module(self, required_module=''):
        """Ensure the required module is loaded.

        Returns:
            The required storage module.
        """
        self.load_modules()
        return self.loaded_storage.get(required_module, None)

    def store(self, dictionary, wait=True):
        """Stores dictionary in active storage module. If wait is False, a thread object is returned.
        """
        if wait:
            self._store_thread(dictionary)
        else:
            t = threading.Thread(target=self._store_thread, args=(dictionary,))
            t.daemon = False
            t.start()
            return t

    def _store_thread(self, dictionary):
        self.storage_counter.add()
        self.storage_lock.acquire()
        thread_list = []
        for storage in self.loaded_storage.values():
            t = threading.Thread(target=storage.store, args=(dict(dictionary),))
            t.daemon = False
            t.start()
            thread_list.append(t)
        for t in thread_list:
            t.join()
        self.storage_lock.release()
        self.storage_counter.sub()

    def close(self):
        """
        Waits for all storage operations to finish and closes each storage module
        """
        self.storage_counter.wait()
        thread_list = []
        for storage in self.loaded_storage.values():
            t = threading.Thread(target=storage.teardown)
            t.daemon = False
            t.start()
            thread_list.append(t)
        for t in thread_list:
            t.join()
        self.loaded_storage = {}

    def is_done(self, wait=False):
        if wait:
            self.storage_counter.wait()
            return True
        else:
            return self.storage_counter.is_done()


def config_init(filepath, overwrite=False, storage_classes=None):
    if storage_classes is None:
        storage_classes = _get_storage_classes()
    config_object = configparser.SafeConfigParser()
    config_object.optionxform = str
    if overwrite or not os.path.isfile(filepath):
        _write_main_config(config_object)
        _rewrite_config(storage_classes, config_object, filepath)
    else:
        config_object.read(filepath)
        _write_main_config(config_object)
        _write_missing_config(config_object, filepath, storage_classes=storage_classes)


def _write_main_config(config_object):
    if not config_object.has_section('main'):
        # Write default config
        config_object.add_section('main')
        for key in DEFAULTCONF:
            config_object.set('main', key, str(DEFAULTCONF[key]))


def _rewrite_config(storage_classes, config_object, filepath):
    keys = list(storage_classes.keys())
    keys.sort()
    for class_name in keys:
        conf = storage_classes[class_name].DEFAULTCONF
        config_object.add_section(class_name)
        for key in conf:
            config_object.set(class_name, key, str(conf[key]))

    with codecs.open(filepath, 'w', 'utf-8') as f:
        config_object.write(f)


def _write_missing_config(config_object, filepath, storage_classes=None):
    """
    Write in default config for modules not in config file. Returns True if config was written, False if not.

    config_object - The config object
    filepath - The path to the config file
    storage_classes - The dictionary object from _get_storage_classes. If None we call _get_storage_classes()
    """
    if storage_classes is None:
        storage_classes = _get_storage_classes()
    ConfNeedsWrite = False
    keys = list(storage_classes.keys())
    keys.sort()
    for module in keys:
        if module in config_object:
            continue
        try:
            conf = module.DEFAULTCONF
        except Exception as e:
            # TODO: log exception
            continue
        ConfNeedsWrite = True
        config_object.add_section(module)
        for key in conf:
            config_object.set(module, key, str(conf[key]))

    if ConfNeedsWrite:
        with codecs.open(filepath, 'w', 'utf-8') as f:
            config_object.write(f)
        return True
    return False


def _get_storage_classes(dir_path=STORAGE_DIR):
    storage_classes = {}
    dir_list = utils.parseDir(dir_path, recursive=True)
    dir_list.remove(os.path.join(dir_path, 'storage.py'))
    # dir_list.remove(os.path.join(dir_path, '__init__.py'))
    dir_list.remove(os.path.join(dir_path, 'sql_driver.py'))
    for filename in dir_list:
        if filename.endswith('.py'):
            modname = os.path.basename(filename[:-3])
            moddir = os.path.dirname(filename)
            mod = utils.load_module(os.path.basename(modname), [moddir])
            if not mod:
                print(filename, 'not a valid storage module...')
                continue
            for member_name in dir(mod):
                member = getattr(mod, member_name)
                if inspect.isclass(member) and issubclass(member, Storage):
                    storage_classes[member_name] = member()
    if 'Storage' in storage_classes:
        del storage_classes['Storage']
    return storage_classes

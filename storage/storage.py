# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import division, absolute_import, with_statement, print_function, unicode_literals
from builtins import *
from future import standard_library
standard_library.install_aliases()
import codecs
import configparser
import os
import sys
import threading
import inspect
STORAGE_DIR = os.path.dirname(__file__)
MS_WD = os.path.dirname(STORAGE_DIR)
if os.path.join(MS_WD, 'libs') not in sys.path:
    sys.path.append(os.path.join(MS_WD, 'libs'))
import common
CONFIG = os.path.join(MS_WD, "storage.ini")


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
        pass

    def store(self, results):
        raise NotImplementedError

    def teardown(self):
        pass


class StorageHandler(object):
    def __init__(self, configfile=CONFIG, config=None, configregen=False):
        self.storage_lock = threading.Lock()
        self.storage_counter = ThreadCounter()
        # Load all storage classes
        storage_classes = _get_storage_classes()

        # Read in config
        if configfile:
            config_object = configparser.SafeConfigParser()
            config_object.optionxform = str
            # Regen the config if needed or wanted
            if configregen or not os.path.isfile(configfile):
                _rewite_config(storage_classes, config_object, configfile)

            config_object.read(configfile)
            if config:
                file_conf = common.parse_config(config_object)
                for key in config:
                    if key not in file_conf:
                        file_conf[key] = config[key]
                        file_conf[key]['_load_default'] = True
                    else:
                        file_conf[key].update(config[key])
                config = file_conf
            else:
                config = common.parse_config(config_object)
        else:
            if config is None:
                config = {}
                for storage_name in storage_classes:
                    config[storage_name] = {}
            config['_load_default'] = True

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

        # Call setup for each enabled storage
        loaded_storage = []
        for storage_name in storage_classes:
            storage = storage_classes[storage_name]
            if storage.config['ENABLED'] is True:
                try:
                    if storage.setup():
                        loaded_storage.append(storage)
                except Exception as e:
                    print('ERROR:', 'storage', storage_name, 'failed to load.', e)
        if loaded_storage == []:
            raise RuntimeError('No storage classes loaded')
        self.loaded_storage = loaded_storage

    def store(self, dictionary, wait=True):
        """
        Takes a dictionary and stores it in each of the active storage modules. If wait is False a thread object is returned.
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
        for storage in self.loaded_storage:
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
        for storage in self.loaded_storage:
            t = threading.Thread(target=storage.teardown)
            t.daemon = False
            t.start()
            thread_list.append(t)
        for t in thread_list:
            t.join()
        self.loaded_storage = []

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
        _rewite_config(storage_classes, config_object, filepath)
    else:
        config_object.read(filepath)
        _write_missing_config(config_object, filepath, storage_classes=storage_classes)


def _rewite_config(storage_classes, config_object, filepath):
    for class_name in storage_classes:
        conf = storage_classes[class_name].DEFAULTCONF
        config_object.add_section(class_name)
        for key in conf:
            config_object.set(class_name, key, str(conf[key]))
    
    conffile = codecs.open(filepath, 'w', 'utf-8')
    config_object.write(conffile)
    conffile.close()


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
    storage_classes.sort()
    for module in storage_classes:
        try:
            conf = module.DEFAULTCONF
        except:
            continue
        ConfNeedsWrite = True
        config_object.add_section(module)
        for key in conf:
            config_object.set(module, key, str(conf[key]))

    if ConfNeedsWrite:
        conffile = codecs.open(filepath, 'w', 'utf-8')
        config_object.write(conffile)
        conffile.close()
        return True
    return False


def _get_storage_classes(dir_path=STORAGE_DIR):
    storage_classes = {}
    dir_list = common.parseDir(dir_path, recursive=True)
    dir_list.remove(os.path.join(dir_path, 'storage.py'))
    dir_list.remove(os.path.join(dir_path, '__init__.py'))
    for filename in dir_list:
        if filename.endswith('.py'):
            modname = os.path.basename(filename[:-3])
            moddir = os.path.dirname(filename)
            mod = common.load_module(os.path.basename(modname), [moddir])
            if not mod:
                print(filename, 'not a valid storage module...')
                continue
            for member_name in dir(mod):
                member = getattr(mod, member_name)
                if inspect.isclass(member) and issubclass(member, Storage):
                    storage_classes[member_name] = member()
    return storage_classes

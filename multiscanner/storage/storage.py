# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import (absolute_import, division, unicode_literals, with_statement)

import inspect
import logging
import os
import time
import threading
from builtins import *  # noqa: F401,F403

from future import standard_library
standard_library.install_aliases()


from multiscanner.common import utils
from multiscanner.config import MSConfigParser, get_config_path


DEFAULTCONF = {
    'retry_time': 5,  # Number of seconds to wait between retrying to connect to storage
    'retry_num': 20,  # Number of times to retry to connect to storage
}


STORAGE_DIR = os.path.dirname(__file__)

logger = logging.getLogger(__name__)


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
    def __init__(self, configfile=None, config=None):
        self.storage_lock = threading.Lock()
        self.storage_counter = ThreadCounter()
        # Load all storage classes
        storage_classes = _get_storage_classes()
        if configfile is None:
            configfile = get_config_path('storage')

        # Read in config
        config_object = MSConfigParser()
        config_object.read(configfile)
        if config:
            for key in config:
                if key not in config_object:
                    config_object[key] = config[key]
                else:
                    config_object[key].update(config[key])
        config = config_object

        self.sleep_time = config.get('main', 'retry_time', fallback=DEFAULTCONF['retry_time'])
        self.num_retries = config.get('main', 'retry_num', fallback=DEFAULTCONF['retry_num'])
        # Set the config inside of the storage classes
        for storage_name in storage_classes:
            if storage_name in config:
                storage_classes[storage_name].config = storage_classes[storage_name].DEFAULTCONF
                storage_classes[storage_name].config.update(config[storage_name])

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
                        logger.error('storage {} failed to load.'.format(storage_name))
                        logger.error(e)
                elif storage_name == required_module and storage.config['ENABLED'] is False:
                    raise StorageNotLoadedError('{} module is required but not loaded!'.format(required_module))

            if not self.loaded_storage:
                no_storage_msg = 'No storage classes loaded.'
                if x < self.num_retries:
                    no_storage_msg += ' Retrying...'
                logger.error(no_storage_msg)
            elif required_module:
                if required_module in self.loaded_storage:
                    storage_error = None
                else:
                    required_not_loaded_msg = 'Required storage {} not loaded.'.format(required_module)
                    if x < self.num_retries:
                        required_not_loaded_msg += ' Retrying...'
                    logger.warning(required_not_loaded_msg)
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


def _get_storage_classes(dir_path=STORAGE_DIR):
    storage_classes = {}
    dir_list = utils.parse_dir(dir_path, recursive=True)
    dir_list.remove(os.path.join(dir_path, 'storage.py'))
    # dir_list.remove(os.path.join(dir_path, '__init__.py'))
    # sql_driver is not configurable in storage.ini, and is used by the api
    # and celery workers rather than by the StorageHandler
    dir_list.remove(os.path.join(dir_path, 'sql_driver.py'))
    for filename in dir_list:
        if filename.endswith('.py'):
            modname = os.path.basename(filename[:-3])
            moddir = os.path.dirname(filename)
            mod = utils.load_module(os.path.basename(modname), [moddir])
            if not mod:
                logger.warning('{} is not a valid storage module...'.format(filename))
                continue
            for member_name in dir(mod):
                member = getattr(mod, member_name)
                if inspect.isclass(member) and issubclass(member, Storage):
                    storage_classes[member_name] = member()
    if 'Storage' in storage_classes:
        del storage_classes['Storage']
    return storage_classes

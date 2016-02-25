'''
Factory for generating a Storage class for
use by the RESTful API. This class will be
subclassed by various storage wrappers
that will allow the API to interface consistently
with the backend database regardless of which database
the end user chooses.

The storage subclass simply must support the following
4 operations:
Store:
    - Accepts a dictionary representing a task and
      stores it in the DB
    - Returns an ID #
Get:
    - Accepts an ID #
    - Returns a dictionary representing the task requested
    - If the task has not finished, the report field will
      be "pending"
Get Report:
    - Accepts an ID #
    - Returns a dictionary representing the report requested
Delete:
    - Accepts an ID #
    - Deletes the specified task
    - Returns a {"Message": "deleted"} dictionary or a
      404 {"Message": "No task with that ID found"} dictionary
'''

import os
import sys
from importlib import import_module
import abc
import ConfigParser


MS_WD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.join(MS_WD, 'libs') not in sys.path:
    sys.path.insert(0, os.path.join(MS_WD, 'libs'))

STORAGE_CONFIG = os.path.join(MS_WD, 'config_storage.ini')
STORAGE_SECTION = 'Database'

from common import parse_config

def get_config(config_file):
    '''
    Take in filepath to config file and return ConfigParser
    object.
    '''
    config = ConfigParser.SafeConfigParser()
    config.optionxform = str
    config.read(config_file)
    return config


class Storage(object):
    __metaclass__ = abc.ABCMeta

    @staticmethod
    def get_storage(config_file=STORAGE_CONFIG):
        config_object = get_config(config_file)
        config_dict = parse_config(config_object)
        db_choice = config_dict['Database']['database']

        mod_name = '%s_storage' % db_choice.lower()
        if db_choice == 'ElasticSearch':
            mod = import_module(mod_name)
            return mod.ElasticSearchStorage(config_dict['Database'])
        elif db_choice == 'Mongo':
            mod = import_module(mod_name)
            return mod.MongoStorage(config_dict['Database'])
        else:
            raise ValueError('Unsupported DB type')

    @abc.abstractmethod
    def store(self, task):
        pass

    @abc.abstractmethod
    def get(self, task_id):
        pass

    @abc.abstractmethod
    def get_report(self, report_id):
        pass

    @abc.abstractmethod
    def list(self):
        pass

    @abc.abstractmethod
    def delete(self, task_id):
        pass

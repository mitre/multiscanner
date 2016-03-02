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
    - Accepts a dictionary representing a report and
      stores it in the DB
    - Returns an ID #
Get Task:
    - Accepts an ID #
    - Returns a dictionary representing the task requested
        - <task_id, task_status, report_id>
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

import sqlite_driver

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
    sql_db = sqlite_driver.Database()

    def __init__(self):
        self.sql_db.init_sqlite_db()

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

    def _store(self, task_id, task_status, report):
        report_ids = self.store(report)
        self.sql_db.update_record(
            task_id=task_id,
            task_status=task_status,
            report_id=report_ids
        )
        return report_ids
        

    @abc.abstractmethod
    def store(self, report):
        pass

    @abc.abstractmethod
    def get_report(self, report_id):
        pass

    @abc.abstractmethod
    def delete(self, report_id):
        pass

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
Delete:
    - Accepts an ID #
    - Deletes the specified task
    - Returns a {"Message": "deleted"} dictionary or a
      404 {"Message": "No task with that ID found"} dictionary
'''

from importlib import import_module
import abc
import ConfigParser

STORAGE_CONFIG = 'config_storage.ini'
STORAGE_SECTION = 'Database'


def get_config(config_file):
    '''
    Take in filepath to config file and return ConfigParser
    object.
    '''
    config = ConfigParser.SafeConfigParser()
    config.optionxform = str
    config.read(config_file)
    return config


# TODO: import this function from libs/common.py
def parse_config(config_object):
    """Take a config object and returns it as a dictionary"""
    return_var = {}
    for section in config_object.sections():
        section_dict = dict(config_object.items(section))
        for key in section_dict:
            try:
                section_dict[key] = ast.literal_eval(section_dict[key])
            except:
                pass
        return_var[section] = section_dict
    return return_var


class Storage(object):
    __metaclass__ = abc.ABCMeta

    @staticmethod
    def get_storage(config_file):
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
    def list(self):
        pass

    @abc.abstractmethod
    def delete(self, task_id):
        pass

'''
This is the multiscanner celery worker. To initialize a worker node run:
$ celery -A celery_worker worker
from the utils/ directory.
'''

import os
import sys
import configparser
MS_WD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Append .. to sys path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Add the storage dir to the sys.path. Allows import of sql_driver module
if os.path.join(MS_WD, 'storage') not in sys.path:
    sys.path.insert(0, os.path.join(MS_WD, 'storage'))
# Add the libs dir to the sys.path. Allows import of common module
if os.path.join(MS_WD, 'libs') not in sys.path:
    sys.path.insert(0, os.path.join(MS_WD, 'libs'))
import multiscanner
import common
import sql_driver as database

from celery import Celery

DEFAULTCONF = {
    'protocol': 'pyamqp',
    'host': 'localhost',
    'user': 'guest',
    'password': '',
    'vhost': '/',
}

config_object = configparser.SafeConfigParser()
config_object.optionxform = str
configfile = common.get_api_config_path(multiscanner.CONFIG)
config_object.read(configfile)
config = common.parse_config(config_object)
worker_config = config.get('celery')
db_config = config.get('Database')

app = Celery(broker='{0}://{1}:{2}@{3}/{4}'.format(
    worker_config.get('protocol'),
    worker_config.get('user'),
    worker_config.get('password'),
    worker_config.get('host'),
    worker_config.get('vhost'),
))
db = database.Database(config=db_config)

@app.task
def multiscanner_celery(file_, original_filename, task_id, file_hash, config=multiscanner.CONFIG):
    '''
    TODO: Figure out how to do batching.
    This function essentially takes in a file list and runs
    multiscanner on them. Results are stored in the
    storage configured in storage.ini.

    Usage:
    from celery_worker import multiscanner_celery
    multiscanner_celery.delay([list, of, files, to, scan])
    '''
    # Initialize the connection to the task DB
    db.init_db()

    print('\n\n{}{}Got file: {}.\nOriginal filename: {}.\n'.format('='*48, '\n', file_hash, original_filename))

    # Get the storage config
    storage_conf = multiscanner.common.get_storage_config_path(config)
    storage_handler = multiscanner.storage.StorageHandler(configfile=storage_conf)

    resultlist = multiscanner.multiscan([file_], configfile=config)
    results = multiscanner.parse_reports(resultlist, python=True)
    # Use the original filename as the value for the filename
    # in the report (instead of the tmp path assigned to the file
    # by the REST API)
    results[original_filename] = results[file_]
    del results[file_]

    # Save the report to storage
    storage_handler.store(results, wait=False)
    storage_handler.close()

    # Update the task DB to reflect that the task is done
    db.update_task(
        task_id=task_id,
        task_status='Complete',
        report_id=file_hash,
    )

    print('Results of the scan:\n{}'.format(results)) 

    return results


if __name__ == '__main__':
    app.start()

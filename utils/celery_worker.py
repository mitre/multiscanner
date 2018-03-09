'''
This is the multiscanner celery worker. To initialize a worker node run:
$ celery -A celery_worker worker
from the utils/ directory.
'''

import os
import sys
import codecs
import configparser
from datetime import datetime
from socket import gethostname
MS_WD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Append .. to sys path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Add the storage dir to the sys.path. Allows import of sql_driver module
if os.path.join(MS_WD, 'storage') not in sys.path:
    sys.path.insert(0, os.path.join(MS_WD, 'storage'))
# Add the libs dir to the sys.path. Allows import of common, celery_batches modules
if os.path.join(MS_WD, 'libs') not in sys.path:
    sys.path.insert(0, os.path.join(MS_WD, 'libs'))
# Add the analytics dir to the sys.path. Allows import of ssdeep_analytics
if os.path.join(MS_WD, 'analytics') not in sys.path:
    sys.path.insert(0, os.path.join(MS_WD, 'analytics'))
import multiscanner
import common
import sql_driver as database
from ssdeep_analytics import SSDeepAnalytic

from celery import Celery, Task
from celery.schedules import crontab

DEFAULTCONF = {
    'protocol': 'pyamqp',
    'host': 'localhost',
    'user': 'guest',
    'password': '',
    'vhost': '/',
    'flush_every': '100',
    'flush_interval': '10',
    'tz': 'US/Eastern',
}

config_object = configparser.SafeConfigParser()
config_object.optionxform = str
configfile = common.get_config_path(multiscanner.CONFIG, 'api')
config_object.read(configfile)

if not config_object.has_section('celery') or not os.path.isfile(configfile):
    # Write default config
    config_object.add_section('celery')
    for key in DEFAULTCONF:
        config_object.set('celery', key, str(DEFAULTCONF[key]))
    conffile = codecs.open(configfile, 'w', 'utf-8')
    config_object.write(conffile)
    conffile.close()
config = common.parse_config(config_object)
api_config = config.get('api')
worker_config = config.get('celery')
db_config = config.get('Database')

app = Celery(broker='{0}://{1}:{2}@{3}/{4}'.format(
    worker_config.get('protocol'),
    worker_config.get('user'),
    worker_config.get('password'),
    worker_config.get('host'),
    worker_config.get('vhost'),
))
app.conf.timezone = worker_config.get('tz')
db = database.Database(config=db_config)


@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Executes every morning at 2:00 a.m.
    sender.add_periodic_task(
        crontab(hour=2, minute=0),
        ssdeep_compare_celery.s(),
    )


class MultiScannerTask(Task):
    '''
    Class of tasks that defines call backs to handle signals
    from celery
    '''
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        '''
        When a task fails, update the task DB with a "Failed"
        status. Dump a traceback to local logs
        '''
        print('Task #{} failed'.format(args[2]))
        print('Traceback info:\n{}'.format(einfo))

        # Initialize the connection to the task DB
        db.init_db()

        scan_time = datetime.now().isoformat()

        # Update the task DB with the failure
        db.update_task(
            task_id=args[2],
            task_status='Failed',
            timestamp=scan_time,
        )


@app.task(base=MultiScannerTask)
def multiscanner_celery(file_, original_filename, task_id, file_hash, metadata, config=multiscanner.CONFIG):
    '''
    Queue up multiscanner tasks

    Usage:
    from celery_worker import multiscanner_celery
    multiscanner_celery.delay(full_path, original_filename, task_id, metdata,
                              hashed_filename, metadata, config)
    '''
    # Initialize the connection to the task DB
    db.init_db()

    files = {}
    print('\n\n{}{}Got file: {}.\nOriginal filename: {}.\n'.format('='*48, '\n', file_hash, original_filename))
    files[file_] = {
        'original_filename': original_filename,
        'task_id': task_id,
        'file_hash': file_hash,
        'metadata': metadata,
    }

    # Get the storage config
    storage_conf = multiscanner.common.get_config_path(config, 'storage')
    storage_handler = multiscanner.storage.StorageHandler(configfile=storage_conf)

    resultlist = multiscanner.multiscan(list(files), configfile=config)
    results = multiscanner.parse_reports(resultlist, python=True)

    scan_time = datetime.now().isoformat()

    # Get the Scan Config that the task was run with and
    # add it to the task metadata
    scan_config_object = configparser.SafeConfigParser()
    scan_config_object.optionxform = str
    scan_config_object.read(config)
    full_conf = common.parse_config(scan_config_object)
    sub_conf = {}
    for key in full_conf:
        if key == 'main':
            continue
        sub_conf[key] = {}
        sub_conf[key]['ENABLED'] = full_conf[key]['ENABLED']

    # Count number of modules enabled out of total possible
    # and add it to the Scan Metadata
    total_enabled = 0
    total_modules = 0
    for key in sub_conf:
        total_modules += 1
        if sub_conf[key]['ENABLED'] is True:
            total_enabled += 1

    results[file_]['Scan Metadata'] = {}
    results[file_]['Scan Metadata']['Worker Node'] = gethostname()
    results[file_]['Scan Metadata']['Scan Config'] = sub_conf
    results[file_]['Scan Metadata']['Modules Enabled'] = '{} / {}'.format(
        total_enabled, total_modules
    )

    # Use the original filename as the value for the filename
    # in the report (instead of the tmp path assigned to the file
    # by the REST API)
    results[original_filename] = results[file_]
    del results[file_]

    results[original_filename]['Scan Time'] = scan_time
    results[original_filename]['Metadata'] = metadata

    # Update the task DB to reflect that the task is done
    db.update_task(
        task_id=task_id,
        task_status='Complete',
        timestamp=scan_time,
    )

    # Save the reports to storage
    storage_handler.store(results, wait=False)
    storage_handler.close()
    print('Completed Task #{}'.format(task_id))

    return results

@app.task()
def ssdeep_compare_celery():
    '''
    Run ssdeep.compare for new samples.

    Usage:
    from celery_worker import ssdeep_compare_celery
    ssdeep_compare_celery.delay()
    '''
    ssdeep_analytic = SSDeepAnalytic()
    ssdeep_analytic.ssdeep_compare()


if __name__ == '__main__':
    app.start()

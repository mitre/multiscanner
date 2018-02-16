'''
This is the multiscanner celery worker. To initialize a worker node run:
$ celery -A celery_worker worker
from the utils/ directory.
'''

import codecs
import configparser
import os
import sys
from datetime import datetime
from socket import gethostname

from celery import Celery
from celery.schedules import crontab

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

import common
import multiscanner
import sql_driver as database
from celery_batches import Batches
from ssdeep_analytics import SSDeepAnalytic


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

def celery_task(files, config=multiscanner.CONFIG):
    '''
    Run multiscanner on the given file and store the results in the storage
    handler(s) specified in the storage configuration file.
    '''
    # Get the storage config
    storage_conf = multiscanner.common.get_config_path(config, 'storage')
    storage_handler = multiscanner.storage.StorageHandler(configfile=storage_conf)

    resultlist = multiscanner.multiscan(list(files), configfile=config)
    results = multiscanner.parse_reports(resultlist, python=True)

    scan_time = datetime.now().isoformat()

    # Loop through files in a way compatible with Py 2 and 3, and won't be
    # affected by changing keys to original filenames
    for file_ in files:
        original_filename = files[file_]['original_filename']
        task_id = files[file_]['task_id']
        metadata = files[file_]['metadata']
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
        results[file_]['Scan Metadata'] = {}
        results[file_]['Scan Metadata']['Worker Node'] = gethostname()
        results[file_]['Scan Metadata']['Scan Config'] = sub_conf

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

    return results


@app.task(base=Batches, flush_every=api_config['batch_size'], flush_interval=api_config['batch_interval'])
def multiscanner_celery(requests, *args, **kwargs):
    '''
    Queue up multiscanner tasks and then run a batch of them at a time for
    better performance.

    Usage:
    from celery_worker import multiscanner_celery
    multiscanner_celery.delay(full_path, original_filename, task_id, metdata,
                              hashed_filename, config)
    '''
    # Initialize the connection to the task DB
    db.init_db()

    files = {}
    for request in requests:
        file_ = request.args[0]
        original_filename = request.args[1]
        task_id = request.args[2]
        file_hash = request.args[3]
        metadata = request.args[4]
        # print('\n\n{}{}Got file: {}.\nOriginal filename: {}.\n'.format('='*48, '\n', file_hash, original_filename))
        files[file_] = {
            'original_filename': original_filename,
            'task_id': task_id,
            'file_hash': file_hash,
            'metadata': metadata,
        }

    celery_task(files)

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

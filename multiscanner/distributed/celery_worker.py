'''
This is the multiscanner celery worker. To initialize a worker node run:
$ celery -A celery_worker worker
from the utils/ directory.
'''

import codecs
import configparser
import os
from datetime import datetime
from socket import gethostname

from celery import Celery, Task
from celery.schedules import crontab
from celery.utils.log import get_task_logger

from multiscanner import CONFIG as MS_CONFIG
from multiscanner import multiscan, parse_reports
from multiscanner.common import utils
from multiscanner.storage import elasticsearch_storage, storage
from multiscanner.storage import sql_driver as database
from multiscanner.analytics.ssdeep_analytics import SSDeepAnalytic


logger = get_task_logger(__name__)

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
configfile = utils.get_config_path(MS_CONFIG, 'api')
config_object.read(configfile)

if not config_object.has_section('celery') or not os.path.isfile(configfile):
    # Write default config
    config_object.add_section('celery')
    for key in DEFAULTCONF:
        config_object.set('celery', key, str(DEFAULTCONF[key]))
    conffile = codecs.open(configfile, 'w', 'utf-8')
    config_object.write(conffile)
    conffile.close()
config = utils.parse_config(config_object)
api_config = config.get('api')
worker_config = config.get('celery')
db_config = config.get('Database')

storage_config_object = configparser.SafeConfigParser()
storage_config_object.optionxform = str
storage_configfile = utils.get_config_path(MS_CONFIG, 'storage')
storage_config_object.read(storage_configfile)
config = utils.parse_config(storage_config_object)
es_storage_config = config.get('ElasticSearchStorage')

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
    # Run ssdeep match analytic
    # Executes every morning at 2:00 a.m.
    sender.add_periodic_task(
        crontab(hour=2, minute=0),
        ssdeep_compare_celery.s(),
    )

    # Delete old metricbeat indices
    # Executes every morning at 3:00 a.m.
    metricbeat_enabled = es_storage_config.get('metricbeat_enabled', True)
    if metricbeat_enabled:
        sender.add_periodic_task(
            crontab(hour=3, minute=0),
            metricbeat_rollover.s(days=es_storage_config.get('metricbeat_rollover_days')),
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
        logger.error('Task #{} failed'.format(args[2]))
        logger.error('Traceback info:\n{}'.format(einfo))

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
def multiscanner_celery(file_, original_filename, task_id, file_hash, metadata,
                        config=MS_CONFIG, module_list=None):
    '''
    Queue up multiscanner tasks

    Usage:
    from celery_worker import multiscanner_celery
    multiscanner_celery.delay(full_path, original_filename, task_id,
                              hashed_filename, metadata, config, module_list)
    '''

    # Initialize the connection to the task DB
    db.init_db()

    logger.info('\n\n{}{}Got file: {}.\nOriginal filename: {}.\n'.format('=' * 48, '\n', file_hash, original_filename))

    # Get the storage config
    storage_conf = utils.get_config_path(config, 'storage')
    storage_handler = storage.StorageHandler(configfile=storage_conf)

    resultlist = multiscan(
        [file_],
        configfile=config,
        module_list=module_list
    )
    results = parse_reports(resultlist, python=True)

    scan_time = datetime.now().isoformat()

    # Get the Scan Config that the task was run with and
    # add it to the task metadata
    scan_config_object = configparser.SafeConfigParser()
    scan_config_object.optionxform = str
    scan_config_object.read(config)
    full_conf = utils.parse_config(scan_config_object)
    sub_conf = {}
    # Count number of modules enabled out of total possible
    # and add it to the Scan Metadata
    total_enabled = 0
    total_modules = len(full_conf.keys())

    # Get the count of modules enabled from the module_list
    # if it exists, else count via the config
    if module_list:
        total_enabled = len(module_list)
    else:
        for key in full_conf:
            if key == 'main':
                continue
            sub_conf[key] = {}
            sub_conf[key]['ENABLED'] = full_conf[key]['ENABLED']
            if sub_conf[key]['ENABLED'] is True:
                total_enabled += 1

    results[file_]['Scan Metadata'] = metadata
    results[file_]['Scan Metadata']['Worker Node'] = gethostname()
    results[file_]['Scan Metadata']['Scan Config'] = sub_conf
    results[file_]['Scan Metadata']['Modules Enabled'] = '{} / {}'.format(
        total_enabled, total_modules
    )
    results[file_]['Scan Metadata']['Scan Time'] = scan_time
    results[file_]['Scan Metadata']['Task ID'] = task_id

    # Use the original filename as the value for the filename
    # in the report (instead of the tmp path assigned to the file
    # by the REST API)
    results[original_filename] = results[file_]
    del results[file_]

    # Save the reports to storage
    storage_ids = storage_handler.store(results, wait=False)
    storage_handler.close()

    # Only need to raise ValueError here,
    # Further cleanup will be handled by the on_failure method
    # of MultiScannerTask
    if not storage_ids:
        raise ValueError('Report failed to index')

    # Update the task DB to reflect that the task is done
    db.update_task(
        task_id=task_id,
        task_status='Complete',
        timestamp=scan_time,
    )

    logger.info('Completed Task #{}'.format(task_id))

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


@app.task()
def metricbeat_rollover(days, config=MS_CONFIG):
    '''
    Clean up old Elastic Beats indices
    '''
    try:
        # Get the storage config
        storage_handler = storage.StorageHandler(configfile=storage_configfile)
        metricbeat_enabled = es_storage_config.get('metricbeat_enabled', True)

        if not metricbeat_enabled:
            logger.debug('Metricbeat logging not enbaled, exiting...')
            return

        if not days:
            days = es_storage_config.get('metricbeat_rollover_days')
        if not days:
            raise NameError("name 'days' is not defined, check storage.ini for 'metricbeat_rollover_days' setting")

        # Find Elastic storage
        for handler in storage_handler.loaded_storage:
            if isinstance(handler, elasticsearch_storage.ElasticSearchStorage):
                ret = handler.delete_index(index_prefix='metricbeat', days=days)

                if ret is False:
                    logger.warn('Metricbeat Roller failed')
                else:
                    logger.info('Metricbeat indices older than {} days deleted'.format(days))
    except Exception as e:
        logger.warn(e)
    finally:
        storage_handler.close()


if __name__ == '__main__':
    logger.debug('Initializing celery worker...')
    app.start()

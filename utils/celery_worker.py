import os
import sys
# Append .. to sys path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import multiscanner

from celery import Celery
from celery.contrib.batches import Batches

app = Celery('celery_worker', broker='pyamqp://guest@localhost//')

@app.task(base=Batches, flush_every=100, flush_interval=10)
def multiscanner_celery(filelist, config=multiscanner.CONFIG):
    '''
    TODO: Add other ars + config options...
    This function essentially takes in a file list and runs
    multiscanner on them. Results are stored in the
    storage configured in storage.ini.

    Usage:
    from celery_worker import multiscanner_celery
    multiscanner_celery.delay([list, of, files, to, scan])
    '''
    storage_conf = multiscanner.common.get_storage_config_path(config)
    storage_handler = multiscanner.storage.StorageHandler(configfile=storage_conf)

    resultlist = multiscanner.multiscan(filelist, configfile=config)
    results = multiscanner.parse_reports(resultlist, python=True)

    storage_handler.store(results, wait=False)
    storage_handler.close()
    return results

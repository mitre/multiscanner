import os
import sys
MS_WD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Append .. to sys path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Add the storage dir to the sys.path. Allows import of sql_driver module
if os.path.join(MS_WD, 'storage') not in sys.path:
    sys.path.insert(0, os.path.join(MS_WD, 'storage'))
import multiscanner
import sql_driver as database

from celery import Celery

RABBIT_USER = 'guest'
RABBIT_HOST = 'localhost'

app = Celery(broker='pyamqp://%s@%s//' % (RABBIT_USER, RABBIT_HOST))
db = database.Database()

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
        report_id=file_hash
    )

    return results

#!/usr/bin/env python
'''
THIS APP IS NOT PRODUCTION READY!! DO NOT USE!

Flask app that provides a RESTful API to
the multiscanner.

Proposed supported operations:
GET / ---> Test functionality. {'Message': 'True'}
GET /api/v1/tasks/list  ---> Receive list of tasks in multiscanner
GET /api/v1/tasks/list/<task_id> ---> receive task in JSON format
GET /api/v1/tasks/report/<task_id> ---> receive report in JSON
GET /api/v1/tasks/delete/<task_id> ----> delete task_id
POST /api/v1/tasks/create ---> POST file and receive report id
Sample POST usage:
    curl -i -X POST http://localhost:8080/api/v1/tasks/create/ -F file=@/bin/ls

The API endpoints all have Cross Origin Resource Sharing (CORS) enabled and set
to allow ALL origins.

TODO:
* Add doc strings to functions
'''
from __future__ import print_function
import os
import sys
import time
import hashlib
import multiprocessing
import queue
from uuid import uuid4
from flask_cors import cross_origin
from flask import Flask, jsonify, make_response, request, abort

MS_WD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.join(MS_WD, 'storage') not in sys.path:
    sys.path.insert(0, os.path.join(MS_WD, 'storage'))
if MS_WD not in sys.path:
    sys.path.insert(0, os.path.join(MS_WD))

import multiscanner
import sqlite_driver as database
from storage import Storage
import elasticsearch_storage

TASK_NOT_FOUND = {'Message': 'No task with that ID found!'}
INVALID_REQUEST = {'Message': 'Invalid request parameters'}
UPLOAD_FOLDER = 'tmp/'

BATCH_SIZE = 100
WAIT_SECONDS = 60   # Number of seconds to wait for additional files
                    # submitted to the create/ API

HTTP_OK = 200
HTTP_CREATED = 201
HTTP_BAD_REQUEST = 400
HTTP_NOT_FOUND = 404

FULL_DB_PATH = os.path.join(MS_WD, 'sqlite.db')


app = Flask(__name__)
db = database.Database(FULL_DB_PATH)
storage_conf = multiscanner.common.get_storage_config_path(multiscanner.CONFIG)
storage_handler = multiscanner.storage.StorageHandler(configfile=storage_conf)
for handler in storage_handler.loaded_storage:
    if isinstance(handler, elasticsearch_storage.ElasticSearchStorage):
        break
work_queue = multiprocessing.Queue()


def multiscanner_process(work_queue, exit_signal):
    metadata_list = []
    time_stamp = None
    while True:
        time.sleep(1)
        try:
            metadata_list.append(work_queue.get_nowait())
            if not time_stamp:
                time_stamp = time.time()
            while len(metadata_list) < BATCH_SIZE:
                metadata_list.append(work_queue.get_nowait())
        except queue.Empty:
            if metadata_list and time_stamp:
                if len(metadata_list) >= BATCH_SIZE:
                    pass
                elif time.time() - time_stamp > WAIT_SECONDS:
                    pass
                else:
                    continue
            else:
                continue

        filelist = [item[0] for item in metadata_list]
        resultlist = multiscanner.multiscan(
            filelist, configfile=multiscanner.CONFIG
        )
        results = multiscanner.parse_reports(resultlist, python=True)

        for file_name in results:
            os.remove(file_name)

        for item in metadata_list:

            # Use the filename as the index instead of the full path 
            results[item[1]] = results[item[0]]
            del results[item[0]]

            r_id = str(uuid4())
            results[item[1]]['report_id'] = r_id

            db.update_task(
                task_id=item[2],
                task_status='Complete',
                sample_id=item[3],
                report_id=r_id
            )

        storage_handler.store(results, wait=False)

        filelist = []
        time_stamp = None
    storage_handler.close()


@app.errorhandler(HTTP_BAD_REQUEST)
def invalid_request(error):
    '''Return a 400 with the INVALID_REQUEST message.'''
    return make_response(jsonify(INVALID_REQUEST), HTTP_BAD_REQUEST)


@app.errorhandler(HTTP_NOT_FOUND)
def not_found(error):
    '''Return a 404 with a TASK_NOT_FOUND message.'''
    return make_response(jsonify(TASK_NOT_FOUND), HTTP_NOT_FOUND)


@app.route('/')
def index():
    '''
    Return a default standard message
    for testing connectivity.
    '''
    return jsonify({'Message': 'True'})


@app.route('/api/v1/tasks/list/', methods=['GET'])
@cross_origin()
def task_list():
    '''
    Return a JSON dictionary containing all the tasks
    in the DB.
    '''

    return jsonify({'Tasks': db.get_all_tasks()})


@app.route('/api/v1/tasks/list/<int:task_id>', methods=['GET'])
@cross_origin()
def get_task(task_id):
    '''
    Return a JSON dictionary corresponding
    to the given task ID.
    '''
    task = db.get_task(task_id)
    if task:
        return jsonify({'Task': task.to_dict()})
    else:
        abort(HTTP_NOT_FOUND)


@app.route('/api/v1/tasks/delete/<int:task_id>', methods=['GET'])
@cross_origin()
def delete_task(task_id):
    '''
    Delete the specified task. Return deleted message.
    '''
    result = db.delete_task(task_id)
    if not result:
        abort(HTTP_NOT_FOUND)
    return jsonify({'Message': 'Deleted'})


@app.route('/api/v1/tasks/create/', methods=['POST'])
@cross_origin()
def create_task():
    '''
    Create a new task. Save the submitted file
    to UPLOAD_FOLDER. Return task id and 201 status.
    '''
    task_ids = []
    for file_ in request.files.getlist('file'):
        # TODO: Figure out how to get multiscanner to report
        # the original filename
        original_filename = file_.filename
        f_name = hashlib.sha256(file_.read()).hexdigest()
        # Reset the file pointer to the beginning
        # to allow us to save it
        file_.seek(0)

        file_path = os.path.join(UPLOAD_FOLDER, f_name)
        file_.save(file_path)
        full_path = os.path.join(MS_WD, file_path)

        # Add task to sqlite DB
        task_id = db.add_task()

        work_queue.put((full_path, original_filename, task_id, f_name))
        task_ids.append(str(task_id))

    if len(task_ids) == 1:
        msg = {'task_id': task_id}
    else:
        msg = {'task_ids': ", ".join(task_ids)}

    return make_response(
        jsonify({'Message': msg}),
        HTTP_CREATED
    )


@app.route('/api/v1/tasks/report/<task_id>', methods=['GET'])
@cross_origin()
def get_report(task_id):
    '''
    Return a JSON dictionary corresponding
    to the given task ID.
    '''
    task = db.get_task(task_id)
    if not task:
        abort(HTTP_NOT_FOUND)

    if task.task_status == 'Complete':
        report = handler.get_report(task.sample_id, task.report_id)

    elif task.task_status == 'Pending':
        report = {'Report': 'Task still pending'}

    if report:
        return jsonify({'Report': report})
    else:
        abort(HTTP_NOT_FOUND)


@app.route('/api/v1/tasks/delete/<task_id>', methods=['GET'])
@cross_origin()
def delete_report(task_id):
    '''
    Delete the specified task. Return deleted message.
    '''
    task = db.get_task(task_id)
    if not task:
        abort(HTTP_NOT_FOUND)

    if handler.delete(task.report_id):
        return jsonify({'Message': 'Deleted'})
    else:
        abort(HTTP_NOT_FOUND)


if __name__ == '__main__':

    db.init_sqlite_db()

    if not os.path.isdir(UPLOAD_FOLDER):
        print('Creating upload dir')
        os.makedirs(UPLOAD_FOLDER)

    exit_signal = multiprocessing.Value('b')
    exit_signal.value = False
    ms_process = multiprocessing.Process(
        target=multiscanner_process,
        args=(work_queue, exit_signal)
    )
    ms_process.start()

    app.run(host='0.0.0.0', port=8080)

    ms_process.join()

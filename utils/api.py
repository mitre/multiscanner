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
import codecs
import configparser
import multiprocessing
import queue
from uuid import uuid4
from flask_cors import cross_origin
from flask import Flask, jsonify, make_response, request, abort
from jinja2 import Markup

MS_WD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.join(MS_WD, 'storage') not in sys.path:
    sys.path.insert(0, os.path.join(MS_WD, 'storage'))
if MS_WD not in sys.path:
    sys.path.insert(0, os.path.join(MS_WD))

import multiscanner
import sql_driver as database
from storage import Storage
import elasticsearch_storage
from celery_worker import multiscanner_celery

TASK_NOT_FOUND = {'Message': 'No task with that ID found!'}
INVALID_REQUEST = {'Message': 'Invalid request parameters'}

BATCH_SIZE = 100
WAIT_SECONDS = 60   # Number of seconds to wait for additional files
                    # submitted to the create/ API

HTTP_OK = 200
HTTP_CREATED = 201
HTTP_BAD_REQUEST = 400
HTTP_NOT_FOUND = 404

DEFAULTCONF = {
    'host': 'localhost',
    'port': 8080,
    'upload_folder': '/mnt/samples/',
    'distributed': True
}

app = Flask(__name__)
api_config_object = configparser.SafeConfigParser()
api_config_object.optionxform = str
api_config_file = multiscanner.common.get_api_config_path(multiscanner.CONFIG)
api_config_object.read(api_config_file)
if not api_config_object.has_section('api') or not os.path.isfile(api_config_file):
    # Write default config
    api_config_object.add_section('api')
    for key in DEFAULTCONF:
        api_config_object.set('api', key, str(DEFAULTCONF[key]))
    conffile = codecs.open(api_config_file, 'w', 'utf-8')
    api_config_object.write(conffile)
    conffile.close()
api_config = multiscanner.common.parse_config(api_config_object)

db = database.Database(config=api_config.get('Database'))
storage_conf = multiscanner.common.get_storage_config_path(multiscanner.CONFIG)
storage_handler = multiscanner.storage.StorageHandler(configfile=storage_conf)
for handler in storage_handler.loaded_storage:
    if isinstance(handler, elasticsearch_storage.ElasticSearchStorage):
        break

if not api_config['api']['distributed']:
    work_queue = multiprocessing.Queue()


def multiscanner_process(work_queue, exit_signal):
    '''Not used in distributed mode.
    '''
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

            results[item[1]]['Metadata'] = item[4]

            db.update_task(
                task_id=item[2],
                task_status='Complete',
                report_id=item[3]
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
    Create a single new task. Save the submitted file
    to UPLOAD_FOLDER. Return task id and 201 status.
    '''
    file_ = request.files['file']
    original_filename = file_.filename
    f_name = hashlib.sha256(file_.read()).hexdigest()
    # Reset the file pointer to the beginning
    # to allow us to save it
    file_.seek(0)

    metadata = {}
    for key in request.form.keys():
        if key != 'file_id' and request.form[key] != '':
            metadata[key] = request.form[key]

    # TODO: should we check if the file is already there
    # and skip this step if it it?
    file_path = os.path.join(api_config['api']['upload_folder'], f_name)
    file_.save(file_path)
    full_path = os.path.join(MS_WD, file_path)

    # Add task to sqlite DB
    # Make the sample_id equal the sha256 hash
    task_id = db.add_task(sample_id=f_name)

    if api_config['api']['distributed']:
        # Publish the task to Celery
        multiscanner_celery.delay(full_path, original_filename,
                                  task_id, f_name, metadata)
    else:
        # Put the task on the queue
        work_queue.put((full_path, original_filename, task_id, f_name, metadata))

    msg = {'task_id': task_id}
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


@app.route('/api/v1/tags/', methods=['GET'])
@cross_origin()
def taglist():
    '''
    Return a list of all tags currently in use.
    '''
    response = handler.get_tags()
    if not response:
        abort(HTTP_BAD_REQUEST)
    return jsonify({'Tags': response})


@app.route('/api/v1/tasks/tags/<task_id>', methods=['GET'])
@cross_origin()
def tags(task_id):
    '''
    Add/Remove the specified tag to the specified task.
    '''
    task = db.get_task(task_id)
    if not task:
        abort(HTTP_NOT_FOUND)

    add = request.args.get('add', '')
    if add:
        response = handler.add_tag(task.sample_id, add)
        if not response:
            abort(HTTP_BAD_REQUEST)
        return jsonify({'Message': 'Tag Added'})

    remove = request.args.get('remove', '')
    if remove:
        response = handler.remove_tag(task.sample_id, remove)
        if not response:
            abort(HTTP_BAD_REQUEST)
        return jsonify({'Message': 'Tag Removed'})


@app.route('/api/v1/tasks/<task_id>/notes', methods=['GET'])
@cross_origin()
def get_notes(task_id):
    '''
    Add an analyst note/comment to the specified task.
    '''
    task = db.get_task(task_id)
    if not task:
        abort(HTTP_NOT_FOUND)

    if ('ts' in request.args and 'uid' in request.args):
        ts = request.args.get('ts', '')
        uid = request.args.get('uid', '')
        response = handler.get_notes(task.sample_id, [ts, uid])
    else:
        response = handler.get_notes(task.sample_id)

    if not response:
        abort(HTTP_BAD_REQUEST)

    if 'hits' in response and 'hits' in response['hits']:
        response = response['hits']['hits']
    try:
        for hit in response:
            hit['_source']['text'] = Markup.escape(hit['_source']['text'])
    except:
        pass
    return jsonify(response)


@app.route('/api/v1/tasks/<task_id>/note', methods=['POST'])
@cross_origin()
def add_note(task_id):
    '''
    Add an analyst note/comment to the specified task.
    '''
    task = db.get_task(task_id)
    if not task:
        abort(HTTP_NOT_FOUND)

    response = handler.add_note(task.sample_id, request.form.to_dict())
    if not response:
        abort(HTTP_BAD_REQUEST)
    return jsonify(response)


@app.route('/api/v1/tasks/<task_id>/note/<note_id>/edit', methods=['POST'])
@cross_origin()
def edit_note(task_id, note_id):
    '''
    Modify the specified analyst note/comment.
    '''
    task = db.get_task(task_id)
    if not task:
        abort(HTTP_NOT_FOUND)

    response = handler.edit_note(task.sample_id, note_id,
                                 Markup(request.form['text']).striptags())
    if not response:
        abort(HTTP_BAD_REQUEST)
    return jsonify(response)


@app.route('/api/v1/tasks/<task_id>/note/<note_id>/delete', methods=['GET'])
@cross_origin()
def del_note(task_id, note_id):
    '''
    Delete an analyst note/comment from the specified task.
    '''
    task = db.get_task(task_id)
    if not task:
        abort(HTTP_NOT_FOUND)

    response = handler.delete_note(task.sample_id, note_id)
    if not response:
        abort(HTTP_BAD_REQUEST)
    return jsonify(response)


if __name__ == '__main__':

    db.init_db()

    if not os.path.isdir(api_config['api']['upload_folder']):
        print('Creating upload dir')
        os.makedirs(api_config['api']['upload_folder'])

    if not api_config['api']['distributed']:
        exit_signal = multiprocessing.Value('b')
        exit_signal.value = False
        ms_process = multiprocessing.Process(
            target=multiscanner_process,
            args=(work_queue, exit_signal)
        )
        ms_process.start()

    app.run(host=api_config['api']['host'], port=api_config['api']['port'])

    if not api_config['api']['distributed']:
        ms_process.join()

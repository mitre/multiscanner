#!/usr/bin/env python
'''
Flask app that provides a RESTful API to
the multiscanner.

Proposed supported operations:
GET / ---> Test functionality. {'Message': 'True'}
GET /api/v1/tasks/list  ---> Receive list of tasks in multiscanner
GET /api/v1/tasks/<task_id> ---> receive report in JSON format
GET /api/v1/tasks/delete/<task_id> ----> delete task_id
POST /api/v1/tasks/create ---> POST file and receive report id
Sample POST usage:
    curl -i -X POST http://localhost:8080/api/v1/tasks/create/ -F file=@/bin/ls

TODO:
* Add a backend DB to store reports
* Make this app agnostic to choice of backend DB
* Add doc strings to functions
'''
import os
import uuid
from flask import Flask, jsonify, make_response, request, abort

TASKS = [
    {'id': 1, 'report': {"/tmp/example.log": {"MD5": "53f43f9591749b8cae536ff13e48d6de", "SHA256": "815d310bdbc8684c1163b62f583dbaffb2df74b9104e2aadabf8f8491bafab66", "libmagic": "ASCII text"}}},
    {'id': 2, 'report': {"/opt/grep_in_mem.py": {"MD5": "96b47da202ddba8d7a6b91fecbf89a41", "SHA256": "26d11f0ea5cc77a59b6e47deee859440f26d2d14440beb712dbac8550d35ef1f", "libmagic": "a /bin/python script text executable"}}},
]

TASK_NOT_FOUND = {'Message': 'No task with that ID not found!'}
INVALID_REQUEST = {'Message': 'Invalid request parameters'}
UPLOAD_FOLDER = 'tmp/'

HTTP_OK = 200
HTTP_CREATED = 201
HTTP_BAD_REQUEST = 400
HTTP_NOT_FOUND = 404

app = Flask(__name__)


@app.errorhandler(HTTP_BAD_REQUEST)
def invalid_request(error):
    return make_response(jsonify(INVALID_REQUEST), HTTP_BAD_REQUEST)


@app.errorhandler(HTTP_NOT_FOUND)
def not_found(error):
    return make_response(jsonify(TASK_NOT_FOUND), HTTP_NOT_FOUND)


@app.route('/')
def index():
    return jsonify({'Message': 'True'})


@app.route('/api/v1/tasks/list/', methods=['GET'])
def task_list():
    return jsonify({'tasks': TASKS})


@app.route('/api/v1/tasks/list/<int:task_id>', methods=['GET'])
def get_task(task_id):
    task = [task for task in TASKS if task['id'] == task_id]
    if len(task) == 0:
        abort(HTTP_NOT_FOUND)
    return jsonify({'Message': task[0]})


@app.route('/api/v1/tasks/delete/<int:task_id>', methods=['GET'])
def delete_task(task_id):
    task = [task for task in TASKS if task['id'] == task_id]
    if len(task) == 0:
        abort(HTTP_NOT_FOUND)
    TASKS.remove(task[0])
    return jsonify({'Message': 'Deleted'})


@app.route('/api/v1/tasks/create/', methods=['POST'])
def create_task():
    file_ = request.files['file']
    extension = os.path.splitext(file_.filename)[1]
    f_name = str(uuid.uuid4()) + extension
    file_path = os.path.join(UPLOAD_FOLDER, f_name)
    file_.save(file_path)

    # TODO: save file to DB
    # TODO: run multiscan on the file, have it update the
    # DB when done
    # output = multiscanner.multiscan([file_path])
    # report = multiscanner.parseReports

    id = TASKS[-1]['id'] + 1
    TASKS.append({'id': id, 'report': 'pending'})
    return make_response(jsonify({'Message': {'task_id': id}}), HTTP_CREATED)

if __name__ == '__main__':
    if (not os.path.isdir(UPLOAD_FOLDER)):
        print 'Creating upload dir'
        os.makedirs(UPLOAD_FOLDER)
    app.run(host='0.0.0.0', port=8080, debug=True)

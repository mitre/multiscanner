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
'''

from flask import Flask, jsonify, make_response, request

TASKS = [
    {'id': 1, 'report': {"/tmp/example.log":{"MD5":"53f43f9591749b8cae536ff13e48d6de","SHA256":"815d310bdbc8684c1163b62f583dbaffb2df74b9104e2aadabf8f8491bafab66","libmagic":"ASCII text"}}},
    {'id': 2, 'report': {"/opt/qtip/grep_in_mem.py":{"MD5":"96b47da202ddba8d7a6b91fecbf89a41","SHA256":"26d11f0ea5cc77a59b6e47deee859440f26d2d14440beb712dbac8550d35ef1f","libmagic":"a /bin/python script text executable"}}},
]

TASK_NOT_FOUND = {'Message': 'No task with that ID not found!'}
INVALID_REQUEST = {'Message': 'Invalide request parameters'}

app = Flask(__name__)

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
        return make_response(jsonify(TASK_NOT_FOUND), 404)
    return jsonify({'Message': task[0]})


@app.route('/api/v1/tasks/delete/<int:task_id>', methods=['GET'])
def delete_task(task_id):
    task = [task for task in TASKS if task['id'] == task_id]
    if len(task) == 0:
        return make_response(jsonify(TASK_NOT_FOUND), 404)
    TASKS.remove(task[0])
    return jsonify({'Message': 'Deleted'})


@app.route('/api/v1/tasks/create/', methods=['POST'])
def create_task():
    if not request.json or not 'title' in request.json:
        make_response(jsonify(INVALID_REQUEST), 400)
    task = {
        'id': TASKS[-1]['id'] + 1,
        'report': request.json['report'],
    }
    TASKS.append(task)
    return jsonify({'Message': 'Added'}), 201

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)

#!/usr/bin/env python
'''
THIS APP IS NOT PRODUCTION READY!! DO NOT USE!

Flask app that provides a RESTful API to
the multiscanner.

Proposed supported operations:
GET / ---> Test functionality. {'Message': 'True'}
GET /api/v1/tasks/list  ---> Receive list of tasks in multiscanner
GET /api/v1/tasks/list/<task_id> ---> receive task in JSON format
GET /api/v1/reports/list/<report_id> ---> receive report in JSON
GET /api/v1/reports/delete/<report_id> ----> delete report_id
POST /api/v1/tasks/create ---> POST file and receive report id
Sample POST usage:
    curl -i -X POST http://localhost:8080/api/v1/tasks/create/ -F file=@/bin/ls

TODO:
* Add a backend DB to store reports
* Make this app agnostic to choice of backend DB
* Add doc strings to functions
'''
import os
import sys
import uuid
from flask import Flask, jsonify, make_response, request, abort

MS_WD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.join(MS_WD, 'storage') not in sys.path:
    sys.path.insert(0, os.path.join(MS_WD, 'storage'))


import sqlite_driver as database


TASK_NOT_FOUND = {'Message': 'No task with that ID not found!'}
INVALID_REQUEST = {'Message': 'Invalid request parameters'}
UPLOAD_FOLDER = 'tmp/'

HTTP_OK = 200
HTTP_CREATED = 201
HTTP_BAD_REQUEST = 400
HTTP_NOT_FOUND = 404

app = Flask(__name__)
db = database.Database()


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
def task_list():
    '''
    Return a JSON dictionary containing all the tasks
    in the DB.
    '''
    db = database.Database()

    return jsonify({'Tasks': db.get_all_tasks()})


@app.route('/api/v1/tasks/list/<int:task_id>', methods=['GET'])
def get_task(task_id):
    '''
    Return a JSON dictionary corresponding
    to the given task ID.
    '''
    task = db.get_task(task_id)
    if task:
        return jsonify({'Task': task})
    else:
        abort(HTTP_NOT_FOUND)


@app.route('/api/v1/tasks/delete/<int:task_id>', methods=['GET'])
def delete_task(task_id):
    '''
    Delete the specified task. Return deleted message.
    '''
    result = db.delete_task(task_id)
    if not result:
        abort(HTTP_NOT_FOUND)
    return jsonify({'Message': 'Deleted'})


@app.route('/api/v1/tasks/create/', methods=['POST'])
def create_task():
    '''
    Create a new task. Save the submitted file
    to UPLOAD_FOLDER. Return task id and 201 status.
    '''
    file_ = request.files['file']
    extension = os.path.splitext(file_.filename)[1]
    f_name = str(uuid.uuid4()) + extension
    file_path = os.path.join(UPLOAD_FOLDER, f_name)
    file_.save(file_path)

    # TODO: run multiscan on the file, have it update the
    # DB when done
    # output = multiscanner.multiscan([file_path])
    # report = multiscanner.parseReports

    task_id = db.add_task()
    return make_response(
        jsonify({'Message': {'task_id': task_id}}),
        HTTP_CREATED
    )


@app.route('/api/v1/reports/list/<int:report_id>', methods=['GET'])
def get_report(report_id):
    '''
    Return a JSON dictionary corresponding
    to the given report ID.
    '''
    report = [report for report in REPORTS if report['report_id'] == report_id]
    if len(report) == 0:
        abort(HTTP_NOT_FOUND)
    return jsonify({'Report': report[0]})


@app.route('/api/v1/reports/delete/<int:report_id>', methods=['GET'])
def delete_report(report_id):
    '''
    Delete the specified report. Return deleted message.
    '''
    report = [report for report in REPORTS if report['report_id'] == report_id]
    if len(report) == 0:
        abort(HTTP_NOT_FOUND)
    REPORTS.remove(report[0])
    return jsonify({'Message': 'Deleted'})


if __name__ == '__main__':

    db.init_sqlite_db()

    if not os.path.isdir(UPLOAD_FOLDER):
        print 'Creating upload dir'
        os.makedirs(UPLOAD_FOLDER)
    app.run(host='0.0.0.0', port=8080, debug=True)

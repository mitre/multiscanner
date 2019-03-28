#!/usr/bin/env python
'''
THIS APP IS NOT PRODUCTION READY!! DO NOT USE!

Flask app that provides a RESTful API to MultiScanner.

Supported operations:
GET / ---> Test functionality. {'Message': 'True'}
GET /api/v1/files/<sha256>?raw={t|f} ----> Download sample, defaults to passwd protected zip
GET /api/v1/modules ---> Receive list of modules available
GET /api/v1/tags ----> Receive list of all tags in use
GET /api/v1/tasks ---> Receive list of tasks in MultiScanner
POST /api/v1/tasks ---> POST file and receive report id
    Sample POST usage:
        curl -i -X POST http://localhost:8080/api/v1/tasks -F file=@/bin/ls
GET /api/v1/tasks/<task_id> ---> Receive task in JSON format
DELETE /api/v1/tasks/<task_id> ----> Delete task_id
GET /api/v1/tasks/search/ ---> Receive list of most recent report for matching samples
GET /api/v1/tasks/search/history ---> Receive list of most all reports for matching samples
GET /api/v1/tasks/sha256/<sha256> ---> Receive the task id for most recent scan of sample
GET /api/v1/tasks/<task_id>/file?raw={t|f} ----> Download sample, defaults to passwd protected zip
GET /api/v1/tasks/<task_id>/maec ----> Download the Cuckoo MAEC 5.0 report, if it exists
GET /api/v1/tasks/<task_id>/notes ---> Receive list of this task's notes
POST /api/v1/tasks/<task_id>/notes ---> Add a note to task
PUT /api/v1/tasks/<task_id>/notes/<note_id> ---> Edit a note
DELETE /api/v1/tasks/<task_id>/notes/<note_id> ---> Delete a note
GET /api/v1/tasks/<task_id>/report?d={t|f} ---> Receive report in JSON, set d=t to download
GET /api/v1/tasks/<task_id>/pdf ---> Receive PDF report
GET /api/v1/tasks/<task_id>/stix2?pretty={t|f}&custom_labels={string} ---> Receive STIX2 Bundle from report
POST /api/v1/tasks/<task_id>/tags ---> Add tags to task
DELETE /api/v1/tasks/<task_id>/tags ---> Remove tags from task
GET /api/v1/analytics/ssdeep_compare ---> Run ssdeep.compare analytic
GET /api/v1/analytics/ssdeep_group ---> Receive list of sample hashes grouped by ssdeep hash

The API endpoints all have Cross Origin Resource Sharing (CORS) enabled. By
default it will allow requests from any port on localhost. Change this setting
by modifying the 'cors' setting in the 'api' section of the api config file.

TODO:
* Add doc strings to functions
'''
from __future__ import print_function

import codecs
import configparser
import hashlib
import json
import multiprocessing
import os
import queue
import re
import shutil
import subprocess
import time
import uuid
import zipfile
from datetime import datetime

import rarfile
import requests
from flask import Flask, abort, jsonify, make_response, request, safe_join
from flask.json import JSONEncoder
from flask_cors import CORS
from jinja2 import Markup

# TODO: Why do we need to parseDir(MODULEDIR) multiple times?
from multiscanner import MODULESDIR, MS_WD, multiscan, parse_reports, CONFIG as MS_CONFIG
from multiscanner.common import utils, pdf_generator, stix2_generator
from multiscanner.config import PY3
from multiscanner.storage import StorageHandler
from multiscanner.storage import sql_driver as database
from multiscanner.storage.storage import StorageNotLoadedError


TASK_NOT_FOUND = {'Message': 'No task or report with that ID found!'}
INVALID_REQUEST = {'Message': 'Invalid request parameters'}

HTTP_OK = 200
HTTP_CREATED = 201
HTTP_BAD_REQUEST = 400
HTTP_NOT_FOUND = 404

DEFAULTCONF = {
    'host': 'localhost',
    'port': 8080,
    'upload_folder': '/mnt/samples/',
    'distributed': True,
    'web_loc': 'http://localhost:80',
    'cors': r'https?://localhost(:\d+)?',
    'batch_size': 100,
    'batch_interval': 60   # Number of seconds to wait for additional files
                           # submitted to the create/ API
}


# Customize timestamp format output of jsonify()
class CustomJSONEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            if obj.utcoffset() is not None:
                obj = obj - obj.utcoffset()
            return str(obj)
        else:
            return JSONEncoder.default(self, obj)


app = Flask(__name__)
app.json_encoder = CustomJSONEncoder
api_config_object = configparser.SafeConfigParser()
api_config_object.optionxform = str
# TODO: Why does this multiscanner.common instead of just common?
api_config_file = utils.get_config_path(MS_CONFIG, 'api')
api_config_object.read(api_config_file)
if not api_config_object.has_section('api') or not os.path.isfile(api_config_file):
    # Write default config
    api_config_object.add_section('api')
    for key in DEFAULTCONF:
        api_config_object.set('api', key, str(DEFAULTCONF[key]))
    conffile = codecs.open(api_config_file, 'w', 'utf-8')
    api_config_object.write(conffile)
    conffile.close()
api_config = utils.parse_config(api_config_object)

# TODO: fix this mess
# Needs api_config in order to function properly
from multiscanner.distributed.celery_worker import multiscanner_celery, ssdeep_compare_celery
from multiscanner.analytics.ssdeep_analytics import SSDeepAnalytic

db = database.Database(config=api_config.get('Database'))
# To run under Apache, we need to set up the DB outside of __main__
# Sleep and retry until database connection is successful
try:
    # wait this many seconds between tries
    db_sleep_time = int(api_config_object.get('Database', 'retry_time'))
except (configparser.NoSectionError, configparser.NoOptionError):
    db_sleep_time = database.Database.DEFAULTCONF['retry_time']
try:
    # max number of times to retry
    db_num_retries = int(api_config_object.get('Database', 'retry_num'))
except (configparser.NoSectionError, configparser.NoOptionError):
    db_num_retries = database.Database.DEFAULTCONF['retry_num']

for x in range(0, db_num_retries):
    try:
        db.init_db()
    except Exception as excinfo:
        db_error = excinfo
        print("ERROR: Can't connect to task database.", excinfo)
    else:
        break

    if db_error:
        if x == db_num_retries - 1:
            raise StorageNotLoadedError()
        print("Retrying...")
        time.sleep(db_sleep_time)

storage_conf = utils.get_config_path(MS_CONFIG, 'storage')
storage_handler = StorageHandler(configfile=storage_conf)
handler = storage_handler.load_required_module('ElasticSearchStorage')

ms_config_object = configparser.SafeConfigParser()
ms_config_object.optionxform = str
ms_configfile = MS_CONFIG
ms_config_object.read(ms_configfile)
ms_config = utils.parse_config(ms_config_object)

try:
    DISTRIBUTED = api_config['api']['distributed']
except KeyError:
    DISTRIBUTED = False

if not DISTRIBUTED:
    work_queue = multiprocessing.Queue()

try:
    cors_origins = api_config['api']['cors']
except KeyError:
    cors_origins = DEFAULTCONF['cors']
CORS(app, origins=cors_origins)

batch_size = api_config['api'].get('batch_size', 10)
batch_interval = api_config['api'].get('batch_interval', 100)
# Add `delete_after_scan = True` to api_config.ini to delete samples after scan has completed
delete_after_scan = api_config['api'].get('delete_after_scan', False)


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
            while len(metadata_list) < batch_size:
                metadata_list.append(work_queue.get_nowait())
        except queue.Empty:
            if metadata_list and time_stamp:
                if len(metadata_list) >= batch_size:
                    pass
                elif time.time() - time_stamp > batch_interval:
                    pass
                else:
                    continue
            else:
                continue

        filelist = [item[0] for item in metadata_list]
        # modulelist = [item[5] for item in metadata_list]
        resultlist = multiscan(
            filelist, configfile=MS_CONFIG
            # module_list
        )
        results = parse_reports(resultlist, python=True)

        scan_time = datetime.now().isoformat()

        if delete_after_scan:
            for file_name in results:
                os.remove(file_name)

        for item in metadata_list:
            # Use the original filename as the index instead of the full path
            results[item[1]] = results[item[0]]
            del results[item[0]]

            results[item[1]]['Scan Metadata'] = item[4]
            results[item[1]]['Scan Metadata']['Scan Time'] = scan_time
            results[item[1]]['Scan Metadata']['Task ID'] = item[2]
            results[item[1]]['tags'] = results[item[1]]['Scan Metadata'].get('Tags', '').split(',')
            results[item[1]]['Scan Metadata'].pop('Tags', None)

            db.update_task(
                task_id=item[2],
                task_status='Complete',
                timestamp=scan_time,
            )
        metadata_list = []

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


@app.route('/api/v1/modules', methods=['GET'])
def modules():
    '''
    Return a list of module names available for MultiScanner to use,
    and whether or not they are enabled in the config.
    '''
    files = utils.parseDir(MODULESDIR, True)
    filenames = [os.path.splitext(os.path.basename(f)) for f in files]
    module_names = [m[0] for m in filenames if m[1] == '.py']

    ms_config = configparser.SafeConfigParser()
    ms_config.optionxform = str
    ms_config.read(MS_CONFIG)
    modules = {}
    for module in module_names:
        try:
            modules[module] = ms_config.get(module, 'ENABLED')
        except (configparser.NoSectionError, configparser.NoOptionError):
            pass
    return jsonify({'Modules': modules})


@app.route('/api/v1/tasks', methods=['GET'])
def task_list():
    '''
    Return a JSON dictionary containing all the tasks
    in the tasks DB.
    '''

    return jsonify({'Tasks': db.get_all_tasks()})


def search(params, get_all=False):
    # Pass search term to Elasticsearch, get back list of sample_ids
    search_term = params.get('search[value]')
    search_type = params.pop('search_type', 'default')
    if not search_term:
        es_result = None
    else:
        es_result = handler.search(search_term, search_type)

    # Search the task db for the ids we got from Elasticsearch
    if get_all:
        return db.search(params, es_result, return_all=True)
    else:
        return db.search(params, es_result)


@app.route('/api/v1/tasks/search/history', methods=['GET'])
def task_search_history():
    '''
    Handle query between jQuery Datatables, the task DB, and Elasticsearch.
    Return all reports for matching samples.
    '''
    params = request.args.to_dict()
    resp = search(params, get_all=True)
    return jsonify(resp)


@app.route('/api/v1/tasks/search', methods=['GET'])
def task_search():
    '''
    Handle query between jQuery Datatables, the task DB, and Elasticsearch.
    Return only the most recent report for each of the matching samples.
    '''
    params = request.args.to_dict()
    resp = search(params)
    return jsonify(resp)


@app.route('/api/v1/tasks/<int:task_id>', methods=['GET'])
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


@app.route('/api/v1/tasks/sha256/<string:sha256>', methods=['GET'])
def get_task_sha256(sha256):
    '''
    Return the task ID number for the most recent scan of the sample with the
    given SHA256 hash.
    '''
    if re.match(r'^[a-fA-F0-9]{64}$', sha256):
        task_id = db.exists(sha256)
        if task_id:
            return make_response(
                jsonify({'TaskID': int(task_id)}),
                HTTP_OK)
        else:
            abort(HTTP_NOT_FOUND)
    else:
        abort(HTTP_BAD_REQUEST)


@app.route('/api/v1/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    '''
    Delete the specified task. Return deleted message.
    '''
    es_result = handler.delete_by_task_id(task_id)
    if not es_result:
        abort(HTTP_NOT_FOUND)
    sql_result = db.delete_task(task_id)
    if not sql_result:
        abort(HTTP_NOT_FOUND)
    return jsonify({'Message': 'Deleted'})


def save_hashed_filename(f, zipped=False):
    '''
    Save given file to the upload folder, with its SHA256 hash as its filename.
    '''
    f_name = hashlib.sha256(f.read()).hexdigest()
    # Reset the file pointer to the beginning to allow us to save it
    f.seek(0)

    # TODO: should we check if the file is already there
    # and skip this step if it is?
    file_path = os.path.join(api_config['api']['upload_folder'], f_name)
    full_path = os.path.join(MS_WD, file_path)
    if zipped:
        shutil.copy2(f.name, full_path)
    else:
        f.save(file_path)
    return (f_name, full_path)


class InvalidScanTimeFormatError(ValueError):
    pass


def import_task(file_):
    '''
    Import a JSON report that was downloaded from MultiScanner.
    '''
    report = json.loads(file_.read().decode('utf-8'))
    try:
        report['Scan Time'] = datetime.strptime(report['Scan Time'], '%Y-%m-%dT%H:%M:%S.%f')
    except ValueError:
        raise InvalidScanTimeFormatError()

    task_id = db.add_task(
        sample_id=report['SHA256'],
        task_status='Complete',
        timestamp=report['Scan Time'],
    )
    storage_handler.store({report['filename']: report}, wait=False)

    return task_id


def queue_task(original_filename, f_name, full_path, metadata, rescan=False):
    '''
    Queue up a single new task, for a single non-archive file.
    '''
    # If option set, or no scan exists for this sample, skip and scan sample again
    # Otherwise, pull latest scan for this sample
    if not rescan:
        t_exists = db.exists(f_name)
        if t_exists:
            return t_exists

    # Add task to sqlite DB
    # Make the sample_id equal the sha256 hash
    task_id = db.add_task(sample_id=f_name)

    if DISTRIBUTED:
        # Publish the task to Celery
        multiscanner_celery.delay(full_path, original_filename,
                                  task_id, f_name, metadata,
                                  config=MS_CONFIG)
    else:
        # Put the task on the queue
        work_queue.put((full_path, original_filename, task_id, f_name, metadata))

    return task_id


@app.route('/api/v1/tasks', methods=['POST'])
def create_task():
    '''
    Create a new task for a submitted file. Save the submitted file to
    UPLOAD_FOLDER, optionally unzipping it. Return task id and 201 status.
    '''
    file_ = request.files['file']
    if request.form.get('upload_type', None) == 'import':
        try:
            task_id = import_task(file_)
        except KeyError:
            return make_response(
                jsonify({'Message': 'Cannot import report missing \'Scan Time\' field!'}),
                HTTP_BAD_REQUEST)
        except InvalidScanTimeFormatError:
            return make_response(
                jsonify({'Message': 'Cannot import report with \'Scan Time\' of invalid format!'}),
                HTTP_BAD_REQUEST)
        except (UnicodeDecodeError, ValueError):
            return make_response(
                jsonify({'Message': 'Cannot import non-JSON files!'}),
                HTTP_BAD_REQUEST)

        return make_response(
            jsonify({'Message': {'task_ids': [task_id]}}),
            HTTP_CREATED
        )

    original_filename = file_.filename

    metadata = {}
    task_id_list = []
    extract_dir = None
    rescan = False
    for key in request.form.keys():
        if key in ['file_id', 'archive-password', 'upload_type'] or request.form[key] == '':
            continue
        elif key == 'duplicate':
            if request.form[key] == 'latest':
                rescan = False
            elif request.form[key] == 'rescan':
                rescan = True
        elif key == 'modules':
            module_names = request.form[key]
            files = utils.parseDir(MODULESDIR, True)
            modules = []
            for f in files:
                split = os.path.splitext(os.path.basename(f))
                if split[0] in module_names and split[1] == '.py':
                    modules.append(f)
        elif key == 'archive-analyze' and request.form[key] == 'true':
            extract_dir = api_config['api']['upload_folder']
            if not os.path.isdir(extract_dir):
                return make_response(
                    jsonify({'Message': "'upload_folder' in API config is not "
                             "a valid folder!"}),
                    HTTP_BAD_REQUEST)

            # Get password if present
            if 'archive-password' in request.form:
                password = request.form['archive-password']
                if PY3:
                    password = bytes(password, 'utf-8')
            else:
                password = ''
        else:
            metadata[key] = request.form[key]

    if extract_dir:
        # Extract a zip
        if zipfile.is_zipfile(file_):
            z = zipfile.ZipFile(file_)
            try:
                # NOTE: zipfile module prior to Py 2.7.4 is insecure!
                # https://docs.python.org/2/library/zipfile.html#zipfile.ZipFile.extract
                z.extractall(path=extract_dir, pwd=password)
                for uzfile in z.namelist():
                    unzipped_file = open(os.path.join(extract_dir, uzfile))
                    f_name, full_path = save_hashed_filename(unzipped_file, True)
                    tid = queue_task(uzfile, f_name, full_path, metadata, rescan=rescan)
                    task_id_list.append(tid)
            except RuntimeError as e:
                msg = "ERROR: Failed to extract " + str(file_) + ' - ' + str(e)
                return make_response(
                    jsonify({'Message': msg}),
                    HTTP_BAD_REQUEST)
        # Extract a rar
        elif rarfile.is_rarfile(file_):
            r = rarfile.RarFile(file_)
            try:
                r.extractall(path=extract_dir, pwd=password)
                for urfile in r.namelist():
                    unrarred_file = open(os.path.join(extract_dir, urfile))
                    f_name, full_path = save_hashed_filename(unrarred_file, True)
                    tid = queue_task(urfile, f_name, full_path, metadata, rescan=rescan)
                    task_id_list.append(tid)
            except RuntimeError as e:
                msg = "ERROR: Failed to extract " + str(file_) + ' - ' + str(e)
                return make_response(
                    jsonify({'Message': msg}),
                    HTTP_BAD_REQUEST)
    else:
        # File was not an archive to extract
        f_name, full_path = save_hashed_filename(file_)
        tid = queue_task(original_filename, f_name, full_path, metadata, rescan=rescan)
        task_id_list = [tid]

    msg = {'task_ids': task_id_list}
    return make_response(
        jsonify({'Message': msg}),
        HTTP_CREATED
    )


@app.route('/api/v1/tasks/<int:task_id>/report', methods=['GET'])
def get_report(task_id):
    '''
    Return a JSON dictionary corresponding
    to the given task ID.
    '''

    download = request.args.get('d', default='False', type=str)[0].lower()

    report_dict, success = get_report_dict(task_id)
    if success:
        if download == 't' or download == 'y' or download == '1':
            # raw JSON
            response = make_response(jsonify(report_dict))
            response.headers['Content-Type'] = 'application/json'
            response.headers['Content-Disposition'] = 'attachment; filename=%s.json' % task_id
            return response
        else:
            # processed JSON intended for web UI
            report_dict = _pre_process(report_dict)
            return jsonify(report_dict)
    else:
        return jsonify(report_dict)


def _pre_process(report_dict={}):
    '''
    Returns a JSON dictionary where a series of pre-processing steps are
    executed on report_dict.
    '''

    # TODO: create way to mark certain data as internal only (e.g., does
    # not need to be part of generated report)
    # pop unecessary keys
    if report_dict.get('Report', {}).get('ssdeep', {}):
        for k in ['chunksize', 'chunk', 'double_chunk']:
            try:
                report_dict['Report']['ssdeep'].pop(k)
            except KeyError as e:
                pass

    if report_dict.get('Report', {}).get('impfuzzy', {}):
        for k in ['chunksize', 'chunk', 'double_chunk']:
            try:
                report_dict['Report']['impfuzzy'].pop(k)
            except KeyError as e:
                pass

    report_dict = _add_links(report_dict)

    return report_dict


def _add_links(report_dict):
    '''
    Returns a JSON dictionary where certain keys and/or values are replaced
    with hyperlinks.
    '''

    web_loc = api_config['api']['web_loc']

    # ssdeep matches
    matches_dict = report_dict.get('Report', {}) \
                              .get('ssdeep', {}) \
                              .get('matches', {})

    if matches_dict:
        links_dict = {}
        # k=SHA256, v=ssdeep.compare result
        for k, v in matches_dict.items():
            t_id = db.exists(k)
            if t_id:
                url = '{h}/report/{t_id}'.format(h=web_loc, t_id=t_id)
                href = _linkify(k, url, True)
                links_dict[href] = v
            else:
                links_dict[k] = v

        # replace with updated dict
        report_dict['Report']['ssdeep']['matches'] = links_dict

    return report_dict


# TODO: should we move these helper functions to separate file?
def _linkify(s, url, new_tab=True):
    '''
    Return string s as HTML a tag with href pointing to url.
    '''

    return '<a{new_tab} href="{url}">{s}</a>'.format(
        new_tab=' target="_blank"' if new_tab else '',
        url=url,
        s=s)


@app.route('/api/v1/tasks/<int:task_id>/file', methods=['GET'])
def get_file_task(task_id):
    '''
    Download a single sample. Either raw binary or enclosed in a zip file.
    '''
    # try to get report dict
    report_dict, success = get_report_dict(task_id)
    if not success:
        return jsonify(report_dict)

    # okay, we have report dict; get sha256
    sha256 = report_dict.get('Report', {}).get('SHA256', '')
    if re.match(r'^[a-fA-F0-9]{64}$', sha256):
        return files_get_sha256_helper(
                sha256,
                request.args.get('raw', default='f'))
    else:
        return jsonify({'Error': 'sha256 invalid or not in report!'})


@app.route('/api/v1/tasks/files', methods=['GET'])
def get_files_task():
    '''
    Given a comma-separated list of task ids. Download the samples enclosed in a zip file.
    '''
    task_ids = request.args.get('task_ids', default=None)

    if task_ids is not None:
        task_ids = task_ids.split(',')
        uuidv4 = str(uuid.uuid4())
        zipname = uuidv4 + '.zip'
        zip_command = ['/usr/bin/zip', '-j',
                       safe_join('/tmp', zipname),
                       '-P', 'infected']

        try:
            for t in task_ids:
                value = int(t)
                if value <= 0:
                    raise ValueError

                try:
                    sha256 = db.get_task(t).sample_id
                except AttributeError:
                    return make_response(
                            jsonify({'Error': 'Task {} not found!'.format(t)}),
                            HTTP_NOT_FOUND)

                if re.match(r'^[a-fA-F0-9]{64}$', sha256):
                    file_path = safe_join(api_config['api']['upload_folder'], sha256)
                    if not os.path.exists(file_path):
                        abort(HTTP_NOT_FOUND)

                    with open(file_path, 'rb') as fh:
                        fh_content = fh.read()

                    rawname = sha256 + '.bin'
                    with open(safe_join('/tmp/', rawname), 'wb') as raw_fh:
                        raw_fh.write(fh_content)

                    zip_command.insert(3, safe_join('/tmp', rawname))
                else:
                    return jsonify({'Error': 'sha256 invalid!'})
        except ValueError:
            abort(HTTP_BAD_REQUEST)

        proc = subprocess.Popen(zip_command)
        wait_seconds = 30

        while proc.poll() is None and wait_seconds:
            time.sleep(1)
            wait_seconds -= 1

        if proc.returncode:
            return make_response(jsonify({'Error': 'Failed to create zip ()'.format(proc.returncode)}))
        elif not wait_seconds:
            proc.terminate()
            return make_response(jsonify({'Error': 'Process timed out'}))
        else:
            with open(safe_join('/tmp', zipname), 'rb') as zip_fh:
                zip_data = zip_fh.read()
            if len(zip_data) == 0:
                return make_response(jsonify({'Error': 'Zip file empty'}))
            response = make_response(zip_data)
            response.headers['Content-Type'] = 'application/zip; charset=UTF-8'
            response.headers['Content-Disposition'] = 'inline; filename={}.zip'.format(uuidv4)
            return response
    else:
        return jsonify({'Error': 'empty request'})


@app.route('/api/v1/tasks/<int:task_id>/maec', methods=['GET'])
def get_maec_report(task_id):
    # try to get report dict
    report_dict, success = get_report_dict(task_id)
    if not success:
        return jsonify(report_dict)

    # okay, we have report dict; get cuckoo task ID
    try:
        cuckoo_task_id = report_dict['Report']['Cuckoo Sandbox']['info']['id']
    except KeyError:
        return jsonify({'Error': 'No MAEC report found for that task!'})

    # Get the MAEC report from Cuckoo
    try:
        maec_report = requests.get(
            '{}/v1/tasks/report/{}/maec'.format(ms_config.get('Cuckoo', {}).get('API URL', ''), cuckoo_task_id)
        )
    except Exception as e:
        # TODO: log exception
        return jsonify({'Error': 'No MAEC report found for that task!'})
    # raw JSON
    response = make_response(jsonify(maec_report.json()))
    response.headers['Content-Type'] = 'application/json'
    response.headers['Content-Disposition'] = 'attachment; filename=%s.json' % task_id
    return response


def get_report_dict(task_id):
    task = db.get_task(task_id)
    if not task:
        abort(HTTP_NOT_FOUND)

    if task.task_status == 'Complete':
        result = handler.get_report(task.sample_id, task.timestamp)
        if result:
            return {'Report': result}, True
        else:
            return {'Report': 'Error occurred in ElasticSearch'}, False
    elif task.task_status == 'Pending':
        return {'Report': 'Task still pending'}, False
    else:
        return {'Report': 'Task failed'}, False


@app.route('/api/v1/tags/', methods=['GET'])
def taglist():
    '''
    Return a list of all tags currently in use.
    '''
    response = handler.get_tags()
    return jsonify({'Tags': response})


@app.route('/api/v1/tasks/<int:task_id>/tags', methods=['POST', 'DELETE'])
def tags(task_id):
    '''
    Add/Remove the specified tag to the specified task.
    '''
    task = db.get_task(task_id)
    if not task:
        abort(HTTP_NOT_FOUND)

    tag = request.values.get('tag', '')

    if request.method == 'POST':
        response = handler.add_tag(task.sample_id, tag)
        if not response:
            abort(HTTP_BAD_REQUEST)
        return jsonify({'Message': 'Tag Added'})

    elif request.method == 'DELETE':
        response = handler.remove_tag(task.sample_id, tag)
        if not response:
            abort(HTTP_BAD_REQUEST)
        return jsonify({'Message': 'Tag Removed'})


@app.route('/api/v1/tasks/<int:task_id>/notes', methods=['GET'])
def get_notes(task_id):
    '''
    Get one or more analyst notes/comments associated with the specified task.
    '''
    task = db.get_task(task_id)
    if not task:
        abort(HTTP_NOT_FOUND)

    if 'ts' in request.args and 'uid' in request.args:
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
    except Exception as e:
        # TODO: log exception
        pass
    return jsonify(response)


@app.route('/api/v1/tasks/<int:task_id>/notes', methods=['POST'])
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


@app.route('/api/v1/tasks/<int:task_id>/notes/<string:note_id>', methods=['PUT', 'DELETE'])
def edit_note(task_id, note_id):
    '''
    Modify/remove the specified analyst note/comment.
    '''
    task = db.get_task(task_id)
    if not task:
        abort(HTTP_NOT_FOUND)

    if request.method == 'PUT':
        response = handler.edit_note(task.sample_id, note_id,
                                     Markup(request.form.get('text', '')).striptags())
    elif request.method == 'DELETE':
        response = handler.delete_note(task.sample_id, note_id)

    if not response:
        abort(HTTP_BAD_REQUEST)
    return jsonify(response)


@app.route('/api/v1/files/<string:sha256>', methods=['GET'])
# get raw file - /api/v1/files/get/<sha256>?raw=true
def files_get_sha256(sha256):
    '''
    Returns binary from storage. Defaults to password protected zipfile.
    '''
    # is there a robust way to just get this as a bool?
    raw = request.args.get('raw', default='f', type=str)

    if re.match(r'^[a-fA-F0-9]{64}$', sha256):
        return files_get_sha256_helper(sha256, raw)
    else:
        return abort(HTTP_BAD_REQUEST)


def files_get_sha256_helper(sha256, raw='f'):
    '''
    Returns binary from storage. Defaults to password protected zipfile.
    '''
    file_path = safe_join(api_config['api']['upload_folder'], sha256)
    if not os.path.exists(file_path):
        abort(HTTP_NOT_FOUND)

    with open(file_path, 'rb') as fh:
        fh_content = fh.read()

    raw = str(raw)[0].lower()
    if raw in ['t', 'y', '1']:
        response = make_response(fh_content)
        response.headers['Content-Type'] = 'application/octet-stream; charset=UTF-8'
        # better way to include fname?
        response.headers['Content-Disposition'] = 'inline; filename={}.bin'.format(sha256)
    else:
        # ref: https://github.com/crits/crits/crits/core/data_tools.py#L122
        rawname = sha256 + '.bin'
        with open(safe_join('/tmp/', rawname), 'wb') as raw_fh:
            raw_fh.write(fh_content)

        zipname = sha256 + '.zip'
        args = ['/usr/bin/zip', '-j',
                safe_join('/tmp', zipname),
                safe_join('/tmp', rawname),
                '-P', 'infected']
        proc = subprocess.Popen(args)
        wait_seconds = 30
        while proc.poll() is None and wait_seconds:
            time.sleep(1)
            wait_seconds -= 1

        if proc.returncode:
            return make_response(jsonify({'Error': 'Failed to create zip ()'.format(proc.returncode)}))
        elif not wait_seconds:
            proc.terminate()
            return make_response(jsonify({'Error': 'Process timed out'}))
        else:
            with open(safe_join('/tmp', zipname), 'rb') as zip_fh:
                zip_data = zip_fh.read()
            if len(zip_data) == 0:
                return make_response(jsonify({'Error': 'Zip file empty'}))
            response = make_response(zip_data)
            response.headers['Content-Type'] = 'application/zip; charset=UTF-8'
            response.headers['Content-Disposition'] = 'inline; filename={}.zip'.format(sha256)
    return response


@app.route('/api/v1/analytics/ssdeep_compare', methods=['GET'])
def run_ssdeep_compare():
    '''
    Runs ssdeep compare analytic and returns success / error message.
    '''
    try:
        if DISTRIBUTED:
            # Publish task to Celery
            ssdeep_compare_celery.delay()
            return make_response(jsonify({'Message': 'Success'}))
        else:
            ssdeep_analytic = SSDeepAnalytic()
            ssdeep_analytic.ssdeep_compare()
            return make_response(jsonify({'Message': 'Success'}))
    except Exception as e:
        return make_response(
            jsonify({'Message': 'Unable to complete request.'}),
            HTTP_BAD_REQUEST)


@app.route('/api/v1/analytics/ssdeep_group', methods=['GET'])
def run_ssdeep_group():
    '''
    Runs ssdeep group analytic and returns list of groups as a list.
    '''
    try:
        ssdeep_analytic = SSDeepAnalytic()
        groups = ssdeep_analytic.ssdeep_group()
        return make_response(jsonify({'groups': groups}))
    except Exception as e:
        return make_response(
            jsonify({'Message': 'Unable to complete request.'}),
            HTTP_BAD_REQUEST)


@app.route('/api/v1/tasks/<int:task_id>/pdf', methods=['GET'])
def get_pdf_report(task_id):
    '''
    Generates a PDF version of a JSON report.
    '''
    report_dict, success = get_report_dict(task_id)

    if not success:
        return jsonify(report_dict)

    pdf = pdf_generator.create_pdf_document(MS_CONFIG, report_dict)
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=%s.pdf' % task_id
    return response


@app.route('/api/v1/tasks/<int:task_id>/stix2', methods=['GET'])
def get_stix2_bundle_from_report(task_id):
    '''
    Generates a STIX2 Bundle with indicators generated of a JSON report.

    custom labels must be comma-separated.
    '''
    report_dict, success = get_report_dict(task_id)

    if not success:
        return jsonify(report_dict)

    formatting = request.args.get('pretty', default='False', type=str)[0].lower()
    custom_labels = request.args.get('custom_labels', default='', type=str).split(",")

    if formatting == 't' or formatting == 'y' or formatting == '1':
        formatting = True
    else:
        formatting = False

    # If list is empty or any entry in the list is empty -> clear labels
    if custom_labels or all(custom_labels) is False:
        custom_labels = []

    # If the report has no key/value pairs that we can use to create
    # STIX representations of this data. The default behavior is to return
    # an empty bundle.
    bundle = stix2_generator.parse_json_report_to_stix2_bundle(report_dict, custom_labels)

    # Setting pretty=True can be an expensive operation!
    response = make_response(bundle.serialize(pretty=formatting))
    response.headers['Content-Type'] = 'application/json'
    response.headers['Content-Disposition'] = 'attachment; filename=%s_bundle_stix2.json' % task_id
    return response


def _main():
    if not os.path.isdir(api_config['api']['upload_folder']):
        print('Creating upload dir')
        os.makedirs(api_config['api']['upload_folder'])

    if not DISTRIBUTED:
        exit_signal = multiprocessing.Value('b')
        exit_signal.value = False
        ms_process = multiprocessing.Process(
            target=multiscanner_process,
            args=(work_queue, exit_signal)
        )
        ms_process.start()

    app.run(host=api_config['api']['host'], port=api_config['api']['port'])

    if not DISTRIBUTED:
        ms_process.join()


if __name__ == '__main__':
    _main()

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/
'''
Scanning module to interact with OPSWAT Metadefender Core 4 Version 3.x.
The scan() method submits a set of files to the Metadefender REST
API, and then polls Metadefender for the scan results.
Notes on special configuration options:
    'fetch delay seconds': the number of seconds for the module to
        wait between submitting all samples and polling for scan results.
        Increase this value if Metadefender is taking a long time to store
        the samples
    'poll interval seconds': the number of seconds between successive
        queries to Metadefender for scan results
    The value of ('fetch delay seconds' + 'poll interval seconds')
    should be less than ('timeout' + 'running timeout')
'''
from __future__ import division, absolute_import, with_statement, print_function, unicode_literals
import requests
import time
from multiscanner.common.utils import basename

__author__ = "Julian Feild"
__license__ = "MPL 2.0"

TYPE = "Antivirus"
NAME = "Metadefender"
DEFAULTCONF = {
    "ENABLED": False,
    "API URL": 'http://metadefender:8008/',
    "timeout": 60,
    "running timeout": 30,
    "fetch delay seconds": 5,
    "poll interval seconds": 5,
    "user agent": "user_agent",
    "API key": ""
}

PERCENT_SCAN_COMPLETE = 100
MD_SCAN_RES_CODES = {0: 'No threats Found', 1: 'Infected/Known',
                     2: 'Suspicious', 3: 'Failed to Scan',
                     4: 'Cleaned/Deleted', 5: 'Unknown',
                     6: 'Quarantined', 7: 'Skipped - Clean',
                     8: 'Skipped - Infected', 9: 'Exceeded Archive Depth',
                     10: 'Not Scanned/No Scan Results', 11: 'Aborted',
                     12: 'Encrypted', 13: 'Exceeded Archive Size',
                     14: 'Exceeded Archive File Number',
                     15: 'Password Protected', 16: 'Exceeded Archive Timeout'}
MD_UNKNOWN_SCAN_RES = 5
MD_HTTP_ERR_CODES = {400: 'Unsupported HTTP Method or invalid HTTP Request',
                     401: 'API key is missing or invalid',
                     404: 'Scan result not found',
                     500: 'Server temporarily unavailable'
                     }
UNKNOWN_ERROR = 'Unknown Error'
STATUS_SUCCESS = 'Success'
STATUS_FAIL = 'Failure'
STATUS_PENDING = 'Pending'
STATUS_TIMEOUT = 'Timeout'


def check(conf=DEFAULTCONF):
    return conf["ENABLED"]


def _parse_scan_result(response):
    '''
    Parses the Response object returned by the call to requests.get()
    for the scan result.
    Parameters:
        response - requests.Response object returned by
            _retrieve_scan_results()
    Returns:
        tuple(is_complete, scan_output) where:
            is_complete = boolean indicating if the scan has completed
            scan_output = dictionary in the form:
            {
                overall_status: 'Success|Pending|Failure',
                msg: '<Error message/status explanation
                    if status is not 'Success'>'|''
                engine_results: [
                    {
                        engine_name: '<Engine Name>',
                        threat_found: '<Threat Name>'|'',
                        scan_result: '<Value from MD_SCAN_RES_CODES>'
                    },
                    ...
                ]
            }
            if is_completed is False, then scan_output will be None
    '''
    status_code = response.status_code

    if status_code == requests.codes.ok:
        response_json = response.json()
        process_info = response_json.get('process_info', {})
        prog_percent = process_info.get('progress_percentage', None)

        # Metadefender returns a 200 rather than a 404 if there's no scan
        # result, so we have to check the output for a progress percentage.
        # No results could mean that MD simply hasn't begun processing so
        # we don't want to mark the scan as failed
        if prog_percent is None:
            is_complete = False
            overall_status = STATUS_PENDING
            msg = 'Scan results not found; Metadefender has likely not started analysis yet'
            engine_results = []
        elif prog_percent < PERCENT_SCAN_COMPLETE:
            is_complete = False
            overall_status = STATUS_PENDING
            msg = 'Scan in progress, percent complete: %d' % prog_percent
            engine_results = []
        else:
            is_complete = True
            overall_status = STATUS_SUCCESS
            msg = ''
            overall_results = response_json.get("scan_results", {})
            scan_details = overall_results.get("scan_details", {})
            engine_results = []
            for engine_name, engine_output in scan_details.items():
                scan_code = engine_output.get("scan_result_i", MD_UNKNOWN_SCAN_RES)
                scan_result_string = MD_SCAN_RES_CODES[scan_code]
                engine_result = {'engine_name': engine_name,
                                 'threat_found': engine_output.get('threat_found', ''),
                                 'scan_result': scan_result_string
                                 }
                engine_results.append(engine_result)
    else:
        is_complete = True
        overall_status = STATUS_FAIL
        try:
            response_json = response.json()
            msg = response_json.get('err', MD_HTTP_ERR_CODES.get(status_code,
                                                                       UNKNOWN_ERROR))
        # It's possible (though unlikely) that no JSON response was returned
        except ValueError:
            msg = 'No data received from Metadefender'
        engine_results = []

    scan_result = {
        'overall_status': overall_status,
        'msg': msg,
        'engine_results': engine_results
    }
    return (is_complete, scan_result)


def _submit_sample(fname, scan_url, user_agent, api_key=None):
    '''
    Submits the specified sample file to Metadefender and returns
    Metadefender's response.
    Parameters:
        fname - sample file name
        scan_url - API URL for scan submission
        user_agent - Metadefender user agent string
    Returns:
        Dictionary in the form:
        {
            status_code: <HTTP status code>,
            scan_id: <scan ID if present> | None,
            error: <error message if present> | None
        }
    '''
    with open(fname, "rb") as sample:
        # TODO - send file in chunks if file size > some threshold.
        # Due to MD's API, we would have to split the file up manually
        # and perform several POSTS
        headers = {'content-type': 'application/json',
                   'user_agent': user_agent,
                   'filename': basename(fname)}
        if api_key:
            headers['apikey'] = api_key
        request = requests.post(scan_url, data=sample, headers=headers)
    resp_status_code = request.status_code
    if resp_status_code == requests.codes.ok:
        resp_json = request.json()
        scan_id = resp_json.get('data_id', None)
        error_msg = None
    else:
        scan_id = None
        try:
            resp_json = request.json()
            error_msg = resp_json.get('err', MD_HTTP_ERR_CODES.get(resp_status_code,
                                                               UNKNOWN_ERROR))
        except (ValueError, AttributeError):
            error_msg = MD_HTTP_ERR_CODES.get(resp_status_code, UNKNOWN_ERROR)

    submission_response = {
        'status_code': resp_status_code,
        'scan_id': scan_id,
        'error': error_msg
    }
    return submission_response


def _retrieve_scan_results(results_url, scan_id, api_key=None):
    '''
    Retrieves the results of a scan from Metadefender.
    Parameters:
        results_url - API URL for result retrieval
        scan_id - scan ID returned my Metadefender on sample submission
    Returns:
        requests.Response object
    '''
    headers = None
    if api_key:
        headers = {'apikey': api_key}
    scan_output = requests.get(results_url + scan_id, headers=headers)
    return scan_output


def scan(filelist, conf=DEFAULTCONF):
    '''
    Submits all the files in filelist to the Metadefender API, and then
    polls Metadefender after submission to retrieve the scan results.
    Parameters:
        filelist - list of filenames to be scanned
        conf - module configuration
    Returns:
        tuple(resultlist, metadata) where:
            resultlist = list of scan results, one per file. Each result is
                a dictionary in the form of the scan_output dictionary returned
                by _parse_scan_result()
            metadata = module metadata (name, type)
    '''
    fetch_delay_seconds = conf['fetch delay seconds']
    poll_interval_seconds = conf['poll interval seconds']
    api_key = conf['API key']
    if api_key.strip() == '':
        api_key = None

    resultlist = []
    tasks = []
    if conf['API URL'].endswith('/'):
        url = conf['API URL']
    else:
        url = conf['API URL'] + '/'
    scan_url = url + 'metascan_rest/file'
    results_url = url + 'metascan_rest/file/'

    user_agent = conf['user agent']
    for fname in filelist:
        submission_resp = _submit_sample(fname, scan_url, user_agent, api_key)
        resp_status_code = submission_resp['status_code']
        if resp_status_code == requests.codes.ok:
            task_id = submission_resp['scan_id']
            if task_id is not None:
                tasks.append((fname, str(task_id)))
            else:
                # TODO Do something here?
                pass
        else:
            err_msg = submission_resp['error']
            print('%s: %s not submitted: Code: %d, Message: %s'
                  % (NAME, basename(fname), resp_status_code, err_msg))

    # Wait for tasks to finish
    time.sleep(fetch_delay_seconds)
    task_status = {}
    while tasks:
        for fname, task_id in tasks[:]:
            scan_output = _retrieve_scan_results(results_url, task_id, api_key)
            is_scan_complete, scan_result = _parse_scan_result(scan_output)

            # If we have a report
            if is_scan_complete:
                resultlist.append((fname, scan_result))
                tasks.remove((fname, task_id))

            # Check for dead tasks
            else:
                if task_id not in task_status:
                    task_status[task_id] = time.time() + conf['timeout'] + conf['running timeout']
                else:
                    if time.time() > task_status[task_id]:
                        # Log timeout
                        if scan_result['overall_status'] == STATUS_PENDING:
                            scan_result['overall_status'] = STATUS_TIMEOUT
                        resultlist.append((fname, scan_result))
                        tasks.remove((fname, task_id))

        time.sleep(poll_interval_seconds)

    metadata = {}
    metadata["Name"] = NAME
    metadata["Type"] = TYPE
    metadata["Include"] = False
    return (resultlist, metadata)

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/
from __future__ import division, absolute_import, with_statement, print_function, unicode_literals
import requests
import time
# from common import basename
from boltons.iterutils import remap


__author__ = 'Austin West'
__license__ = 'MPL 2.0'

TYPE = 'Detonation'
NAME = 'VxStream Sandbox'
DEFAULTCONF = {
    'ENABLED': False,
    'BASE URL': 'http://localhost',
    'API URL': 'http://localhost/api/',
    'API key': '',
    'API secret': '',
    'Environment ID': 1,
    'Verify': False,
    'timeout': 360,
    'running timeout': 120,
}
EMPTY_STR_TO_OBJ = {
    'runtime': [
        'additionalContext',
        'apidb',
        'chronology',
        'console',
        'handles',
        'hooks',
        'mutants',
        'network',
        'parameterdb',
        'vbeevents',
        'createdfiles',
    ],
    'hybridanalysis': [
        'streams',
    ],
    'final': [
        'business_threats',
        'signatures_chronology',
        'engines',
        'delayed',
        'multiscan',
        'warnings',
        'similarity',
        'imageprocessing',
    ],
    'general': [
        'yarahits',
        'exec_options',
        'verinfo',
        'tls_callbacks',
        'resources',
        'exports',
        'certificate',
        'dictionary',
    ],
}
EMPTY_STR_TO_LS = {
    'runtime': [
        'targets', ],
    'hybridanalysis': [
        'targets',
        'dropped', ],
}

# we could use the full path of the keys
# known to cause issues


def visit(path, key, value):
    if value == '':
        if key in EMPTY_STR_TO_OBJ['runtime'] or \
           key in EMPTY_STR_TO_OBJ['hybridanalysis'] or \
           key in EMPTY_STR_TO_OBJ['final'] or \
           key in EMPTY_STR_TO_OBJ['general']:
            # null values should be empty dict
            return key, {}
        elif key in EMPTY_STR_TO_LS['runtime'] or \
             key in EMPTY_STR_TO_LS['hybridanalysis']:
            # null values should be empty list
            return key, []
    elif 'runtime' in path and key == 'parentuid':
        # first parentuid is always int, rest are strings...
        return key, str(value)
    elif key == 'netsim' and type(value) == int:
        # sometimes uses 0 / 1 for false / true,
        # make everything string
        return key, str(bool(value)).lower()
    elif '_entropy' in str(key) and type(value) == str:
        # entropy shows up as float and str,
        # make all of them floats
        return key, float(value)
    return key, value


def post_to_vxstream(f_name, environment_id,
        submit_url, apikey, secret, runtime, verify):
    with open(f_name, 'rb') as f:
        files = {'file': f}
        data = {
            'apikey': apikey,
            'secret': secret,
            'environmentId': environment_id,
            'customruntime': runtime,
        }
        try:
            user_agent = {'User-agent': 'VxStream Sandbox'}
            res = requests.post(submit_url, data=data, headers=user_agent, files=files, verify=verify)
            if res.status_code == 200:
                return res.json()
            else:
                print('Error code: {}, returned when uploading: {}'.format(res.status_code, f.name))
        except requests.exceptions.HTTPError as err:
            print(err)


def get_file_status(file_sha256, status_url, environment_id, apikey, secret, verify):
    user_agent = {'User-agent': 'VxStream Sandbox'}
    params = {'apikey': apikey, 'secret': secret, 'environmentId': environment_id}
    resource_url = '%s/%s' % (status_url, file_sha256)

    try:
        res = requests.get(resource_url, headers=user_agent, params=params, verify=verify)
        if res.status_code == 200:
            return res.json()

        else:
            print('Error code: {}, returned when getting file status: {}'.format(res.status_code, file_sha256))
            return res
    except requests.exceptions.HTTPError as err:
        print(err)


def get_file_report(file_sha256, report_url, environment_id, type_, apikey, secret, verify):
    user_agent = {'User-agent': 'VxStream Sandbox'}
    params = {'apikey': apikey, 'secret': secret, 'environmentId': environment_id, 'type': type_}
    resource_url = '%s/%s' % (report_url, file_sha256)

    try:
        res = requests.get(resource_url, headers=user_agent, params=params, verify=verify)
        if res.status_code == 200:
            # walk entire json blob to fix
            # the keys known to cause issues
            remapped = remap(res.json(), visit=visit)
            return remapped
        else:
            print('Error code: {}, returned when getting report: {}'.format(res.status_code, file_sha256))
            return res
    except requests.exceptions.HTTPError as err:
        print(err)


def check(conf=DEFAULTCONF):
    return conf['ENABLED']


def scan(filelist, conf=DEFAULTCONF):
    resultlist = []
    tasks = []

    if conf['API URL'].endswith('/'):
        url = conf['API URL']
    else:
        url = conf['API URL'] + '/'

    submit_url = url + 'submit'
    status_url = url + 'state'
    report_url = url + 'result'

    for fname in filelist:
        response = post_to_vxstream(
            fname, environment_id=conf['Environment ID'],
            submit_url=submit_url, apikey=conf['API key'],
            secret=conf['API secret'], runtime=conf['running timeout'],
            verify=conf['Verify'])
        try:
            file_sha256 = response['response']['sha256']
        except Exception as e:
            print(e, fname)
            continue
        if file_sha256 is not None:
            tasks.append((fname, file_sha256))

    # Wait for tasks to finish
    task_status = {}
    while tasks:
        for fname, file_sha256 in tasks[:]:
            status_dict = get_file_status(
                file_sha256, status_url, conf['Environment ID'],
                apikey=conf['API key'], secret=conf['API secret'],
                verify=conf['Verify']
            )
            status = status_dict.get('response', {}).get('state', 'ERROR')

            # If we have a report
            if status == 'SUCCESS':
                report = get_file_report(
                    file_sha256, report_url, conf['Environment ID'],
                    apikey=conf['API key'], secret=conf['API secret'],
                    type_='json', verify=conf['Verify']
                )
                if report:
                    # Drop some additional values from report
                    for field in ['strings', 'signatures_chronology',
                                  'imageprocessing', 'multiscan']:
                        try:
                            report['analysis']['final'].pop(field)
                        except KeyError:
                            pass
                    # Add the link to Web Report
                    report['analysis']['final']['web_report'] = (
                        '<a href="{base_url}/sample/{file_sha256}?environmentId={env_id}" target="_blank">'
                        'View the report in VxStream</a>'
                    ).format(base_url=conf['BASE URL'], file_sha256=file_sha256, env_id=conf['Environment ID'])
                    resultlist.append((fname, report.get('analysis', {}).get('final')))
                    tasks.remove((fname, file_sha256))

            # Check for dead tasks
            elif status == 'IN_PROGRESS':
                if file_sha256 not in task_status:
                    task_status[file_sha256] = time.time() + conf['timeout'] + conf['running timeout']
                else:
                    if time.time() > task_status[file_sha256]:
                        # TODO Log timeout
                        tasks.remove((fname, file_sha256))

            # If there is an unknown status
            elif status == 'ERROR':
                # TODO Log errors better
                tasks.remove((fname, file_sha256))
        time.sleep(15)

    metadata = {}
    metadata["Name"] = NAME
    metadata["Type"] = TYPE
    metadata["Include"] = False
    return (resultlist, metadata)

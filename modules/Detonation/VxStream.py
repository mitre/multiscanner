# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/
from __future__ import division, absolute_import, with_statement, print_function, unicode_literals
import requests
import json
import time
# from common import basename
from collections import Counter


__author__ = 'Austin West'
__license__ = 'MPL 2.0'

TYPE = 'Detonation'
NAME = 'VxStream Sandbox'
DEFAULTCONF = {
    'ENABLED': False,
    'API URL': 'http://localhost/api/',
    'API key': '',
    'API secret': '',
    'Environment ID': 1,
    'Verify': False,
    'timeout': 360,
    'running timeout': 120,
}


def post_to_vxstream(
        f_name, environment_id,
        submit_url, apikey, secret, verify):
    with open(f_name, 'rb') as f:
        files = {'file': f}
        data = {'apikey': apikey, 'secret': secret, 'environmentId': environment_id}
        try:
            user_agent = {'User-agent': 'VxStream Sandbox'}
            res = requests.post(submit_url, data=data, headers=user_agent, files=files, verify=verify)
            if res.status_code == 200:
                return res.json()
            else:
                print('Error code: {}, returned when uploading: {}'.format(res.status_code, f.name))
        except requests.exceptions.HTTPError as err:
            print(err)
            #traceback.print_exc()


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
            return res.json()
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
            submit_url=submit_url, apikey=conf['API key'], secret=conf['API secret'],
            verify=conf['Verify'])
        try:
            file_sha256 = response['response']['sha256']
        except KeyError as e:
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
                    resultlist.append((fname, report))
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

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/
from __future__ import division, absolute_import, with_statement, print_function, unicode_literals
import requests
import json
import time
from multiscanner.common.utils import basename

__author__ = "Drew Bonasera"
__license__ = "MPL 2.0"

TYPE = "Detonation"
NAME = "Cuckoo Sandbox"
DEFAULTCONF = {
    "ENABLED": False,
    "API URL": 'http://cuckoo:8090/',
    "WEB URL": 'http://cuckoo:80/',
    "timeout": 360,
    "running timeout": 120,
    "delete tasks": False,
    "maec": False,
}


def fetch_report_json(report_url):
    report = requests.get(report_url)
    if report.status_code == 200:
        return report.json()
    return {}


def normalize_url(url):
    """Removes trailing '/' from url.
    """
    if url.endswith('/'):
        return url[:-1]
    return url


def check(conf=DEFAULTCONF):
    return conf["ENABLED"]


def scan(filelist, conf=DEFAULTCONF):
    resultlist = []
    tasks = []

    api_url = normalize_url(conf['API URL'])
    web_url = normalize_url(conf['WEB URL'])

    new_file_url = api_url + 'tasks/create/file'
    report_url = api_url + 'tasks/report/'
    view_url = api_url + 'tasks/view/'
    delete_url = api_url + 'tasks/delete/'
    maec_report_url = (
        '<a href="{api_url}/v1/tasks/report/{{task_id}}/maec" target="_blank">'
        'View the Cuckoo MAEC report</a>'
    ).format(api_url=api_url)
    web_report_url = (
        '<a href="{web_url}/analysis/{{task_id}}/summary/" target="_blank">'
        'View the report in Cuckoo</a>'
    ).format(web_url=web_url)

    for fname in filelist:
        with open(fname, "rb") as sample:
            multipart_file = {"file": (basename(fname), sample)}
            payload = {"timeout": conf['timeout']}
            request = requests.post(new_file_url, files=multipart_file, json=json.dumps(payload))

        task_id = request.json()["task_id"]
        if task_id is not None:
            tasks.append((fname, str(task_id)))
        else:
            # TODO Do something here?
            pass

    # Wait for tasks to finish
    task_status = {}
    while tasks:
        for fname, task_id in tasks[:]:
            status = requests.get(view_url + task_id).json()['task']['status']

            # TODO - if we don't find a report, should we add (fname, {}) or
            # just skip fname?
            # If we have a report
            if status == 'reported':
                report = fetch_report_json(report_url + task_id)
                if conf['maec']:
                    report['info']['maec report'] = maec_report_url.format(task_id=task_id)
                    # maec_report = fetch_report_json(
                    #     maec_report_url.format(task_id=task_id))
                    # report['maec'] = maec_report
                # TODO - should we just modify Cuckoo to add this itself?
                if report.get('info'):
                    report['info']['web_report'] = web_report_url.format(
                        task_id=task_id)
                resultlist.append((fname, report))
                tasks.remove((fname, task_id))
                if conf['delete tasks']:
                    requests.get(delete_url + task_id)

            # Check for dead tasks
            elif status == 'running':
                if task_id not in task_status:
                    task_status[task_id] = time.time() + conf['timeout'] + conf['running timeout']
                else:
                    if time.time() > task_status[task_id]:
                        # TODO Log timeout
                        tasks.remove((fname, task_id))

            # If there is an unknown status
            elif status not in ['pending', 'processing', 'finished', 'completed', 'running']:
                # TODO Log errors better
                tasks.remove((fname, task_id))
        time.sleep(15)

    metadata = {}
    metadata["Name"] = NAME
    metadata["Type"] = TYPE
    metadata["Include"] = False
    return (resultlist, metadata)

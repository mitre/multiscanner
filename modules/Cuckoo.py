# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/
from __future__ import division, absolute_import, with_statement, print_function, unicode_literals
import requests
import json
import time
from common import basename

__author__ = "Drew Bonasera"
__license__ = "MPL 2.0"

TYPE = "Detonation"
NAME = "Cuckoo Sandbox"
DEFAULTCONF = {
    "ENABLED": False,
    "API URL": 'http://cuckoo:8090/',
    "timeout": 360,
    "delete tasks": False,
    "rerun": False
}
REQUIRES = ['MD5']

def check(conf=DEFAULTCONF):
    return conf["ENABLED"]

def scan(filelist, conf=DEFAULTCONF):
    resultlist = []
    tasks = []
    if conf['API URL'].endswith('/'):
        url = conf['API URL']
    else:
        url = conf['API URL'] + '/'
    new_file_url = url + 'tasks/create/file'
    report_url = url + 'tasks/report/'
    view_url = url + 'tasks/view/'
    delete_url = url + 'tasks/delete/'
    files_view_url = url + 'files/view/md5/'

    if not conf['rerun'] and REQUIRES[0]:
        md5s = dict(REQUIRES[0])
        for fname in filelist[:]:
            md5 = md5s[fname]
            r = requests.get(files_view_url+md5)
            if r.status_code == 200:
                task_id = r.json()['sample']['id']
                r = requests.get(report_url + task_id)
                if r.status_code == 200:
                    resultlist.append((fname, r.json()))
                    filelist.remove(fname)

    for fname in filelist:
        with open(fname, "rb") as sample:
            multipart_file = {"file": (basename(fname), sample)}
            payload = {"timeout": conf['timeout']}
            request = requests.post(new_file_url, files=multipart_file, json=json.dumps(payload))

        task_id = request.json()["task_id"]
        if task_id is not None:
            tasks.append((fname, str(task_id)))
        else:
            #TODO Do something here?
            pass

    # Wait for tasks to finish
    while tasks:
        for fname, task_id in tasks[:]:
            status = requests.get(view_url+task_id).json()['status']

            # If we have a report
            if status == 'reported':
                report = requests.get(report_url+task_id)
                if report.status_code == 200:
                    report = report.json()
                    resultlist.append((fname, report))
                    tasks.remove((fname, task_id))
                    if conf['delete tasks']:
                        requests.get(delete_url+task_id)
                else:
                    # Do we ever actually hit here?
                    pass
            # If there is an unknown status
            elif status not in ['pending', 'processing', 'finished']:
                tasks.remove((fname, task_id))

        time.sleep(15)

    metadata = {}
    metadata["Name"] = NAME
    metadata["Type"] = TYPE
    metadata["Include"] = False
    return (resultlist, metadata)

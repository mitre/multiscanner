# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/
from __future__ import division, absolute_import, with_statement, print_function, unicode_literals
import requests
import json
from common import basename

__author__ = "Drew Bonasera"
__license__ = "MPL 2.0"

TYPE = "Detonation"
NAME = "Cuckoo Sandbox"
DEFAULTCONF = {
"ENABLED": False,
"API URL": 'http://cuckoo:8090/',
"timeout": 360
}

def check(conf=DEFAULTCONF):
    return conf["ENABLED"]

def scan(filelist, conf=DEFAULTCONF):
    resultlist = []
    tasks = []
    url = ''
    if conf['API URL'].endswith('/'):
        url = conf['API URL']
    else:
        url = conf['API URL'] + '/'
    new_file_url = url + 'tasks/create/file'
    report_url = url + 'tasks/report'

    for fname in filelist:
        with open(fname, "rb") as sample:
            multipart_file = {"file": (basename(sample), sample), "timeout": conf['timeout']}
            request = requests.post(new_file_url, files=multipart_file)

        json_decoder = json.JSONDecoder()
        task_id = json_decoder.decode(request.text)["task_id"]
        if task_id is not None:
            tasks.append(task_id)
        else:
            #TODO Do something here
            pass

    for task in tasks:
        request = requests.get(report_url, {})

    metadata = {}
    metadata["Name"] = NAME
    metadata["Type"] = TYPE
    return (resultlist, metadata)

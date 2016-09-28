# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import division, absolute_import, with_statement, print_function, unicode_literals
import os
import time
import csv
import shutil
import sys
import requests
import json
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

__author__ = "Michael Limiero"
__license__ = "MPL 2.0"

TYPE = "Detonation"
NAME = "FireEyeAPI"
DEFAULTCONF = {
        "API URL":"https://fireeye/wsapis/v1.1.0",
        "fireeye images":["win7-sp1", "win7x64-sp1", "winxp-sp3"],
        "username":"api_analyst",
        "password":"Pa$$word1",
        "info level":"normal", # concise, normal, extended
        "timeout":500,
        "force":False, # rescan if it exactly matches a previous scan?
        "analysis type": 0, # 0 = sandbox, 1 = live
        "application id": 0, # For AX Series appliances (7.7 and higher) and
                             # CM Series appliances that manage AX Series
                             # appliances (7.7 and higher), setting the applic-
                             # ation value to -1 allows the AX Series appliance
                             # to choose the application for you. For other
                             # appliances, setting the application value to 0
                             # allows the AX Series appliance to choose the
                             # application for you.
        "ENABLED":False}

VERBOSE = False

def check(conf=DEFAULTCONF):
    return conf["ENABLED"]

def scan(filelist, conf=DEFAULTCONF):
    if VERBOSE:
        print('Authenticating to FireEye API...')
    resp = requests.post(conf['API URL']+'/auth/login', auth=(conf["username"], conf["password"]), verify=False)
    if resp.status_code == 200:
        token = resp.headers['x-feapi-token']
        if VERBOSE:
            print('Authenticated')
    elif resp.status_code == 401:
        raise ValueError('Bad authentication for FireEye API')
    elif resp.status_code == 503:
        raise ValueError('FireEye WSAPI is not enabled')
    else:
        raise ValueError('Unknown response')

    resultlist = []
    waitlist = []
    donelist = []

    for fname in filelist:
        with open(fname, 'rb') as f:
            options = {
                    "priority": "0",
                    "profiles": conf['fireeye images'],
                    "analysistype": str(conf['analysis type']),
                    "prefetch": "1",
                    "force": conf['force'],
                    "timeout": str(conf['timeout']),
                    "application": str(conf['application id'])
                    }
            resp = requests.post(conf['API URL']+'/submissions', headers={'X-FeApi-Token': token}, files={"filename": f}, data={"options": json.dumps(options)}, verify=False)
            resp.raise_for_status()
            waitlist.append((fname, resp.json()[0]['ID']))

    while waitlist:
        for fname, fid in waitlist[:]:
            resp = requests.get(conf['API URL']+'/submissions/status/'+fid, headers={'X-FeApi-Token': token}, verify=False)
            resp.raise_for_status()
            if resp.json()['submissionStatus'] == 'In Progress':
                continue
            elif resp.json()['submissionStatus'] == 'Done':
                donelist.append((fname, fid))
                waitlist.remove((fname, fid))
            else:
                raise ValueError('Unknown response')
        time.sleep(20)

    for fname, fid in donelist:
        resp = requests.get(conf['API URL']+'/submissions/results/'+fid, headers={'X-FeApi-Token': token, 'Accept': 'application/json'}, params={'info_level': conf['info level']}, verify=False)
        resp.raise_for_status()
        resultlist.append((fname, resp.json()))

    resp = requests.post(conf['API URL']+'/auth/logout', headers={'X-FeApi-Token': token}, verify=False)

    metadata = {"Name": NAME, "Type": TYPE}
    return (resultlist, metadata)

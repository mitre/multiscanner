# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import division, absolute_import, with_statement, print_function, unicode_literals
import os
import sys
import subprocess
import re
from common import list2cmdline
from common import sshexec
from common import SSH
subprocess.list2cmdline = list2cmdline

__author__ = "Drew Bonasera"
__license__ = "MPL 2.0"

TYPE = "Metadata"
NAME = "ExifTool"
#These are overwritten by the config file
HOST = ("MultiScanner", 22, "User")
KEY = os.path.join(os.path.realpath(os.path.dirname(sys.argv[0])), 'etc', 'id_rsa')
PATHREPLACE = "X:\\"
#Entries to be removed from the final results
REMOVEENTRY = ["ExifTool Version Number", "File Name", "Directory", "File Modification Date/Time",
    "File Creation Date/Time", "File Access Date/Time", "File Permissions"]
DEFAULTCONF = {'cmdline': ["-t"],
    "path": "C:\\exiftool.exe",
    "key": KEY,
    'host': HOST,
    "replacement path": PATHREPLACE,
    'remove-entry': REMOVEENTRY,
    'ENABLED': True
    }

def check(conf=DEFAULTCONF):
    if not conf['ENABLED']:
        return False
    if os.path.isfile(conf["path"]):
        if 'replacement path' in conf:
            del conf['replacement path']
        return True

    if SSH:
        return True
    else:
        return False

def scan(filelist, conf=DEFAULTCONF):
    if os.path.isfile(conf["path"]):
        local = True
    elif SSH:
        local = False

    cmdline = conf["cmdline"]
    results = []
    output = ""
    cmd = cmdline
    for item in filelist:
        cmd.append('"' + item + '" ')
    cmd.insert(0, conf["path"])

    host, port, user = conf["host"]
    if local:
        try:
            output = subprocess.check_output(cmd)
        except subprocess.CalledProcessError as e:
            output = e.output
            e.returncode
    else:
        try:
            output = sshexec(host, list2cmdline(cmd), port=port, username=user, key_filename=conf["key"])
        except:
            return None

    output = output.decode("utf-8", errors="ignore")
    output = output.replace('\r', '')
    reader = output.split('\n')
    data = {}
    fname = filelist[0]
    for row in reader:
        row = row.split('\t')
        try:
            if row[0].startswith('======== '):
                if data:
                    results.append((fname, data))
                    data = {}
                fname = row[0][9:]
                if re.match('[A-Za-z]:/', fname):
                    #why exif tools, whyyyyyyyy
                    fname = fname.replace('/', '\\')
                continue
        except:
            pass
        try:
            if row[0] not in conf['remove-entry']:
                data[row[0]] = row[1]
        except:
            continue
    if data:
        results.append((fname, data))
        data = {}
    reader = None

    #Gather metadata
    metadata = {}
    output = output.replace('\r', '')
    reader = output.split('\n')
    for row in reader:
        row = row.split('\t')
        if row and row[0] == "ExifTool Version Number":
            metadata["Program version"] = row[1]
            break
    metadata["Name"] = NAME
    metadata["Type"] = TYPE
    return (results, metadata)


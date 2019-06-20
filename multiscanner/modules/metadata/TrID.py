# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import division, absolute_import, with_statement, print_function, unicode_literals

import logging
import os
import subprocess
import re

import multiscanner as ms
from multiscanner.common.utils import list2cmdline, sshexec, SSH

logger = logging.getLogger(__name__)

subprocess.list2cmdline = list2cmdline

__author__ = "Drew Bonasera"
__license__ = "MPL 2.0"

TYPE = "Metadata"
NAME = "TrID"
# These are overwritten by the config file
# Hostname, port, username
HOST = ("MultiScanner", 22, "User")
# SSH Key
KEY = os.path.join(os.path.split(ms.config.CONFIG_FILEPATH)[0], 'etc', 'id_rsa')
# Replacement path for SSH connections
PATHREPLACE = "X:\\"
DEFAULTCONF = {
    "path": '/opt/trid/trid',
    'ENABLED': False,
    "key": KEY,
    "cmdline": ['-r:3'],
    'host': HOST,
    "replacement path": PATHREPLACE
}


def check(conf=DEFAULTCONF):
    if not conf['ENABLED']:
        return False
    if os.path.isfile(conf["path"]):
        del conf['replacement path']
        return True
    elif SSH:
        return True
    else:
        return False


def scan(filelist, conf=DEFAULTCONF):
    if os.path.isfile(conf["path"]):
        local = True
    elif SSH:
        local = False

    cmdline = [conf["path"]]
    cmdline.extend(conf["cmdline"])
    # Generate scan option
    for item in filelist:
        cmdline.append('"' + item + '"')

    output = ""
    if local:
        try:
            output = subprocess.check_output(cmdline)
        except subprocess.CalledProcessError as e:
            logger.error(e)
            output = e.output

    else:
        host, port, user = conf["host"]
        try:
            output = sshexec(host, list2cmdline(cmdline), port=port, username=user, key_filename=conf["key"])
        except Exception as e:
            logger.error(e)
            return None

    # Parse output
    output = output.decode("utf-8")
    output = output.replace('\r', '')
    output = output.split('\n')
    results = []
    fresults = {}
    fname = None
    for line in output:
        if line.startswith('File: '):
            fname = line[6:]
            fresults[fname] = []
            continue

        elif line.startswith('Collecting data from file: '):
            fname = line[27:]
            fresults[fname] = []
            continue

        if fname:
            virusresults = re.findall(r"\s*(\d+.\d+\%) \((\.[^\)]+)\) (.+) \(\d+/", line)
            if virusresults:
                confidence, exnt, ftype = virusresults[0]
                fresults[fname].append([confidence, ftype, exnt])
    for fname in fresults:
        results.append((fname, fresults[fname]))
    metadata = {}
    metadata["Name"] = NAME
    metadata["Type"] = TYPE
    metadata["Include"] = False
    return (results, metadata)

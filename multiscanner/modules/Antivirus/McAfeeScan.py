# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import division, absolute_import, with_statement, print_function, unicode_literals

import os
import subprocess
import re

from multiscanner.config import CONFIG
from multiscanner.common.utils import list2cmdline, sshexec, SSH

subprocess.list2cmdline = list2cmdline

__author__ = "Drew Bonasera"
__license__ = "MPL 2.0"

TYPE = "Antivirus"
NAME = "McAfee"
# These are overwritten by the config file
# SSH Key
KEY = os.path.join(os.path.split(CONFIG)[0], 'etc', 'id_rsa')
# Replacement path for SSH connections
PATHREPLACE = "X:\\"
HOST = ("MultiScanner", 22, "User")
DEFAULTCONF = {
    "path": "C:\\vscl-w32-604-e\\scan.exe",
    "key": KEY,
    "cmdline": ["/ALL"],
    "host": HOST,
    "replacement path": PATHREPLACE,
    "ENABLED": True
}


def check(conf=DEFAULTCONF):
    if not conf['ENABLED']:
        return False
    if os.path.isfile(conf["path"]) or SSH:
        return True
    else:
        return False


def scan(filelist, conf=DEFAULTCONF):
    if os.path.isfile(conf["path"]):
        local = True
    else:
        local = False
    cmdline = conf["cmdline"]
    path = conf["path"]
    # Fixes list2cmd so we can actually quote things...
    subprocess.list2cmdline = list2cmdline
    # Generate scan option
    for item in filelist:
        cmdline.append('"' + item + '"')

    # Create full command line
    cmdline.insert(0, path)
    if local:
        try:
            output = subprocess.check_output(cmdline)
        except subprocess.CalledProcessError as e:
            output = e.output
    else:
        try:
            host, port, user = conf["host"]
            output = sshexec(host, list2cmdline(cmdline), port=port, username=user, key_filename=conf["key"])
        except Exception as e:
            # TODO: log exception
            return None

    # Parse output
    output = output.decode("utf-8")
    virusresults = re.findall("([^\n\r]+) ... Found: ([^\n\r]+)", output, re.MULTILINE)
    metadata = {}
    verinfo = re.search("McAfee VirusScan Command Line for \S+ Version: ([\d\.]+)", output)
    metadata["Name"] = NAME
    metadata["Type"] = TYPE
    if verinfo:
        metadata["Program version"] = verinfo.group(1)
        verinfo = re.search("AV Engine version: ([\d\.]+)\s", output)
        metadata["Engine version"] = verinfo.group(1)
        verinfo = re.search("Dat set version: (\d+) created (\w+ (?:\d|\d\d) \d\d\d\d)", output)
        metadata["Definition version"] = verinfo.group(1)
        metadata["Definition date"] = verinfo.group(2)

    return (virusresults, metadata)

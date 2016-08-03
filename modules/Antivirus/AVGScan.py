# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/
from __future__ import division, absolute_import, with_statement, print_function, unicode_literals
import os
import subprocess
import sys
import re
from common import list2cmdline
from common import sshexec
from common import SSH
subprocess.list2cmdline = list2cmdline

__author__ = "Drew Bonasera"
__license__ = "MPL 2.0"

TYPE = "Antivirus"
NAME = "AVG 2014"
#These are overwritten by the config file
#Hostname, port, username
HOST = ("MultiScanner", 22, "User")
#SSH Key
KEY = os.path.join(os.path.realpath(os.path.dirname(sys.argv[0])), 'etc', 'id_rsa')
#Replacement path for SSH connections
PATHREPLACE = "X:\\"
DEFAULTCONF = {"path":"C:\\Program Files\\AVG\\AVG2014\\avgscanx.exe", 
    "key":KEY, 
    "cmdline":['/A', '/H', '/PRIORITY=High'],
    'host':HOST, 
    "replacement path":PATHREPLACE,
    'ENABLED': True
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
    elif SSH:
        local = False
    
    cmdline = conf["cmdline"]
    #Generate scan option
    scan = '/SCAN='
    for item in filelist:
        scan += '"' + item + '";'
    
    #Create full command line
    cmdline.insert(0, conf["path"])
    cmdline.append(scan)
    output = ""
    if local:
        try:
            output = subprocess.check_output(cmdline)
            returnval = 0
        except subprocess.CalledProcessError as e: 
            output = e.output
            #returnval = e.returncode
    else:
        host, port, user = conf["host"]
        try:
            output = sshexec(host, list2cmdline(cmdline), port=port, username=user, key_filename=conf["key"])
        except:
            return None
    #Parse output
    output = output.decode("utf-8", errors='replace')
    virusresults = re.findall("(?:\([^\)]*\) )?([^\s]+) (.+)\s+$", output, re.MULTILINE)
    results = []
    for (file, result) in virusresults[:]:
        if result.endswith(' '):
            result = result[:-1]
        result = result.split(' ')
        if file not in filelist:
            file = file.split(':')[0]
            while file not in filelist and result:
                file = file + ' ' + result.pop(0)
            if file not in filelist or not result:
                continue
        result = result[-1]
        results.append((file,result))

    metadata = {}
    verinfo = re.search("Program version ([\d\.]+), engine ([\d\.]+)", output)
    metadata["Name"] = NAME
    metadata["Type"] = TYPE
    if verinfo:
        metadata["Program version"] = verinfo.group(1)
        metadata["Engine version"] = verinfo.group(2)
    verinfo = re.search("Virus Database: Version ([\d/]+) ([\d-]+)", output)
    if verinfo:
        metadata["Definition version"] = verinfo.group(1)
        metadata["Definition date"] = verinfo.group(2)
    return (results, metadata)


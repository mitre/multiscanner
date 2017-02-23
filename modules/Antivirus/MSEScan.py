# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import division, absolute_import, with_statement, print_function, unicode_literals
import os
import subprocess
import re
import sys
from common import list2cmdline
from common import sshconnect
from common import SSH
subprocess.list2cmdline = list2cmdline

__author__ = "Michael Limiero"
__license__ = "MPL 2.0"

TYPE = "Antivirus"
NAME = "Microsoft Security Essentials"
#These are overwritten by the config file
#SSH Key
KEY = os.path.join(os.path.realpath(os.path.dirname(sys.argv[0])), 'etc', 'id_rsa')
#Replacement path for SSH connections
PATHREPLACE = "X:\\"
HOST = ("MultiScanner", 22, "User")
DEFAULTCONF = {"path":"C:\\Program Files\\Microsoft Security Client\\MpCmdRun.exe", 
    "key":KEY, 
    "cmdline":["-Scan", "-ScanType", "3", "-DisableRemediation", "-File"], 
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
        host, port, user = conf["host"]
    cmdline = conf["cmdline"]
    path = conf["path"]
    
    #Fixes list2cmd so we can actually quote things...
    subprocess.list2cmdline = list2cmdline
    #Create full command line
    cmdline.insert(0, path)

    resultlist = []
    client = sshconnect(host, port=port, username=user, key_filename=conf["key"])
    #Generate scan option
    for item in filelist:
        cmd = cmdline[:]
        cmd.append('"' + item + '"')
    
        #print(repr(cmd))
        #print(repr(list2cmdline(cmd)))
        output = ""
        if local:
            try:
                output = subprocess.check_output(cmd)
                returnval = 0
            except subprocess.CalledProcessError as e: 
                output = e.output
                returnval = e.returncode
        else:
            try:
                stdin, stdout, stderr = client.exec_command(list2cmdline(cmd))
                output = stdout.read()
            except Exception as e:
                return None

        #Parse output
        output = output.decode("utf-8")
        #print(output)
        
        if "<===========================LIST OF DETECTED THREATS==========================>" not in output:
            #resultlist.append((item, {"malicious": False, "raw_output": output}))
            continue

        #res = {"malicious": True, "raw_output": output, "threats": []}

        while '----------------------------- Threat information ------------------------------' in output:
            _, _, output = output.partition('----------------------------- Threat information ------------------------------')
            output = output.lstrip()

            block, _, _ = output.partition('-------------------------------------------------------------------------------')

            #print(block)
            lines = block.split('\n')
            threat_name = lines[0].partition(':')[2].strip()
            #threat = {"threat": threat_name, "resources": []}
            #for line in lines[2:]:
            #	if not ':' in line:
            #		continue
            #	kind, _, path = line.partition(':')
            #	threat['resources'].append({kind.strip(): path.strip()})

            #res['threats'].append(threat)

        resultlist.append((item, threat_name))

    metadata = {}
    metadata["Name"] = NAME
    metadata["Type"] = TYPE
    return (resultlist, metadata)

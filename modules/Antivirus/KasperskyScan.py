# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import division, absolute_import, with_statement, print_function, unicode_literals
import os
import subprocess
import re
import sys
from common import list2cmdline
from common import sshexec
from common import SSH
subprocess.list2cmdline = list2cmdline

__author__ = "Drew Bonasera"
__license__ = "MPL 2.0"

TYPE = "Antivirus"
NAME = "Kaspersky"
#These are overwritten by the config file
#SSH Key
KEY = os.path.join(os.path.realpath(os.path.dirname(sys.argv[0])), 'etc', 'id_rsa')
#Replacement path for SSH connections
PATHREPLACE = "X:\\"
HOST = ("MultiScanner", 22, "User")
DEFAULTCONF = {"path":"C:\\Program Files\\Kaspersky Lab\\Kaspersky Anti-Virus 15.0.0\\avp.exe", 
    "key":KEY, 
    "cmdline":["scan", "/i0", "/fa"], 
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
    #Generate scan option
    for item in filelist:
        cmdline.append('"' + item + '"')
    
    #Create full command line
    cmdline.insert(0, path)
    
    output = ""
    if local:
        try:
            output = subprocess.check_output(cmdline)
            returnval = 0
        except subprocess.CalledProcessError as e: 
            output = e.output
            returnval = e.returncode
    else:
        try:
            output = sshexec(host, list2cmdline(cmdline), port=port, username=user, key_filename=conf["key"])
        except:
            return None

    #Parse output
    output = output.decode("utf-8")
    virusresults = re.findall(".*\t([^\t]*)\t(?:detected|suspicion)\t([^\t\r\n]*)", output, re.MULTILINE)
    metadata = {}
    #Sometimes reports come out as FILE//data#### this will just make that go into the main file report
    tofix = []
    fixdict = {}

    for (file, result) in virusresults:
        if len(file.split("//")) > 1:
            tofix.append(file.split("//")[0])
    
    if tofix:
        for (file, result) in virusresults[:]:
            if file.split("//")[0] in tofix:
                virusresults.remove((file, result))
                file = file.split("//")[0]
            elif file in tofix:
                virusresults.remove((file, result))
            else:
                continue
            if file in fixdict:
                blerp = fixdict[file]
                if isinstance(blerp, list):
                    if result not in blerp:
                        blerp.append(result)
                    fixdict[file] = blerp
                else:
                    blerp = fixdict[file]
                    fixdict[file] = [blerp, result]
            else:
                fixdict[file] = result
    
    for key in fixdict:
        virusresults.append((key, fixdict[key]))
    
    #This seems to be all the metadata I can get... Maybe there is a better way?
    if local:
        try:
            output = subprocess.check_output([path,"/?"])
            returnval = 0
        except subprocess.CalledProcessError as e: 
            output = e.output
            returnval = e.returncode
    else:
        try:
            output = sshexec(host, list2cmdline([path,"/?"]), username=user, key_filename=conf["key"])
        except:
            return None
    output = output.decode("utf-8")
    verinfo = re.search("Kaspersky Anti-Virus \(R\) ([\d\.]+)", output)
    metadata["Name"] = NAME
    metadata["Type"] = TYPE
    if verinfo:
        metadata["Program version"] = verinfo.group(1)
    return (virusresults, metadata)


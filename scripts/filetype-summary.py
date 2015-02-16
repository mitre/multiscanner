#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import json
import argparse
import os

parser = argparse.ArgumentParser(description="Read in json files from multi-scanner and print file type summaries")
#parser.add_argument("-v", "--verbose", action="store_true")
parser.add_argument('Files', help="Files to parse", nargs='+')
args = parser.parse_args()

filelist = []
for file in args.Files:
    if os.path.isfile(file):
        filelist.append(file)
    else:
        print "ERROR " + file + " is not a file..."

jsons = []
for file in filelist:
    json_data = open(file, 'rb')
    data = json.load(json_data)
    json_data.close()
    jsons.append(data)

results = {}
    
for obj in jsons:
    filelist = obj.get("Files", None)
    if filelist == None:
        print "Invalid multi-scanner report..."
    for file in filelist:
        filetype = file.split('.')[-1]
        #init the structure if needed
        if filetype not in results:
            results[filetype] = {}
            results[filetype]["count"] = 0
            results[filetype]["virushits"] = 0
            results[filetype]["infected"] = 0
            results[filetype]["yarahits"] = 0
        results[filetype]["count"] += 1
        avs = filelist[file].get("Antivirus", [])
        for av in avs:
            if isinstance(av, list):
                results[filetype]["virushits"] += len(av)
            else:
                results[filetype]["virushits"] += 1
        if avs:
            results[filetype]["infected"] += 1
        yara = filelist[file].get("Yara", [])
        results[filetype]["yarahits"] += len(yara)

filelist = list(results)
filelist.sort()

for filetype in filelist:
    print filetype + ":"
    #Number of files per file type
    print "Total Files - " + str(results[filetype]["count"])
    #Number of files with at least 1 AV hit
    print "Infected Files - " + str(results[filetype]["infected"])
    #Total number of antivirus hits across all files#Total number of antivirus hits across all files
    print "AV hits - " + str(results[filetype]["virushits"])
    #Total number of yara hits across all files
    print "Yara hits - " + str(results[filetype]["yarahits"])
    print ""

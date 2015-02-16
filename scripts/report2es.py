#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import sys
import os
import json
import elasticsearch

ES_HOSTS = [{
    'host': 'darktemplar.mitre.org',
    'port': 9200
    }]
ES_INDEX = 'multiscanner'
ES_DOCTYPE = 'file-results'

def parse_args():
    """
    Parses arguments
    """
    import argparse
    import parser
    #argparse stuff
    parser = argparse.ArgumentParser(description="Scan files and store results in elastic search")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument('Report', help="Report file with one json report per line")
    return parser.parse_args()

def results2es(results):
    """
    Takes a dictionary of Filename: {Results} and stores it in elastic search.
    """
    es = elasticsearch.Elasticsearch(hosts=ES_HOSTS)
    es.indices.create(index=ES_INDEX, ignore=400)
    for fname in results:
        result = results[fname]
        result['filename'] = fname
        ok = False
        while not ok:
            try:
                es.index(index=ES_INDEX, doc_type=ES_DOCTYPE, id=result['SHA256'], body=result)
                ok = True
            except Exception as e:
                print e

if __name__ == '__main__':
    args = parse_args()
    try:
        reportf = open(args.Report, 'r')
    except:
        print "ERROR: could not open report"
        quit(1)
    print "Storing results..."
    for report in reportf:
        try:
            report = json.loads(report)
        except:
            print "ERROR: Invalid json report in file"
            continue
        if 'Files' in report:
            report = report['Files']
        results2es(report)
        print "next..."
    print "All done!"
    reportf.close()


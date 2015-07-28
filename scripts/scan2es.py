#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import sys
import os
#Comment out this line if multiscanner.py in the parent dir of this file.
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import multiscanner
import elasticsearch

ES_HOSTS = [{
    'host': '127.0.0.1',
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
    parser.add_argument("-r", "--recursive", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument('Files', help="Files and Directories to attach", nargs='+')
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
        es.index(index=ES_INDEX, doc_type=ES_DOCTYPE, id=result['SHA256'], body=result)

if __name__ == '__main__':
    args = parse_args()
    print "Starting scan..."
    results = multiscanner.multiscan(args.Files, recursive=args.recursive)
    results = multiscanner.parse_reports(results, python=True, includeMetadata=False)
    print "Storing results..."
    results2es(results)
    print "Done!"

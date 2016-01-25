#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import division, absolute_import, with_statement, print_function, unicode_literals

import sys
import json
import elasticsearch
from elasticsearch import helpers

def send_to_es(data, es, index='multiscanner', doctype='file-result'):
    data = json.loads(data)

    # We don't care about the metadata for ES
    if data.keys() == ['Files', 'Metadata']:
        data = data['Files']

    actions = []
    for filename in data:
        data[filename]['filename'] = filename
        # If we have the SHA256 we use it as the ID
        if 'SHA256' in data[filename]:
            actions.append({'_index': index, '_type': doctype, '_id': data[filename]['SHA256'], '_source': data[filename]})
        else:
            actions.append({'_index': index, '_type': doctype, '_source': data[filename]})
    elasticsearch.helpers.bulk(es, actions)

def _main():
    args = _parse_args()
    es = elasticsearch.Elasticsearch(hosts=[args.ip])
    es.indices.create(index=args.index, ignore=400)
    data = sys.stdin.readline()
    while data:
        send_to_es(data, es, index=args.index, doctype=args.doctype)
        data = sys.stdin.readline()

def _parse_args():
    import argparse
    parser = argparse.ArgumentParser(description="Store MultiScanner output in elasticsearch")
    parser.add_argument('-i', '--ip', help="The ip/hostname of the elasticsearch host", required=False, metavar="IP", default='127.0.0.1')
    parser.add_argument('-n', '--index', help="The elasticsearch index to use", required=False, metavar="index", default='multiscanner')
    parser.add_argument('-d', '--doctype', help="The elasticsearch doctype to use", required=False, metavar="index", default='file-result')
    return parser.parse_args()

if __name__ == '__main__':
    _main()

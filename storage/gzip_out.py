#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import division, absolute_import, with_statement, print_function, unicode_literals

import sys
import gzip

def _main():
    args = _parse_args()
    if args.output == '-':
        file_handle = gzip.GzipFile(fileobj=sys.stdout, mode='ab')
    else:
        file_handle = gzip.open(args.output, 'ab')

    data = sys.stdin.readline()
    while data:
        file_handle.write(data)
        data = sys.stdin.readline()

def _parse_args():
    import argparse
    parser = argparse.ArgumentParser(description="Store MultiScanner output as a gzip file")
    parser.add_argument('output', help="The file to write", metavar="filepath", default='report.json.gz', nargs='?')
    return parser.parse_args()

if __name__ == '__main__':
    _main()

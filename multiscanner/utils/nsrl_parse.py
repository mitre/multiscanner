#!/usr/bin/env python
from __future__ import (absolute_import, division, print_function,
                        with_statement)

import argparse
import codecs
import csv
import math
import os
import struct
import sys

import six
from tqdm import tqdm


def count_lines(path):
    lines = 0
    with open(path, 'rb') as f:
        data = f.read(1000000)
        while data:
            lines += data.count('\n')
            data = f.read(1000000)
    return lines


# This makes it python2.7 compatible. Python 3 is fine on its own
def unicode_csv_reader(unicode_csv_data, dialect=csv.excel, **kwargs):
    # csv.py doesn't do Unicode; encode temporarily as UTF-8:
    csv_reader = csv.reader(utf_8_encoder(unicode_csv_data),
                            dialect=dialect, **kwargs)
    for row in csv_reader:
        # decode UTF-8 back to Unicode, cell by cell:
        # TODO: Is this py3 compatible?
        yield [unicode(cell, 'utf-8') for cell in row]  # noqa: F821; protected by PY3 check


def utf_8_encoder(unicode_csv_data):
    for line in unicode_csv_data:
        yield line.encode('utf-8')


def parse_nsrl(input_file, output_dir):
    output = codecs.open(os.path.join(output_dir, 'hash_list'), 'w', 'utf-8')
    offset = open(os.path.join(output_dir, 'offsets'), 'wb')

    offset_size = 5
    i = 0
    last = -1
    count = 0
    last_hash = ''

    for _ in range(0, int(math.pow(16, offset_size))):
        offset.write(struct.pack('QI', 0, 0))

    print('Starting to parse, this will take a while...', file=sys.stderr)

    with codecs.open(input_file, 'r', 'utf-8', errors='replace') as f:
        if not six.PY3:
            reader = unicode_csv_reader(f)
        else:
            reader = csv.reader(f)
        for line in tqdm(reader):
            if line[7] == '' and line[0] != last_hash:
                last_hash = line[0]
                i += 1
                offset_val = int(line[0][0:offset_size], 16)
                if offset_val != last:
                    if last != -1:
                        offset.seek(last * 12 + 8)
                        offset.write(struct.pack('I', count))
                        count = 0
                    offset.seek(offset_val * 12)
                    offset.write(struct.pack('Q', output.tell()))
                    last = offset_val
                output.write(line[0].lower() + '\t')
                output.write(line[1].lower() + '\t')
                output.write(line[3] + '\n')
                count += 1


def _parse_args():
    parser = argparse.ArgumentParser(description="Parse the NSRL's NSRLFile.txt for consumption with MultiScanner")
    parser.add_argument('-o', '--output', help='The directory to output the files to', default='.')
    parser.add_argument('NSRLFile', help='NSRLFile.txt from the NSRL archive')
    return parser.parse_args()


def _main():
    args = _parse_args()
    parse_nsrl(args.NSRLFile, output_dir=args.output)


if __name__ == '__main__':
    _main()

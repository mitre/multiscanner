#!/usr/bin/env python
from __future__ import (absolute_import, division, print_function,
                        with_statement)

import argparse
import csv
import math
import os
import struct
import sys

from tqdm import tqdm


def count_lines(path):
    lines = 0
    with open(path, 'rb') as f:
        data = f.read(1000000)
        while data:
            lines += data.count('\n')
            data = f.read(1000000)
    return lines


def parse_nsrl(input_file, output_dir):
    output = open(os.path.join(output_dir, 'hash_list'), 'wb')
    offset = open(os.path.join(output_dir, 'offsets'), 'wb')

    offset_size = 5
    i = 0
    last = -1
    count = 0
    last_hash = ''

    for _ in range(0, int(math.pow(16, offset_size))):
        offset.write(struct.pack('QI', 0, 0))

    print('Starting to parse, this will take a while...', file=sys.stderr)

    with open(input_file, 'r') as f:
        reader = csv.reader(f)
        reader.next()
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
                output.write(line[3])
                count += 1
                output.write('\n')


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

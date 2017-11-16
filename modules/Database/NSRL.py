# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import division, absolute_import, with_statement, print_function, unicode_literals
import gzip
import os
import sys
import struct

__author__ = "Drew Bonasera"
__license__ = "MPL 2.0"

TYPE = "Database"
NAME = "NSRL"

REQUIRES = ["SHA1", "MD5"]

DEFAULTCONF = {
    'hash_list': os.path.join(os.path.realpath(os.path.dirname(sys.argv[0])), 'etc', 'nsrl', 'hash_list'),
    'offsets': os.path.join(os.path.realpath(os.path.dirname(sys.argv[0])), 'etc', 'nsrl', 'offsets'),
    'ENABLED': True
    }


def check(conf=DEFAULTCONF):
    if not conf['ENABLED']:
        return False
    if None in REQUIRES:
        return False
    if not os.path.isfile(conf['hash_list']) or not os.path.isfile(conf['offsets']):
        print('NSRL: Required files do not exist')
        return False
    return True


def scan(filelist, conf=DEFAULTCONF):
    # Read in file offsets
    if conf['offsets'].endswith('.gz'):
        offset_handle = gzip.open(conf['offsets'], 'rb')
    else:
        offset_handle = open(conf['offsets'], 'rb')

    # Open hash file
    if conf['hash_list'].endswith('.gz'):
        hash_list = gzip.open(conf['hash_list'], 'rb')
    else:
        hash_list = open(conf['hash_list'], 'r')

    sha1_data = REQUIRES[0][0]
    sha1_data.sort()

    md5_data = dict(REQUIRES[1][0])

    results = []
    i=0
    for filename, sha1 in sha1_data:
        offset_val = int(sha1[0:5], 16)
        offset_handle.seek(offset_val*12)
        pointer, count = struct.unpack('QI', offset_handle.read(12))
        hash_list.seek(pointer)
        for _ in range(0, count):
            line = hash_list.readline().split('\t')
            i += 1
            if sha1 == line[0]:
                if md5_data[filename] == line[1]:
                    results.append((filename, line[2].strip()))
                    continue
    hash_list.close()
    offset_handle.close()

    metadata = {}
    metadata["Name"] = NAME
    metadata["Type"] = TYPE
    metadata["Include"] = False
    return (results, metadata)

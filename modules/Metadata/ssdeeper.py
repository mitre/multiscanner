# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import division, absolute_import, with_statement, print_function, unicode_literals
try:
    import ssdeep
except ImportError:
    print("ssdeep module not installed...")
    ssdeep = False

import time

__author__ = "Drew Bonasera"
__license__ = "MPL 2.0"

TYPE = "Metadata"
NAME = "ssdeep"


def check():
    if ssdeep:
        return True
    else:
        return False


def scan(filelist):
    results = []
    for fname in filelist:
        goodtogo = False
        i = 0
        # Ran into a weird issue with file locking, this fixes it
        while not goodtogo and i < 5:
            try:
                ssdeep_hash = ssdeep.hash_from_file(fname)
                chunksize, chunk, double_chunk = ssdeep_hash.split(':')
                chunksize = int(chunksize)
                doc = {
                    'ssdeep_hash': ssdeep_hash,
                    'chunksize': chunksize,
                    'chunk': chunk,
                    'double_chunk': double_chunk,
                    'analyzed': 'false',
                    'matches': {},
                }

                results.append((fname, doc))
                goodtogo = True
            except Exception as e:
                print('ssdeeper:', e)
                time.sleep(3)
                i += 1

    metadata = {}
    metadata["Name"] = NAME
    metadata["Type"] = TYPE
    metadata["Include"] = False
    return (results, metadata)

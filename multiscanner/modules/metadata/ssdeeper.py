# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import division, absolute_import, with_statement, unicode_literals
import logging

logger = logging.getLogger(__name__)

__author__ = "Drew Bonasera"
__license__ = "MPL 2.0"

TYPE = "Metadata"
NAME = "ssdeep_analytics"
REQUIRES = ["filemeta"]


def check():
    return True


def scan(filelist):
    results = []
    filemeta_results, _ = REQUIRES[0]

    for fname, filemeta_result in filemeta_results:
        if fname not in filelist:
            logger.debug("File not in filelist: {}".format(fname))
            continue

        ssdeep_hash = filemeta_result.get('ssdeep')
        if ssdeep_hash:
            chunksize, chunk, double_chunk = ssdeep_hash.split(':')
            chunksize = int(chunksize)
            doc = {
                'chunksize': chunksize,
                'chunk': chunk,
                'double_chunk': double_chunk,
                'analyzed': 'false',
                'matches': {},
            }

            results.append((fname, doc))

    metadata = {}
    metadata["Name"] = NAME
    metadata["Type"] = TYPE
    metadata["Include"] = False
    return (results, metadata)

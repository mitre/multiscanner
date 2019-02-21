# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import division, absolute_import, with_statement, unicode_literals
import logging

logger = logging.getLogger(__name__)

try:
    import pyimpfuzzy
except ImportError as e:
    logger.error("pyimpfuzzy module not installed...")
    pyimpfuzzy = False

__author__ = "Patrick Copeland"
__credits__ = ["JPCERT/CC"]
__license__ = "MPL 2.0"

TYPE = "Metadata"
NAME = "impfuzzy"
REQUIRES = ["filemeta"]
DEFAULTCONF = {
    'ENABLED': True,
}


def check(conf=DEFAULTCONF):
    if not conf['ENABLED'] or \
       not pyimpfuzzy or \
       None in REQUIRES:
        return False
    return True


def scan(filelist, conf=DEFAULTCONF):
    results = []
    filemeta_results, _ = REQUIRES[0]

    for fname, filemeta_result in filemeta_results:
        if fname not in filelist:
            logger.debug("File not in filelist: {}".format(fname))
        if not filemeta_result.get('filetype', '').startswith('PE32'):
            continue
        impfuzzy_hash = pyimpfuzzy.get_impfuzzy(fname)
        chunksize, chunk, double_chunk = impfuzzy_hash.split(':')
        chunksize = int(chunksize)
        doc = {
            'impfuzzy_hash': impfuzzy_hash,
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

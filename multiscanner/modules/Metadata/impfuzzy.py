# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import division, absolute_import, with_statement, print_function, unicode_literals
try:
    import pyimpfuzzy
except ImportError as e:
    print("pyimpfuzzy module not installed...")
    pyimpfuzzy = False

__author__ = "Patrick Copeland"
__credits__ = ["JPCERT/CC"]
__license__ = "MPL 2.0"

TYPE = "Metadata"
NAME = "impfuzzy"
REQUIRES = ["libmagic"]
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
    libmagicresults, libmagicmeta = REQUIRES[0]

    for fname, libmagicresult in libmagicresults:
        if fname not in filelist:
            print("DEBUG: File not in filelist")
        if not libmagicresult.startswith('PE32'):
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

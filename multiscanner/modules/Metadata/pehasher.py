# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import division, absolute_import, with_statement, print_function, unicode_literals
try:
    import pefile
except ImportError:
    print("pefile module not installed...")
    pefile = False

try:
    import pehash
    HASH_FUNCS = {
        'totalhash': pehash.totalhash,
        'anymaster': pehash.anymaster,
        'anymaster_v1_0_1': pehash.anymaster_v1_0_1,
        'endgame': pehash.endgame,
        'crits': pehash.crits,
        'pehashng': pehash.pehashng,
    }
except ImportError:
    print("pehash module not installed...")
    pehash = False

__author__ = "Patrick Copeland"
__credits__ = ["knowmalware"]
__license__ = "MPL 2.0"

TYPE = "Metadata"
NAME = "pehash"
REQUIRES = ["libmagic"]
DEFAULTCONF = {
    'ENABLED': True,
}


def check(conf=DEFAULTCONF):
    if not conf['ENABLED'] or \
       not pefile or \
       not pehash or \
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
        pe_hashes = {}
        pe = pefile.PE(fname)
        for name, hasher in HASH_FUNCS.items():
            try:
                pe_hashes[name] = hasher(pe=pe, raise_on_error=True).hexdigest()
            except Exception as e:
                print('pehash ({}):'.format(name), e)
        results.append((fname, pe_hashes))

    metadata = {}
    metadata["Name"] = NAME
    metadata["Type"] = TYPE
    metadata["Include"] = False
    return (results, metadata)

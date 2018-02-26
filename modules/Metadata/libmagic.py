# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import division, absolute_import, with_statement, print_function, unicode_literals
try:
    import magic
except ImportError:
    print("python-magic module not installed...")
    magic = False

__author__ = "Drew Bonasera"
__license__ = "MPL 2.0"

TYPE = "Metadata"
NAME = "libmagic"
DEFAULTCONF = {
    'magicfile': None,
    'ENABLED': True
}


def check(conf=DEFAULTCONF):
    if not conf['ENABLED']:
        return False
    if magic:
        return True
    else:
        return False


def scan(filelist, conf=DEFAULTCONF):
    if conf['magicfile']:
        try:
            maaagic = magic.Magic(magic_file=conf['magicfile'])
        except Exception as e:
            # TODO: log exception
            print("ERROR: Failed to use magic file", conf['magicfile'])
            maaagic = magic.Magic()
    else:
        maaagic = magic.Magic()
    results = []
    for fname in filelist:
        result = maaagic.from_file(fname)
        if not isinstance(result, str):
            result = result.decode('UTF-8', 'replace')
        results.append((fname, result))

    metadata = {}
    metadata["Name"] = NAME
    metadata["Type"] = TYPE
    metadata["Include"] = False
    return (results, metadata)

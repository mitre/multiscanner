# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import division, absolute_import, with_statement, print_function, unicode_literals

__authors__ = "Drew Bonasera"
__license__ = "MPL 2.0"

TYPE = "Metadata"
NAME = "Tika"
REMOVEENTRY = ["X-TIKA:parse_time_millis"]
DEFAULTCONF = {
    'ENABLED': False,
    'remove-entry': REMOVEENTRY
}

try:
    import tika
    from tika import parser
except Exception as e:
    print("tika module not installed...", e)
    tika = False


def check(conf=DEFAULTCONF):
    if not conf['ENABLED']:
        return False
    if not tika:
        return False
    return True


def scan(filelist, conf=DEFAULTCONF):
    results = []

    for f in filelist:
        metadata = parser.from_file(f).get('metadata', {})
        for field in conf['remove-entry']:
            if field in metadata:
                del metadata[field]
        results.append((f, metadata))

    metadata = {}
    metadata["Name"] = NAME
    metadata["Type"] = TYPE
    return results, metadata

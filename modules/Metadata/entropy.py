# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import division, absolute_import, with_statement, print_function, unicode_literals
from collections import Counter
import math


__author__ = "Austin West"
__license__ = "MPL 2.0"

TYPE = "Metadata"
NAME = "entropy"
DEFAULTCONF = {
    'ENABLED': True
}


def check(conf=DEFAULTCONF):
    return True


def scan(filelist, conf=DEFAULTCONF):
    '''Calculate entropy of a string'''
    results = []
    for fname in filelist:
        with open(fname, 'rb') as f:
            text = f.read()
        chars, lns = Counter(text), float(len(text))
        result = -sum(count / lns * math.log(count / lns, 2) for count in chars.values())
        results.append((fname, result))

    metadata = {}
    metadata["Name"] = NAME
    metadata["Type"] = TYPE
    metadata["Include"] = False
    return (results, metadata)
